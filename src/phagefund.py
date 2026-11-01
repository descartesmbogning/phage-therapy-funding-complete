"""Shared functions for the phage therapy funding analysis (1999-2023).

Every figure and table in the paper is produced from one table:
data/processed/phage_funding_analysis.csv (802 grants, Dimensions export of
13 Feb 2024, screened and enriched), built by notebooks/01_preprocessing.ipynb.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Column names used throughout
USD = "Funding amount in USD"
YEAR = "Start Year"
ORG = "Research Organization - standardized"
FUNDER = "Funder"
TOPIC = "Topic N°"
GENDER = "Gender"

PARTIAL_YEAR = 2023          # Dimensions indexes grants with a lag
TREND_YEARS = (1999, 2022)   # complete years used for growth estimates

TOPIC_LABELS = {
    "Bacteriophage Therapy and Infectious Disease Control": "Infectious disease control",
    "Bacterial Genetics and Mechanisms": "Bacterial genetics and mechanisms",
    "Antibiotic Resistance and Therapeutic Strategies": "Antibiotic resistance strategies",
    "Immunotherapy and Targeted Treatments": "Immunotherapy and targeted treatments",
    "Not Class.": "Unclassified",  # 1 grant after duplicates inherit their twin's topic
}
GENDER_LABELS = {"Male": "Male only", "Female": "Female only",
                 "Female;Male": "Mixed", "Male;Female": "Mixed"}

# Categorical palette, fixed order, amber first;
# validated for colour-vision deficiency on white. Do not reorder or cycle.
PALETTE = ["#C98000", "#2F64B5", "#C24A2E", "#0E9A7E", "#8A4FB0"]
NEUTRAL = "#9a9890"                      # "other", totals, context
PARTIAL = "#f6cf85"                      # light amber for the partial year (2023)
INK, INK2, GRID = "#141414", "#5c5c5c", "#e6e3dd"
FONT_SANS = ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"]
FONT_MONO = ["IBM Plex Mono", "DejaVu Sans Mono"]


def load(path: str | Path) -> pd.DataFrame:
    """Load the analysis table and add clean helper columns."""
    d = pd.read_csv(path)
    d = d[(d[YEAR] >= 1999) & (d[YEAR] <= 2023)].copy()
    d["topic"] = d[TOPIC].map(TOPIC_LABELS).fillna("Unclassified")
    d["team_gender"] = d[GENDER].map(GENDER_LABELS).fillna("Gender unknown")
    if "n_researchers" not in d:
        d["n_researchers"] = d["Researchers"].apply(_count_people)
    return d


def _count_people(s) -> int:
    if pd.isna(s):
        return 0
    return len([p for p in str(s).split(",") if p.strip() and p.strip().lower() != "nan"])


def split_list(value, sep: str = ";") -> list[str]:
    if pd.isna(value):
        return []
    return [v.strip() for v in str(value).split(sep) if v.strip() and v.strip().lower() != "nan"]


# ---------------------------------------------------------------- trends
def yearly(d: pd.DataFrame) -> pd.DataFrame:
    y = d.groupby(YEAR).agg(grants=("Grant ID", "count"), usd=(USD, "sum"))
    return y.reindex(range(1999, 2024), fill_value=0)


def loglinear_growth(series: pd.Series, years=TREND_YEARS) -> dict:
    """Annual growth from a log-linear fit, with a 95% CI (replaces endpoint CAGR)."""
    s = series.loc[years[0]:years[1]]
    t = np.asarray(s.index) - years[0]
    coef, cov = np.polyfit(t, np.log(s.values), 1, cov=True)
    b, se = coef[0], np.sqrt(cov[0, 0])
    pct = lambda x: round((np.exp(x) - 1) * 100, 1)
    return {"annual_growth_pct": pct(b), "ci_low": pct(b - 1.96 * se), "ci_high": pct(b + 1.96 * se),
            "years": f"{years[0]}-{years[1]}"}


def endpoint_cagr(series: pd.Series, first: int, last: int) -> float:
    """Compound annual growth rate between two years (last - first intervals)."""
    return round(((series[last] / series[first]) ** (1 / (last - first)) - 1) * 100, 1)


def by_period(d: pd.DataFrame) -> pd.DataFrame:
    p = pd.cut(d[YEAR], [1998, 2008, 2015, 2023], labels=["1999-2008", "2009-2015", "2016-2023"])
    g = d.groupby(p, observed=True)[USD]
    out = pd.DataFrame({
        "Grants": g.count(),
        "Total (USD M)": (g.sum() / 1e6).round(1),
        "Median (USD)": g.median().round(0),
        "Q1 (USD)": g.quantile(0.25).round(0),
        "Q3 (USD)": g.quantile(0.75).round(0),
    })
    out.loc["All years"] = [len(d), round(d[USD].sum() / 1e6, 1), d[USD].median(),
                            d[USD].quantile(.25), d[USD].quantile(.75)]
    out.index.name = "Period"
    return out


# ---------------------------------------------------------------- fractional counting
def fractional(d: pd.DataFrame, col: str, sep: str = ";") -> pd.DataFrame:
    """Split each grant's amount equally across the listed entities so totals add up."""
    rows = []
    for gid, amt, val in zip(d["Grant ID"], d[USD], d[col]):
        items = split_list(val, sep)
        for it in items:
            rows.append((gid, it, amt / len(items), 1 / len(items)))
    f = pd.DataFrame(rows, columns=["Grant ID", col, "usd_frac", "grant_frac"])
    out = f.groupby(col).agg(grants_full=("Grant ID", "nunique"), grants_frac=("grant_frac", "sum"),
                             usd_frac=("usd_frac", "sum"))
    out["share_usd"] = out["usd_frac"] / d[USD].sum()
    return out.sort_values("usd_frac", ascending=False)


def top_funders(d: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    g = d.groupby(FUNDER).agg(**{"Country": ("Funder Country", "first"), "Grants": ("Grant ID", "count"),
                                 "Total (USD M)": (USD, "sum")})
    g["Share (%)"] = (g["Total (USD M)"] / d[USD].sum() * 100).round(1)
    g["Total (USD M)"] = (g["Total (USD M)"] / 1e6).round(1)
    return g.sort_values("Total (USD M)", ascending=False).head(n)


def fractional_aligned(d: pd.DataFrame, list_col: str, org_col: str = "receiver_org_list") -> pd.DataFrame:
    """Fractional counting per recipient institution.

    `list_col` holds one value per institution, in the same order as `org_col`
    (built by src/preprocess.py). A grant with k institutions gives 1/k of its amount
    to each institution, and that share goes to the institution's category.
    """
    rows = []
    for gid, amt, orgs, vals in zip(d["Grant ID"], d[USD], d[org_col], d[list_col]):
        o = split_list(orgs)
        v = str(vals).split(";") if isinstance(vals, str) else []
        if not o:
            continue
        for i in range(len(o)):
            val = v[i].strip() if i < len(v) and v[i].strip() not in ("", "nan") else "Not classified"
            rows.append((gid, val, amt / len(o), 1 / len(o)))
    f = pd.DataFrame(rows, columns=["Grant ID", list_col, "usd_frac", "grant_frac"])
    out = f.groupby(list_col).agg(grants_full=("Grant ID", "nunique"), grants_frac=("grant_frac", "sum"),
                                  usd_frac=("usd_frac", "sum"))
    out["share_usd"] = out["usd_frac"] / d[USD].sum()
    return out.sort_values("usd_frac", ascending=False)


def top_recipients(d: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    f = fractional(d, "receiver_org_list")
    f["Total (USD M, fractional)"] = (f["usd_frac"] / 1e6).round(2)
    f = f.rename(columns={"grants_full": "Grants"})
    return f[["Grants", "Total (USD M, fractional)"]].head(n)


# ---------------------------------------------------------------- gender
def gender_table(d: pd.DataFrame) -> pd.DataFrame:
    order = ["Male only", "Female only", "Mixed", "Gender unknown"]
    g = d.groupby("team_gender")
    out = pd.DataFrame({
        "Grants": g.size(),
        "Total (USD M)": (g[USD].sum() / 1e6).round(1),
        "Share of funding (%)": (g[USD].sum() / d[USD].sum() * 100).round(1),
        "Mean (USD)": g[USD].mean().round(0),
        "Median (USD)": g[USD].median().round(0),
        "Median team size": g["n_researchers"].median(),
    }).reindex(order)
    out.index.name = "Team composition"
    return out


GENDER_MODELS = {
    # name: (outcome, right-hand side). The main model controls for funder, grant length and topic,
    # because female-only teams are not spread evenly across funders and grant lengths.
    "Main: team size, grant length, start year, funder, topic":
        ("log_usd", "log_team + log_years + Q('Start Year') + C(funder_grp) + C(topic)"),
    "Amount per year of grant (team size, start year, funder, topic)":
        ("log_usd_per_year", "log_team + Q('Start Year') + C(funder_grp) + C(topic)"),
    "Simple model: team size, US funder, start year":
        ("log_usd", "log_team + us_funder + Q('Start Year')"),
}


def gender_frame(d: pd.DataFrame, min_funder_grants: int = 10) -> pd.DataFrame:
    e = d[d["team_gender"].isin(["Male only", "Female only", "Mixed"])].copy()
    years = (e["End Year"].fillna(e[YEAR]) - e[YEAR] + 1).clip(lower=1)
    e["log_usd"] = np.log(e[USD])
    e["log_years"] = np.log(years)
    e["log_usd_per_year"] = np.log(e[USD] / years)
    e["us_funder"] = e["Funder Country"].astype(str).str.contains("United States").astype(int)
    e["log_team"] = np.log(e["n_researchers"].clip(lower=1))
    counts = e[FUNDER].map(e[FUNDER].value_counts())
    e["funder_grp"] = e[FUNDER].where(counts >= min_funder_grants, "Other funders")
    e["g"] = pd.Categorical(e["team_gender"], ["Male only", "Female only", "Mixed"])
    return e


def gender_tests(d: pd.DataFrame, models: dict | None = None) -> pd.DataFrame:
    """Mann-Whitney tests and log-amount regressions (robust HC1 errors), one row per comparison and model.

    Funders with fewer than 10 analysed grants are pooled as "Other funders".
    """
    from scipy import stats
    import statsmodels.formula.api as smf

    e = gender_frame(d)
    male = e.loc[e.team_gender == "Male only", USD]
    rows = []
    for name, (y, rhs) in (models or GENDER_MODELS).items():
        m = smf.ols(f"{y} ~ C(g) + {rhs}", data=e).fit(cov_type="HC1")
        for grp in ["Female only", "Mixed"]:
            key = f"C(g)[T.{grp}]"
            rows.append({
                "Comparison": f"{grp} vs Male only", "Model": name,
                "Mann-Whitney p": stats.mannwhitneyu(e.loc[e.team_gender == grp, USD], male).pvalue,
                "Adjusted difference (%)": (np.exp(m.params[key]) - 1) * 100,
                "95% CI low (%)": (np.exp(m.conf_int().loc[key, 0]) - 1) * 100,
                "95% CI high (%)": (np.exp(m.conf_int().loc[key, 1]) - 1) * 100,
                "Regression p": m.pvalues[key], "N": int(m.nobs),
            })
    out = pd.DataFrame(rows).set_index("Comparison").round(3)
    out.attrs["controls"] = "see Model; funders with < 10 grants pooled; robust (HC1) errors"
    return out


# ---------------------------------------------------------------- engagement
def classify_engagement(d: pd.DataFrame, col: str = "Researchers", sep: str = ",",
                        span: bool = False) -> pd.Series:
    """Last-period label per entity, same rules as the patent-study function.

    span=False: an entity is active only in a grant's start year (original rule).
    span=True:  active in every year from start to end year (sensitivity check).
    """
    active: dict[str, set[int]] = {}
    for _, r in d.iterrows():
        s = int(r[YEAR])
        e = int(r["End Year"]) if span and pd.notna(r["End Year"]) else s
        years = range(s, min(max(e, s), PARTIAL_YEAR) + 1)
        for ent in split_list(r[col], sep):
            active.setdefault(ent, set()).update(years)
    last_period = PARTIAL_YEAR
    labels = {}
    for ent, ys in active.items():
        first, last = min(ys), max(ys)
        before = first < last
        if last == last_period:
            labels[ent] = "Continuant" if before else "Newcomer"
        else:
            labels[ent] = "Terminator" if before else "Transient"
    return pd.Series(labels, name="label")


def engagement_summary(d: pd.DataFrame) -> pd.DataFrame:
    a = classify_engagement(d, span=False).value_counts()
    b = classify_engagement(d, span=True).value_counts()
    out = pd.DataFrame({"Start year only (n)": a, "Full grant span (n)": b}).fillna(0).astype(int)
    for c in list(out.columns):
        out[c.replace("(n)", "(%)")] = (out[c] / out[c].sum() * 100).round(1)
    grants_per_person = d["Researchers"].apply(split_list, sep=",").explode().dropna().value_counts()
    out.attrs["single_grant_share"] = round((grants_per_person == 1).mean() * 100, 1)
    out.attrs["n_researchers"] = int(len(grants_per_person))
    return out


# ---------------------------------------------------------------- data quality
def missingness(d: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    m = d[cols].isna().sum()
    return pd.DataFrame({"Present": len(d) - m, "Missing": m, "Missing (%)": (m / len(d) * 100).round(1)})


# ---------------------------------------------------------------- entities, engagement, shares
ENGAGEMENT_LABELS = ["Continuant", "Newcomer", "Terminator", "Transient"]


def engagement_by_year(d: pd.DataFrame, col: str = "Researchers", sep: str = ",",
                       last_period: int = PARTIAL_YEAR) -> pd.DataFrame:
    """Entities per year by engagement label (years x 4 labels, zeros kept).

    In each year an entity is active, it is a Newcomer (active later, never before),
    Continuant (active before and after, or before and in the last period), Terminator
    (before, never after) or Transient (that year only). Activity = grant start year.
    Years with no entity are 0, and every subset uses the same `last_period` (2023),
    so topics and genders are comparable.
    """
    active: dict[str, set[int]] = {}
    for y, val in zip(d[YEAR], d[col]):
        for ent in split_list(val, sep):
            active.setdefault(ent, set()).add(int(y))
    rows = []
    for ys in active.values():
        ys = sorted(ys)
        for i, y in enumerate(ys):
            before, after = i > 0, i < len(ys) - 1
            if y == last_period:
                lab = "Continuant" if before else "Newcomer"
            elif before and after:
                lab = "Continuant"
            elif before:
                lab = "Terminator"
            elif after:
                lab = "Newcomer"
            else:
                lab = "Transient"
            rows.append((y, lab))
    t = pd.DataFrame(rows, columns=["year", "label"])
    out = pd.crosstab(t["year"], t["label"]) if len(t) else pd.DataFrame()
    return out.reindex(index=range(1999, last_period + 1), columns=ENGAGEMENT_LABELS, fill_value=0)


def researchers_by_gender_year(d: pd.DataFrame) -> pd.DataFrame:
    """Distinct named researchers per start year, by inferred gender."""
    rows = []
    for y, names, gens in zip(d[YEAR], d["Researchers"], d["researcher_gender_list"]):
        people = split_list(names, ",")
        g = str(gens).split(";") if isinstance(gens, str) else []
        for i, p in enumerate(people):
            gi = g[i].strip() if i < len(g) else ""
            rows.append((int(y), p, gi if gi in ("Male", "Female") else "Unknown"))
    t = pd.DataFrame(rows, columns=["year", "person", "gender"]).drop_duplicates(["year", "person"])
    out = pd.crosstab(t["year"], t["gender"]).reindex(index=range(1999, 2024), fill_value=0)
    out = out.reindex(columns=["Male", "Female", "Unknown"], fill_value=0)
    out["Female share (%)"] = (out["Female"] / (out["Male"] + out["Female"]) * 100).round(1)
    return out


def aligned_long(d: pd.DataFrame, list_col: str, org_col: str = "receiver_org_list") -> pd.DataFrame:
    """Long table (grant, value, usd_frac, grant_frac) with 1/k per recipient institution."""
    rows = []
    for gid, amt, orgs, vals in zip(d["Grant ID"], d[USD], d[org_col], d[list_col]):
        o = split_list(orgs)
        v = str(vals).split(";") if isinstance(vals, str) else []
        for i in range(len(o)):
            val = v[i].strip() if i < len(v) and v[i].strip() not in ("", "nan") else "Not classified"
            rows.append((gid, val, amt / len(o), 1 / len(o)))
    return pd.DataFrame(rows, columns=["Grant ID", list_col, "usd_frac", "grant_frac"])


def row_shares(d: pd.DataFrame, row: str, col: str, weight: str | None = None,
               rows: list | None = None) -> pd.DataFrame:
    """Row-normalised cross-table in %: each row sums to 100."""
    t = pd.crosstab(d[row], d[col], values=d[weight] if weight else None,
                    aggfunc="sum" if weight else None).fillna(0)
    if rows is not None:
        t = t.reindex(rows).fillna(0)
    return (t.div(t.sum(axis=1), axis=0) * 100).round(1)


def country_flows(d: pd.DataFrame) -> pd.DataFrame:
    """Funding from funder country to recipient country, fractional per institution (USD)."""
    f = aligned_long(d, "receiver_country_list").merge(d[["Grant ID", "Funder Country"]], on="Grant ID")
    out = f.groupby(["Funder Country", "receiver_country_list"]).agg(
        grants_frac=("grant_frac", "sum"), usd_frac=("usd_frac", "sum")).reset_index()
    out = out.rename(columns={"receiver_country_list": "Recipient country"})
    out["domestic"] = out["Funder Country"] == out["Recipient country"]
    return out.sort_values("usd_frac", ascending=False)


def jaccard_matrix(words: dict[str, list[str]]) -> pd.DataFrame:
    """Pairwise Jaccard similarity of topic word lists."""
    k = list(words)
    m = [[len(set(words[a]) & set(words[b])) / len(set(words[a]) | set(words[b])) for b in k] for a in k]
    return pd.DataFrame(m, index=k, columns=k).round(3)


def distinctive_words(texts: pd.Series, groups: pd.Series, n: int = 30, min_df: int = 5) -> dict[str, list[str]]:
    """Top-n words per group: mean grant-level TF-IDF within the group (for topics already assigned).

    Words used in most grants (e.g. "phage") get a low IDF, so each list shows what
    sets a topic apart rather than what all phage grants share.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(min_df=min_df, max_df=0.5, stop_words="english",
                          token_pattern=r"(?u)\b[a-z][a-z]{2,}\b")
    X = vec.fit_transform(texts.fillna("").str.lower().str.replace(r"\bnan\b", " ", regex=True))
    terms = np.array(vec.get_feature_names_out())
    g = np.asarray(groups)
    out = {}
    for k in pd.unique(g):
        m = np.asarray(X[g == k].mean(axis=0)).ravel()
        out[k] = list(terms[np.argsort(-m)[:n]])
    return out


# ---------------------------------------------------------------- concentration, collaboration, sensitivity
NIAID = "National Institute of Allergy and Infectious Diseases"
PERIODS = ([1998, 2008, 2015, 2023], ["1999-2008", "2009-2015", "2016-2023"])


def hhi(values) -> float:
    """Herfindahl-Hirschman index on a 0-10,000 scale (shares in %, squared, summed)."""
    v = pd.Series(values, dtype=float)
    s = v / v.sum() * 100
    return round(float((s ** 2).sum()), 0)


def gini(values) -> float:
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    return round(float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum())), 3)


def lorenz(values) -> pd.DataFrame:
    """Cumulative share of units (poorest first) vs cumulative share of the total."""
    v = np.sort(np.asarray(values, dtype=float))
    return pd.DataFrame({"units": np.r_[0, np.arange(1, len(v) + 1) / len(v)],
                         "total": np.r_[0, np.cumsum(v) / v.sum()]})


def top_share(values, frac: float = 0.10) -> float:
    v = pd.Series(values, dtype=float).sort_values(ascending=False)
    k = max(1, int(round(len(v) * frac)))
    return round(float(v.head(k).sum() / v.sum() * 100), 1)


def concentration(d: pd.DataFrame) -> pd.DataFrame:
    """Concentration of funding across funders, funder countries, recipient countries, institutions."""
    funders = d.groupby(FUNDER)[USD].sum()
    fcountries = d.groupby("Funder Country")[USD].sum()
    rcountries = aligned_long(d, "receiver_country_list").groupby("receiver_country_list")["usd_frac"].sum()
    insts = fractional(d, "receiver_org_list")["usd_frac"]
    rows = []
    for name, v in [("Funders", funders), ("Funder countries", fcountries),
                    ("Recipient countries (fractional)", rcountries), ("Recipient institutions (fractional)", insts)]:
        rows.append({"Unit": name, "N": len(v), "HHI (0-10,000)": hhi(v), "Gini": gini(v),
                     "Top 10% share (%)": top_share(v), "Largest unit": v.idxmax(),
                     "Largest share (%)": round(v.max() / v.sum() * 100, 1)})
    return pd.DataFrame(rows).set_index("Unit")


def shares_by_period(d: pd.DataFrame) -> pd.DataFrame:
    """US-funder and NIAID shares of funding, and funder HHI, per period."""
    p = pd.cut(d[YEAR], PERIODS[0], labels=PERIODS[1])
    rows = []
    for lab, x in list(d.groupby(p, observed=True)) + [("All years", d)]:
        tot = x[USD].sum()
        rows.append({"Period": lab, "Grants": len(x), "Total (USD M)": round(tot / 1e6, 1),
                     "US funders (%)": round(x.loc[x["Funder Country"] == "United States", USD].sum() / tot * 100, 1),
                     "NIAID (%)": round(x.loc[x[FUNDER] == NIAID, USD].sum() / tot * 100, 1),
                     "Funder HHI": hhi(x.groupby(FUNDER)[USD].sum())})
    return pd.DataFrame(rows).set_index("Period")


def collaboration(d: pd.DataFrame) -> pd.DataFrame:
    """Counts only (no names): shared grants and repeat co-investigator pairs."""
    from itertools import combinations
    orgs = d["receiver_org_list"].apply(lambda v: set(split_list(v)))
    ctry = d["receiver_country_list"].apply(lambda v: set(split_list(v)))
    ns = d["receiver_north_south_list"].apply(lambda v: set(split_list(v)))
    inc = d["receiver_income_list"].apply(lambda v: set(split_list(v)))
    pairs: dict = {}
    for v in d["Researchers"]:
        for a, b in combinations(sorted(set(split_list(v, ","))), 2):
            pairs[(a, b)] = pairs.get((a, b), 0) + 1
    n = len(d)
    multi_c = ctry.apply(len) > 1
    rows = [
        ("Grants with more than one recipient institution", int((orgs.apply(len) > 1).sum())),
        ("Grants with recipients in more than one country", int(multi_c.sum())),
        ("Distinct country pairs in those grants", len({p for c in ctry[multi_c] for p in combinations(sorted(c), 2)})),
        ("Grants linking Global North and Global South recipients", int(ns.apply(lambda s: {"Global North", "Global South"} <= s).sum())),
        ("Grants linking high-income and low or lower-middle income recipients",
         int(inc.apply(lambda s: "High income" in s and bool(s & {"Low income", "Lower middle income"})).sum())),
        ("Grants with 2 or more named researchers", int(d["Researchers"].apply(lambda v: len(split_list(v, ",")) >= 2).sum())),
        ("Co-investigator pairs", len(pairs)),
        ("Pairs that worked together on 2 or more grants", sum(1 for c in pairs.values() if c >= 2)),
    ]
    out = pd.DataFrame(rows, columns=["Measure", "Count"]).set_index("Measure")
    out["Share of grants (%)"] = [round(c / n * 100, 1) if m.startswith("Grants") else np.nan for m, c in rows]
    return out


def deflate(d: pd.DataFrame, cpi: pd.DataFrame, base_year: int = 2023) -> pd.Series:
    """Amounts in constant base-year USD using annual CPI-U (start year of the grant)."""
    f = cpi.set_index("year")["cpi_u_annual_avg"]
    return d[USD] * f[base_year] / d[YEAR].map(f)


def without_funder(d: pd.DataFrame, funder: str = NIAID) -> pd.DataFrame:
    """Growth and concentration with and without one funder (sensitivity check)."""
    rows = []
    for lab, x in [("All funders", d), (f"Without {funder}", d[d[FUNDER] != funder])]:
        y = yearly(x)
        g, u = loglinear_growth(y["grants"]), loglinear_growth(y["usd"])
        tot = x[USD].sum()
        rows.append({"Sample": lab, "Grants": len(x), "Total (USD M)": round(tot / 1e6, 1),
                     "Grant growth (%/yr)": g["annual_growth_pct"], "Grant growth CI": f"{g['ci_low']} to {g['ci_high']}",
                     "Funding growth (%/yr)": u["annual_growth_pct"], "Funding growth CI": f"{u['ci_low']} to {u['ci_high']}",
                     "US funders (%)": round(x.loc[x["Funder Country"] == "United States", USD].sum() / tot * 100, 1),
                     "Funder HHI": hhi(x.groupby(FUNDER)[USD].sum()),
                     "Funder-country HHI": hhi(x.groupby("Funder Country")[USD].sum())})
    return pd.DataFrame(rows).set_index("Sample")


# ---------------------------------------------------------------- display
_ACRONYMS = {"Nci": "NCI", "Nih": "NIH", "Usa": "USA", "Uk": "UK", "Inserm": "INSERM", "Cnrs": "CNRS"}


def tidy_name(name: str) -> str:
    """Display-only clean-up of Dimensions title case ("University Of Montana" -> "University of Montana").

    The underlying names are not changed, so joins and counts are unaffected.
    """
    words = str(name).split(" ")
    small = {"Of", "And", "For", "The", "In", "At", "De", "Da", "Du", "Des", "La", "Le"}
    out = [w.lower() if i > 0 and w in small else _ACRONYMS.get(w, w) for i, w in enumerate(words)]
    return " ".join(out)
