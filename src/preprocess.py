"""Build the analysis table from the screened Dimensions export.

Inputs (all private, see data/README.md):
    data/raw/grants_screened.xlsx      screened and hand-enriched Dimensions export (818 rows, 1978-2024)
    data/raw/receiver_metadata.xlsx    one row per recipient institution: country, region, type, income group, North/South
    data/raw/gender_lookup.xlsx        one row per researcher name: inferred gender
    data/interim/topic_assignments.csv Grant ID -> LDA topic number (from 02_topic_modelling)
    data/reference/country_classification.csv  country -> income group and Global North/South (public, in the repo)

Output:
    data/processed/phage_funding_analysis.csv  (802 grants, 1999-2023)

Conventions:
- Lists keep their order and repeats. Columns ending in `_list` hold one value per recipient institution,
  aligned one-to-one with `Research Organization - standardized`, so amounts can be split by institution.
- Summary columns (Gender, Receiver - ...) hold the distinct values per grant.
- Country labels (income group, Global North/South) come from one reference table for both funders
  and recipients.
- The European Commission and the European Research Council are coded as funder country "European Union".
"""
from __future__ import annotations

import pandas as pd

ORG = "Research Organization - standardized"
RECEIVER_COLS = {
    "Receiver - Country of standardized research organization": "receiver_country_list",
    "Receiver - Region of standardized research organization": "receiver_region_list",
    "Receiver - Type of standardized research organization": "receiver_type_list",
    "Receiver - Income group": "receiver_income_list",
    "Receiver - Global north - south": "receiver_north_south_list",
}
TOPIC_NAMES = {
    0: "Bacterial Genetics and Mechanisms",
    1: "Antibiotic Resistance and Therapeutic Strategies",
    2: "Immunotherapy and Targeted Treatments",
    3: "Not Class.",
    4: "Bacteriophage Therapy and Infectious Disease Control",
}


EU_FUNDERS = {"European Commission", "European Research Council"}


def _split(value, sep):
    if pd.isna(value) or str(value).strip() in ("", "[]", "nan"):
        return []
    return [v.strip() for v in str(value).split(sep) if v.strip()]


def load_grants(path, first_year=1999, last_year=2023) -> pd.DataFrame:
    d = pd.read_excel(path)
    d[ORG] = d[ORG].str.title()
    d["Researchers"] = d["Researchers"].str.title().replace("[]", "")
    return d[(d["Start Year"] >= first_year) & (d["Start Year"] <= last_year)].reset_index(drop=True)


def load_receivers(path) -> pd.DataFrame:
    r = pd.read_excel(path, sheet_name=0)
    r[ORG] = r[ORG].str.title()
    return r.drop_duplicates(ORG).set_index(ORG)


def load_gender(path, name_col="Researchers", gender_col="gender_bon") -> dict:
    g = pd.read_excel(path)
    g[name_col] = g[name_col].str.title().replace("[]", "")
    g[gender_col] = g[gender_col].astype(str).str.strip().str.title()
    g = g[g[gender_col].isin(["Male", "Female"])]
    return g.drop_duplicates(name_col).set_index(name_col)[gender_col].to_dict()


def add_receivers(d: pd.DataFrame, rec: pd.DataFrame) -> pd.DataFrame:
    orgs = d[ORG].apply(_split, sep=";")
    d["receiver_org_list"] = orgs.apply(";".join)
    for src, new in RECEIVER_COLS.items():
        aligned = orgs.apply(lambda os: [str(rec[src].get(o, "")) if o in rec.index else "" for o in os])
        d[new] = aligned.apply(";".join)
        # summary column: distinct values per grant
        d[src] = aligned.apply(lambda vs: ";".join(sorted({v for v in vs if v and v != "nan"})) or pd.NA)
    d["n_recipients"] = orgs.apply(len)
    return d


NOT_NAMES = {"Ph.D.", "Phd", "Md", "M.D.", "Dr", "Jr", "Jr."}


def add_gender(d: pd.DataFrame, lookup: dict) -> pd.DataFrame:
    # Dimensions sometimes splits degrees off names ("Jane Doe, Ph.D."); those parts are not people
    people = d["Researchers"].apply(_split, sep=",").apply(lambda ps: [p for p in ps if p not in NOT_NAMES])
    genders = people.apply(lambda ps: [lookup.get(p, "") for p in ps])
    d["researcher_gender_list"] = genders.apply(";".join)
    d["n_researchers"] = people.apply(len)
    d["n_male"] = genders.apply(lambda gs: gs.count("Male"))
    d["n_female"] = genders.apply(lambda gs: gs.count("Female"))
    d["n_gender_unknown"] = genders.apply(lambda gs: sum(1 for g in gs if g not in ("Male", "Female")))

    def team(row):
        m, f = row["n_male"] > 0, row["n_female"] > 0
        if m and f:
            return "Female;Male"
        if m:
            return "Male"
        if f:
            return "Female"
        return pd.NA
    d["Gender"] = d.apply(team, axis=1)
    return d


def add_topics(d: pd.DataFrame, topics: pd.DataFrame) -> pd.DataFrame:
    t = topics.drop_duplicates("Grant ID").set_index("Grant ID")
    d["topic_id"] = d["Grant ID"].map(t["topic_id"])
    d["topic_source"] = d["Grant ID"].map(t["source"])
    d["Topic N°"] = d["topic_id"].map(TOPIC_NAMES).fillna("Not Class.")
    return d


def apply_country_classification(d: pd.DataFrame, ref_path) -> pd.DataFrame:
    """Overwrite funder and recipient income / North-South labels from the reference table."""
    ref = pd.read_csv(ref_path).set_index("country")
    d["Funder Country (Dimensions)"] = d["Funder Country"]
    d.loc[d["Funder"].isin(EU_FUNDERS), "Funder Country"] = "European Union"
    d["Funder Income group"] = d["Funder Country"].map(ref["income_group"])
    d["funder Global north - south"] = d["Funder Country"].map(ref["north_south"])
    countries = d["receiver_country_list"].apply(lambda s: s.split(";") if isinstance(s, str) and s else [])
    for new, summary, col in [("receiver_income_list", "Receiver - Income group", "income_group"),
                             ("receiver_north_south_list", "Receiver - Global north - south", "north_south")]:
        vals = countries.apply(lambda cs: [str(ref[col].get(c, "")) for c in cs])
        d[new] = vals.apply(";".join)
        d[summary] = vals.apply(lambda vs: ";".join(sorted({v for v in vs if v and v != "nan"})) or pd.NA)
    return d


def build(grants_path, receivers_path, gender_path, topics_path, countries_path=None) -> pd.DataFrame:
    d = load_grants(grants_path)
    d = add_receivers(d, load_receivers(receivers_path))
    if countries_path is not None:
        d = apply_country_classification(d, countries_path)
    d = add_gender(d, load_gender(gender_path))
    d = add_topics(d, pd.read_csv(topics_path))
    return d
