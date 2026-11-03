"""Open dataset: the explorer's data cube, the data dictionary and the Frictionless data package.

Everything written here is aggregate. No researcher names, grant titles or grant IDs leave the private folders.
Used by notebook 08.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import phagefund as pf

# ---------------------------------------------------------------- explorer cube
CUBE_DIMS = ["year", "funder_country", "funder", "recipient_country", "recipient_income", "topic"]


def build_cube(d: pd.DataFrame) -> pd.DataFrame:
    """Grants and recorded USD by year x funder country x funder x recipient country x income group x topic.

    Fractional counting by recipient institution, as in the paper, so every total adds up.
    Every funder keeps its own name.
    """
    d = d.copy()
    d["topic"] = d[pf.TOPIC].map(lambda t: pf.TOPIC_LABELS.get(t, t))
    cty = pf.aligned_long(d, "receiver_country_list")
    inc = pf.aligned_long(d, "receiver_income_list")
    long = cty.rename(columns={"receiver_country_list": "recipient_country"})
    long["recipient_income"] = inc["receiver_income_list"].values
    missing = d[~d["Grant ID"].isin(long["Grant ID"])]
    if len(missing):  # a grant with no recipient institution keeps its full amount
        long = pd.concat([long, pd.DataFrame({"Grant ID": missing["Grant ID"], "recipient_country": "Not classified",
                                              "usd_frac": missing[pf.USD], "grant_frac": 1.0,
                                              "recipient_income": "Not classified"})])
    long = long.merge(d[["Grant ID", pf.YEAR, "Funder Country", pf.FUNDER, "topic"]], on="Grant ID")
    long["funder"] = long[pf.FUNDER].map(pf.tidy_name)
    cube = (long.groupby([pf.YEAR, "Funder Country", "funder", "recipient_country", "recipient_income", "topic"])
            .agg(grants=("grant_frac", "sum"), usd=("usd_frac", "sum")).reset_index()
            .rename(columns={pf.YEAR: "year", "Funder Country": "funder_country"}))
    cube["grants"] = cube["grants"].round(4)
    cube["usd"] = cube["usd"].round(0)
    return cube


def check_cube(cube: pd.DataFrame, key: dict) -> None:
    """Stop if the cube does not reproduce the paper's totals."""
    assert abs(cube["grants"].sum() - key["grants"]) < 0.01, cube["grants"].sum()
    assert abs(cube["usd"].sum() / 1e6 - key["usd_m"]) < 0.05, cube["usd"].sum()
    low = cube[cube.recipient_income.isin(["Low income", "Lower middle income"])].usd.sum() / cube.usd.sum() * 100
    assert abs(low - key["lmic_low_recipients_pct"]) < 0.005, low


# ---------------------------------------------------------------- table catalogue
TABLES = {
    "Table1_by_period": "Grants and recorded funding by period of start year.",
    "Table2a_top_funders": "Ten largest funders by recorded funding.",
    "Table2b_top_recipients": "Ten largest recipient institutions by recorded funding (fractional counting).",
    "Table3_topics": "Grants and recorded funding by research topic (Supplementary Table S37).",
    "Table4_gender": "Grants by gender composition of the research team.",
    "Table5_income_groups": "Share of recorded funding by World Bank income group (FY2024), funders and recipients (Supplementary Table S38).",
    "S1_missingness": "Completeness of the analysis table (802 grants): fields present and missing.",
    "S2_growth": "Annual growth of grants and recorded funding, 1999-2022: log-linear estimate with 95% CI, and endpoint compound annual growth rate.",
    "S3_gender_tests": "Grant size by team gender: Mann-Whitney tests and regression models of log(amount).",
    "S4_north_south": "Share of recorded funding by Global North and Global South, funders and recipients.",
    "S5_countries": "Recorded funding by country, as funder country and as recipient country (fractional counting).",
    "S6_funders_by_count": "Ten funders with the most grants.",
    "S7_engagement_definitions": "Researcher engagement labels, counting a grant in its start year only or in every year it runs.",
    "S8_topic_coherence": "Mean c_v topic coherence for LDA models with k = 2-12 topics.",
    "S9_topic_stability": "Share of grants that keep the same topic when the model is refitted with other random seeds.",
    "S10_topic_top_words": "Top 50 words of each topic in the refitted k = 5 model. Columns are refit topic numbers: refit 4, 2, 3, 1 and 0 match the paper's topics 0 (bacterial genetics), 1 (antibiotic resistance), 2 (immunotherapy), 4 (infectious disease control) and 3 (unclassified).",
    "S11_global_south_recipients": "Global South recipient countries: recipient entries and recorded funding (fractional counting).",
    "S12_domestic_vs_crossborder": "Domestic and cross-border funding (domestic: every recipient institution in the funder's country).",
    "S13_crossborder_funders": "Largest cross-border funders.",
    "S14_funder_by_year": "Grants per start year for the 15 funders with the most grants.",
    "S15_topic_share_by_funder": "Topic shares (% of each funder's grants) for the 15 funders with the most grants.",
    "S16_topic_share_by_recipient": "Topic shares (% of each country's grants) for the 15 largest recipient countries.",
    "S17_topic_distinctive_words": "Most distinctive words of each topic, ranked.",
    "S18_topic_jaccard": "Jaccard similarity between the top-word sets of the topics.",
    "S19_researchers_by_gender_year": "Named researchers by inferred gender and start year.",
    "S20_team_gender_by_topic": "Team gender composition by topic, % of grants.",
    "S21_researcher_engagement_by_year": "Researcher engagement labels by year.",
    "S22_institution_engagement_by_topic": "Institution engagement labels by topic and year.",
    "S23_country_flows": "Grants and recorded funding from funder country to recipient country (fractional counting).",
    "S24_concentration": "Concentration of recorded funding: HHI (0-10,000), Gini and top 10% share.",
    "S25_shares_by_period": "Shares of recorded funding from US funders and NIAID, and funder HHI, by period.",
    "S26_collaboration": "Collaboration counts: grants with several recipient institutions or countries, and North-South grants.",
    "S27_without_niaid": "Growth, US share and concentration with and without NIAID grants.",
    "S28_real_growth": "Annual growth of recorded funding in nominal and constant 2023 US dollars (CPI-U).",
    "S29_screening_flow": "Screening flow from the Dimensions export to the analysed grants.",
    "S30_award_types": "Award types among relevant grants with and without a recorded amount.",
    "S31_count_based_shares": "Count-based shares (% of grants) with and without the 272 grants that have no amount.",
    "S32_imputed_amount_scenarios": "Shares of funding with imputed amounts for grants without an amount.",
    "S33_projects": "Yearly grant records merged into projects.",
    "S34_gender_subsets": "Female-only vs male-only grant size gap in subsets of grants.",
    "S35_topic_probability_shares": "Topic shares of funding from the stored assignment, the refitted model, and split by topic probability.",
    "S36_robustness_summary": "Headline results under each sensitivity check.",
    "paper_numbers": "Every number quoted in the paper: section, claim, value as printed and source.",
}
ROW_LABEL = {  # what the unnamed first column holds
    "S1_missingness": "Field of the analysis table", "S2_growth": "Measure (grants or funding)",
    "S4_north_south": "Global North or Global South", "S5_countries": "Country",
    "S16_topic_share_by_recipient": "Recipient country", "S18_topic_jaccard": "Topic",
    "S28_real_growth": "Dollar basis (nominal or constant 2023 USD)", "Table5_income_groups": "World Bank income group",
}
REFERENCE = {
    "country_classification": "Country to World Bank income group (FY2024), Global North/South and OECD DAC ODA-recipient status.",
    "cpi_u_annual": "Annual average US consumer price index (CPI-U), 1999-2023, used for constant-dollar growth.",
    "nih_reporter_crosscheck": "Yearly NIH totals in this dataset, with an empty column for the same search in NIH RePORTER.",
    "ppp_price_level_2023": "Recipient countries, with an empty column for the World Bank price level ratio (PA.NUS.PPPC.RF).",
}
TOPIC_COLS = list(pf.TOPIC_LABELS.values())
SPECIFIC = {
    "grants": "Grants (fractional: a grant shared by k institutions counts 1/k for each)",
    "usd": "Recorded funding, nominal US dollars as converted by Dimensions (fractional)",
    "year": "Grant start year", "funder_country": "Country of the funder", "funder": "Funder name",
    "recipient_country": "Country of the recipient institution", "recipient_income": "World Bank income group (FY2024) of the recipient country",
    "topic": "Research topic (LDA, k = 5)", "annual_growth_pct": "Annual growth from a log-linear fit, %",
    "ci_low": "Lower bound of the 95% confidence interval", "ci_high": "Upper bound of the 95% confidence interval",
    "years": "Years used for the estimate", "p": "p-value", "N": "Number of grants or units", "k": "Number of topics",
    "seed": "Random seed of the refit", "agreement_pct": "Grants keeping the same topic, %", "c_v": "Mean c_v coherence",
    "Gini": "Gini coefficient (0 = equal, 1 = all to one unit)", "domestic": "Domestic or cross-border",
    "Domestic": "True when funder and recipient country are the same",
}


def _unit(col: str) -> str:
    c = col.lower()
    if "usd m" in c or "(usd m" in c or c == "usd (m)" or "total (usd m)" in c: return "USD million"
    if "(usd)" in c: return "USD"
    if c == "usd": return "USD"
    if "%/yr" in c or "pct" in c or "(%)" in c or "%" in c: return "percent"
    if "points" in c: return "percentage points"
    if "hhi" in c: return "index, 0-10,000"
    return ""


GENERIC = {  # plain-language descriptions of column headers used across tables
    "Period": "Period of grant start years", "Grants": "Number of grants", "Grants (fractional)": "Grants, fractional by recipient institution",
    "Total (USD M)": "Recorded funding, USD million", "Total (USD M, fractional)": "Recorded funding, fractional by recipient institution, USD million",
    "USD (M)": "Recorded funding, USD million", "USD (M, fractional)": "Recorded funding, fractional by recipient institution, USD million",
    "Median (USD)": "Median grant amount, USD", "Mean (USD)": "Mean grant amount, USD", "Q1 (USD)": "25th percentile of grant amounts, USD",
    "Q3 (USD)": "75th percentile of grant amounts, USD", "Funder": "Funder name", "Country": "Funder country", "country": "Country",
    "Funder Country": "Funder country", "Recipient country": "Recipient country", "Recipient institution": "Recipient institution (country)",
    "Share (%)": "Share of all recorded funding, %", "Share of funding (%)": "Share of recorded funding, %", "Share of all funding (%)": "Share of all recorded funding, %",
    "Share of grants (%)": "Share of the 802 grants, %", "Recipient entries": "Recipient institutions counted (one per grant and institution)",
    "Funders (%)": "Share of recorded funding by funder country group, %", "Recipients, fractional (%)": "Share of recorded funding by recipient country group, fractional, %",
    "Funder (USD M)": "Funding provided by funders in the country, USD million", "Recipient, fractional (USD M)": "Funding received by institutions in the country, fractional, USD million",
    "Cross-border grants": "Grants with at least one recipient outside the funder's country",
    "Present": "Grants with a value in this field", "Missing": "Grants without a value in this field", "Missing (%)": "Grants without a value, %",
    "Male": "Named researchers inferred as men", "Female": "Named researchers inferred as women", "Unknown": "Named researchers whose gender could not be inferred",
    "Female share (%)": "Women among named researchers with inferred gender, %", "Male only": "Grants with only men named, %", "Female only": "Grants with only women named, %",
    "Mixed": "Grants with women and men named, %", "Gender unknown": "Grants with no researcher of known gender, %", "Team composition": "Gender composition of the named research team",
    "Median team size": "Median number of named researchers", "Comparison": "Groups compared", "Model": "Regression model and its adjustments",
    "Mann-Whitney p": "p-value of the Mann-Whitney test", "Regression p": "p-value of the group coefficient", "Adjusted difference (%)": "Difference in grant size from the regression, %",
    "95% CI low (%)": "Lower bound of the 95% CI, %", "95% CI high (%)": "Upper bound of the 95% CI, %", "Grants in model": "Grants included in the regression",
    "Subset": "Subset of grants", "Female-only vs male-only (%)": "Adjusted difference in grant size, female-only vs male-only teams, %",
    "Continuant": "Entities active before and after this year", "Newcomer": "Entities active for the first time", "Terminator": "Entities active before but not after",
    "Transient": "Entities active in one year only", "group": "Group of researchers", "label": "Engagement label",
    "Start year only (n)": "Count when a grant counts in its start year only", "Full grant span (n)": "Count when a grant counts in every year it runs",
    "Start year only (%)": "Share when a grant counts in its start year only, %", "Full grant span (%)": "Share when a grant counts in every year it runs, %",
    "Unit": "Unit of analysis", "HHI (0-10,000)": "Herfindahl-Hirschman index (0-10,000)", "Top 10% share (%)": "Share received by the top 10% of units, %",
    "Largest unit": "Unit with the largest share", "Largest share (%)": "Share of the largest unit, %", "US funders (%)": "Share from US funders, %",
    "NIAID (%)": "Share from NIAID, %", "Funder HHI": "HHI across funders (0-10,000)", "Funder-country HHI": "HHI across funder countries (0-10,000)",
    "Measure": "Measure", "Count": "Number of grants or pairs", "Sample": "Grants included", "Grant growth (%/yr)": "Annual growth in grants, %",
    "Grant growth CI": "95% CI of grant growth", "Funding growth (%/yr)": "Annual growth in recorded funding, %", "Funding growth CI": "95% CI of funding growth",
    "Endpoint CAGR 1999-2022 (%)": "Compound annual growth between 1999 and 2022 values, %", "Step": "Screening step", "Records": "Records left after the step",
    "Note": "Note", "Award type": "Award type (research grant, training award, capacity funding)", "With an amount (n)": "Relevant grants with a recorded amount",
    "Without an amount (n)": "Relevant grants without an amount", "With an amount (%)": "Share of grants with an amount, %", "Without an amount (%)": "Share of grants without an amount, %",
    "Measure (share of grants)": "Measure, as % of grants", "With an amount": "Among the 802 grants with an amount", "Without an amount": "Among the 272 grants without an amount",
    "All relevant grants": "Among all 1,074 relevant grants", "All, without training awards": "Among relevant grants, training awards excluded",
    "Recorded amounts only (main analysis)": "Value in the main analysis", "Imputed, low (25th percentile)": "Value with missing amounts imputed at the 25th percentile",
    "Imputed, central (median)": "Value with missing amounts imputed at the median", "Imputed, high (75th percentile)": "Value with missing amounts imputed at the 75th percentile",
    "Grant records": "Yearly grant records", "Projects": "Projects after merging yearly records", "Topic": "Research topic",
    "One topic per grant, paper assignment (%)": "Share of funding, one topic per grant, stored assignment, %", "One topic per grant, refit (%)": "Share of funding, one topic per grant, refitted model, %",
    "Split by topic probability, refit (%)": "Share of funding split by topic probability, refitted model, %",
    "1999-2005, paper assignment (%)": "Share in 1999-2005, stored assignment, %", "1999-2005, split, refit (%)": "Share in 1999-2005, split by probability, %",
    "2016-2023, paper assignment (%)": "Share in 2016-2023, stored assignment, %", "2016-2023, split, refit (%)": "Share in 2016-2023, split by probability, %",
    "Check": "Sensitivity check", "Global South recipients (% of funding)": "Share received by the Global South, %",
    "Low + lower-middle income recipients (%)": "Share received by low- and lower-middle-income countries, %", "US funders (% of funding)": "Share from US funders, %",
    "NIAID (% of funding)": "Share from NIAID, %", "Female-only grant gap (%)": "Adjusted female-only vs male-only grant size gap, %",
    "One-year-only researchers (%)": "Researchers active in a single year, %",
    "Rise in antibiotic-resistance share, 1999-2005 to 2016-2023 (points)": "Change in the antibiotic-resistance topic share, percentage points",
    "section": "Section of the paper", "claim": "What the number measures", "value": "Value as printed in the paper", "source": "Table, figure or code that produces it",
    "note": "Note on the classification", "north_south": "Global North or Global South", "income_group": "World Bank income group (FY2024)",
    "oecd_dac_2024": "OECD DAC ODA-recipient status (2024-25)", "cpi_u_annual_avg": "Annual average CPI-U (1982-84 = 100)",
    "this_dataset_usd_m": "NIH funding in this dataset, USD million", "reporter_usd_m": "Same search in NIH RePORTER, USD million (to fill)",
    "price_level_ratio_2023": "World Bank price level ratio, 2023 (to fill)",
}


def _describe(table: str, col: str) -> str:
    if col.startswith("Unnamed"):
        return f"Row label: {ROW_LABEL.get(table, 'category')}"
    if col in SPECIFIC:
        return SPECIFIC[col]
    if col in GENERIC:
        return GENERIC[col]
    if re.fullmatch(r"(19|20)\d\d", col):
        return f"Grants starting in {col}"
    if col in TOPIC_COLS:
        return {"S15_topic_share_by_funder": f"% of the funder's grants in '{col}'",
                "S16_topic_share_by_recipient": f"% of the country's grants in '{col}'",
                "S17_topic_distinctive_words": f"Distinctive words of '{col}', ranked",
                "S18_topic_jaccard": f"Jaccard similarity with '{col}'"}.get(table, f"Value for the topic '{col}'")
    if re.fullmatch(r"topic_\d", col):
        return f"Top words of refit topic {col[-1]} (see table description for the match to paper topics)"
    return col.replace("_", " ")


def _ftype(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s): return "boolean"
    if pd.api.types.is_integer_dtype(s): return "integer"
    if pd.api.types.is_float_dtype(s): return "number"
    return "string"


def data_dictionary(root: Path) -> pd.DataFrame:
    """One row per column of every public CSV: file, column, type, unit, description."""
    rows = []
    groups = [("outputs/tables", TABLES), ("outputs/explorer", {"cube": "Explorer data cube: grants and recorded funding by year, funder country, funder, recipient country, income group and topic (fractional counting)."}),
              ("data/reference", REFERENCE)]
    for folder, cat in groups:
        for name, desc in cat.items():
            f = root / folder / f"{name}.csv"
            if not f.exists():
                continue
            d = pd.read_csv(f)
            for c in d.columns:
                rows.append({"file": f"{folder}/{name}.csv", "table_description": desc, "column": c,
                             "type": _ftype(d[c]), "unit": _unit(c), "description": _describe(name, c)})
    return pd.DataFrame(rows)


def datapackage(root: Path, dictionary: pd.DataFrame, version: str) -> dict:
    """Frictionless Data Package descriptor (datapackage.json) for every public CSV."""
    res = []
    for f, g in dictionary.groupby("file", sort=False):
        res.append({"profile": "tabular-data-resource", "name": Path(f).stem.lower().replace("_", "-"), "path": f, "format": "csv", "mediatype": "text/csv",
                    "encoding": "utf-8", "description": g["table_description"].iloc[0],
                    "schema": {"fields": [{"name": r.column, "type": r.type, "description": r.description +
                                           (f" ({r.unit})" if r.unit else "")} for r in g.itertuples()]}})
    return {
        "profile": "tabular-data-package",
        "name": "phage-therapy-funding",
        "title": "Global phage therapy research funding, 1999-2023: aggregate tables",
        "description": "Aggregate tables behind every figure and number of the study 'Twenty-five years of phage therapy "
                       "funding: rapid growth, narrow base', from 802 grants with a recorded amount in Dimensions "
                       "(searched 13 February 2024). Grant-level records and researcher names are not included.",
        "version": version,
        "homepage": "https://github.com/descartesmbogning/phage-therapy-funding-complete",
        "licenses": [{"name": "CC-BY-4.0", "path": "https://creativecommons.org/licenses/by/4.0/",
                      "title": "Creative Commons Attribution 4.0"}],
        "contributors": [{"title": "Maxime Descartes Mbogning Fonkou", "role": "author",
                          "path": "https://orcid.org/0000-0001-5581-3891"},
                         {"title": "Nathan Yanwou", "role": "author"}, {"title": "Roland Bamou", "role": "author"},
                         {"title": "Idriss Tsayem N", "role": "author"}],
        "keywords": ["phage therapy", "bacteriophage", "research funding", "antimicrobial resistance",
                     "global health equity", "science of science"],
        "sources": [{"title": "Dimensions grants database (Digital Science)", "path": "https://www.dimensions.ai"}],
        "resources": res,
    }


def write_all(root: Path, d: pd.DataFrame, version: str = "1.0.0") -> dict:
    """Write outputs/explorer/{cube.csv, meta.json}, docs/data_dictionary.csv and datapackage.json."""
    key = json.loads((root / "outputs/tables/key_numbers.json").read_text())
    cube = build_cube(d)
    check_cube(cube, key)
    out = root / "outputs/explorer"
    out.mkdir(parents=True, exist_ok=True)
    cube.to_csv(out / "cube.csv", index=False)
    meta = {"title": "Who funds phage therapy research?", "version": version,
            "source": "Dimensions grants database, searched 13 February 2024",
            "coverage": "802 grants with a recorded amount, 1999-2023",
            "counting": "fractional by recipient institution", "page": "https://cognosx.ca/phage-funding",
            "code": "https://github.com/descartesmbogning/phage-therapy-funding-complete"}
    (out / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    dic = data_dictionary(root)
    dic.to_csv(root / "docs/data_dictionary.csv", index=False)
    (root / "datapackage.json").write_text(json.dumps(datapackage(root, dic, version), indent=1, ensure_ascii=False) + "\n")
    return {"cube_rows": len(cube), "cube_grants": round(cube.grants.sum(), 2), "cube_usd_m": round(cube.usd.sum() / 1e6, 1),
            "dictionary_rows": len(dic), "files_described": dic.file.nunique()}
