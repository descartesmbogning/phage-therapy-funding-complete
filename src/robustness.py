"""Robustness checks: grants without an amount, project-level counts, and alternative definitions.

Everything here works on private grant-level data and returns aggregates only. Nothing in this module
writes grant-level rows to `outputs/`.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

import phagefund as pf

YEARS = (1999, 2023)

# ----------------------------------------------------------------------------- award types
# A grant without an amount is often not missing money: studentships, scholarships, theses and
# graduate-programme records usually have no amount in Dimensions by design. We keep them apart.
TRAINING = re.compile(
    r"studentship|scholarship|fellowship|fulbright|sb-beurs|doctoral|doctorate|postdoc|master|"
    r"scientific initiation|ceec|phd|career development award|training|strategisch basisonderzoek \(sb\)|fellows\b", re.I)
CAPACITY = re.compile(r"formula|hatch|state funding|state \(funding source\)|evans-allen|mcintire", re.I)
GRAD_PROGRAMME = re.compile(r"\(\d{11}P\d\)")            # CAPES graduate-programme codes, e.g. (31003010058P2)
THESIS_HOSTS = ("netd.ac.za",)                             # national theses portals


def award_type(program, link="", funder="") -> str:
    """Classify a Dimensions record as 'Training award', 'Capacity funding' or 'Research grant'."""
    p, l = str(program), str(link)
    if any(h in l for h in THESIS_HOSTS) or GRAD_PROGRAMME.search(p) or "sucupira.capes" in l:
        return "Training award"
    if "bv.fapesp.br" in l and "/bolsas/" in l:
        return "Training award"
    if TRAINING.search(p):
        return "Training award"
    if CAPACITY.search(p):
        return "Capacity funding"
    return "Research grant"


# ----------------------------------------------------------------------------- countries
EXTRA_SPELLINGS = {"Suisse": "Switzerland"}


def norm_country(c) -> str:
    c = re.sub(r"\s+", " ", str(c).replace("\xa0", " ")).strip()
    return EXTRA_SPELLINGS.get(c, c)


def split_countries(value) -> list[str]:
    if pd.isna(value):
        return []
    out = [norm_country(c) for c in re.split(r"[;\n]", str(value))]
    return [c for c in out if c and c.lower() != "nan"]


# ----------------------------------------------------------------------------- grants without an amount
def load_unpriced(export_path: Path, years=YEARS) -> pd.DataFrame:
    """Relevant grants that Dimensions lists without an amount (screening flag 'no fund').

    Returns one row per grant with the fields needed for aggregate checks. Private: never write it to outputs/.
    """
    ex = pd.read_excel(export_path, sheet_name="Sheet1", header=1)
    u = ex[(ex["includes ?"] == 1) & ex["funding?"].eq("no fund") & ex["Start Year"].between(*years)].copy()
    u["Funder Country"] = u["Funder Country"].map(norm_country)
    u.loc[u["Funder"].isin({"European Commission", "European Research Council"}), "Funder Country"] = "European Union"
    u["recipient_countries"] = u["Country of standardized research organization"].apply(split_countries)
    u["award_type"] = [award_type(p, l, f) for p, l, f in zip(u["Program"], u["Source Linkout"], u["Funder"])]
    u[pf.USD] = np.nan
    return u


def screening_flow(export_path: Path, analysis: pd.DataFrame, years=YEARS) -> pd.DataFrame:
    """Counts for the flow diagram, from the raw export's screening columns."""
    ex = pd.read_excel(export_path, sheet_name="Sheet1", header=1)
    rel = ex[ex["includes ?"] == 1]
    priced = rel[~rel["funding?"].eq("no fund")]
    rows = [
        ("Records exported from Dimensions (13 Feb 2024)", len(ex), ""),
        ("Excluded: not about therapeutic use of phages", int((ex["includes ?"] != 1).sum()),
         f"{int((ex['includes ?'] == 0).sum())} coded 0, {int((ex['includes ?'] == -1).sum())} coded -1"),
        ("Relevant grants", len(rel), ""),
        ("Excluded from dollar analyses: no amount in Dimensions", int(rel["funding?"].eq("no fund").sum()),
         "kept for count-based checks"),
        ("Grants with an amount", len(priced), ""),
        ("Excluded: start year outside 1999-2023", len(priced) - len(analysis), ""),
        ("Analysed (dollar analyses)", len(analysis), ""),
        ("Relevant grants without an amount, 1999-2023 (count-based checks)",
         int((rel["funding?"].eq("no fund") & rel["Start Year"].between(*years)).sum()), ""),
    ]
    return pd.DataFrame(rows, columns=["Step", "Records", "Note"])


# ----------------------------------------------------------------------------- recipients, count based
def recipient_shares(rows: pd.DataFrame, ref: pd.DataFrame, weight: str = "w") -> pd.DataFrame:
    """Shares (%) by North/South and income group from long rows (one per grant x country) with a weight column."""
    r = rows.copy()
    r["North/South"] = r["country"].map(ref["north_south"]).fillna("No country")
    r["Income group"] = r["country"].map(ref["income_group"]).fillna("No country")
    tot = r[weight].sum()
    out = {}
    for key in ("North/South", "Income group"):
        s = r.groupby(key)[weight].sum() / tot * 100
        for k, v in s.items():
            out[f"{key}: {k}"] = v
    return pd.Series(out)


def long_recipients(d: pd.DataFrame, value: str | None = None) -> pd.DataFrame:
    """One row per grant x recipient country with weight 1/k (or value/k). Works for both tables."""
    rows = []
    col = "recipient_countries" if "recipient_countries" in d else "receiver_country_list"
    for gid, cs, v in zip(d["Grant ID"], d[col], d[value] if value else np.ones(len(d))):
        cs = cs if isinstance(cs, list) else [c.strip() for c in str(cs).split(";") if c.strip() and c.strip() != "nan"]
        if not cs:
            rows.append((gid, "No country", v))
            continue
        for c in cs:
            rows.append((gid, c, v / len(cs)))
    return pd.DataFrame(rows, columns=["Grant ID", "country", "w"])


# ----------------------------------------------------------------------------- imputation
def impute_amounts(priced: pd.DataFrame, unpriced: pd.DataFrame, q: float = 0.5, training_zero: bool = True) -> pd.Series:
    """Fill missing amounts with the q-quantile of comparable priced grants.

    Order of preference: same funder (>= 3 priced grants), same funder country and award type
    (>= 3), same award type. Training awards are set to 0 when `training_zero` (they are usually
    stipends paid by the host, or have no grant value), otherwise imputed the same way.
    """
    p = priced.assign(award_type=[award_type(a, b) for a, b in zip(priced["Program"], priced["Source Linkout"])])
    by_funder = p.groupby(pf.FUNDER)[pf.USD].agg(["count", lambda s: s.quantile(q)])
    by_country = p.groupby(["Funder Country", "award_type"])[pf.USD].agg(["count", lambda s: s.quantile(q)])
    by_type = p.groupby("award_type")[pf.USD].quantile(q)
    out = []
    for f, c, t in zip(unpriced[pf.FUNDER], unpriced["Funder Country"], unpriced["award_type"]):
        if t == "Training award" and training_zero:
            out.append(0.0)
        elif f in by_funder.index and by_funder.loc[f, "count"] >= 3:
            out.append(by_funder.loc[f].iloc[1])
        elif (c, t) in by_country.index and by_country.loc[(c, t), "count"] >= 3:
            out.append(by_country.loc[(c, t)].iloc[1])
        else:
            out.append(by_type.get(t, p[pf.USD].quantile(q)))
    return pd.Series(out, index=unpriced.index, name="imputed_usd")


def read_recovered(path: Path) -> pd.Series:
    """Amounts recovered by hand from funder websites (worksheet filled by the authors), in USD."""
    if not Path(path).exists():
        return pd.Series(dtype=float)
    r = pd.read_csv(path)
    r = r[pd.to_numeric(r["recovered_usd"], errors="coerce").notna()]
    return r.set_index("Grant ID")["recovered_usd"].astype(float)


# ----------------------------------------------------------------------------- projects
def norm_title(s) -> str:
    return re.sub(r"[^a-z0-9 ]", "", str(s).lower()).strip()


def to_projects(d: pd.DataFrame, min_title_len: int = 20) -> pd.DataFrame:
    """Merge records that are yearly instalments of one project.

    Two records belong to the same project when they have the same funder and the same English title
    (translated title, so non-Latin titles are not merged by mistake) and their start years are at most
    one year after the previous record's end. Amounts are summed, years span the project, and researcher
    and institution lists are combined.
    """
    t = d.get("Title translated", d["Title"]).fillna(d["Title"]).map(norm_title)
    d = d.assign(_t=t, _end=d["End Year"].fillna(d[pf.YEAR]))
    d = d.sort_values([pf.FUNDER, "_t", pf.YEAR])
    pid, last_key, last_end, n = [], None, None, -1
    for f, tt, s, e in zip(d[pf.FUNDER], d["_t"], d[pf.YEAR], d["_end"]):
        key = (f, tt)
        if len(tt) >= min_title_len and key == last_key and s <= last_end + 1:
            last_end = max(last_end, e)
        else:
            n += 1
            last_key, last_end = key, e
        pid.append(n)
    d["project_id"] = pid
    join = lambda s: ";".join(x for x in s.dropna().astype(str) if x)
    agg = {pf.USD: "sum", pf.YEAR: "min", "_end": "max", "Grant ID": "first", pf.FUNDER: "first",
           "Funder Country": "first", "Researchers": lambda s: ", ".join(x for x in s.dropna().astype(str)),
           "receiver_country_list": join}
    for c in ("topic", "team_gender"):
        if c in d:
            agg[c] = "first"
    p = d.groupby("project_id").agg(agg).rename(columns={"_end": "End Year"})
    p["records"] = d.groupby("project_id").size()
    return p.reset_index(drop=True)


# ----------------------------------------------------------------------------- income groups over time
# Recipient countries in this dataset whose World Bank group changed between low/lower-middle and higher
# during 1999-2023. Year = first calendar year of the new group (classification published each July, based on
# the previous year's GNI). Entered by hand from the World Bank historical classification (OGHIST):
# verify against the official file before publication.
INCOME_TRANSITIONS = {
    "China": [(1999, "Lower middle income"), (2010, "Upper middle income")],
    "Thailand": [(1999, "Lower middle income"), (2011, "Upper middle income")],
}


def income_at(country: str, year: int, ref: pd.DataFrame) -> str:
    if country in INCOME_TRANSITIONS:
        g = None
        for y, grp in INCOME_TRANSITIONS[country]:
            if year >= y:
                g = grp
        return g
    return ref["income_group"].get(country, "No country")
