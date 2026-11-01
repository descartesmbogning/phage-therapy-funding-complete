"""Every number quoted in the manuscript, recomputed from the pipeline outputs.

`registry(root)` returns one row per quoted number: where it appears, the value as printed in the paper
(recomputed here, never typed), and the table or code it comes from. `check_manuscript()` then reads the
manuscript text and lists every number in it that is not in the registry, so a number cannot enter the paper
without code behind it.

Only aggregate outputs are read (outputs/tables/*.csv, key_numbers.json) plus the private analysis table for a few
counts that no table holds; nothing grant-level is written.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import phagefund as pf


def _pct(x, nd=1):
    return f"{x:.{nd}f}%"


def _m(x, nd=1):
    return f"{x:.{nd}f}"


def _int(x):
    return f"{int(round(x)):,}"


def registry(root: Path) -> pd.DataFrame:
    root = Path(root)
    T = root / "outputs" / "tables"
    key = json.loads((T / "key_numbers.json").read_text())
    rd = lambda name, **kw: pd.read_csv(T / f"{name}.csv", **kw)
    d = pf.load(root / "data" / "processed" / "phage_funding_analysis.csv")
    usd = d[pf.USD].sum()
    R = []

    def add(section, claim, value, source):
        R.append({"section": section, "claim": claim, "value": value, "source": source})

    # --- sample and screening (S29)
    flow = rd("S29_screening_flow").set_index("Step")["Records"]
    add("Methods 2.1", "Records exported", _int(flow["Records exported from Dimensions (13 Feb 2024)"]), "S29")
    add("Methods 2.1", "Excluded, not therapeutic", _int(flow["Excluded: not about therapeutic use of phages"]), "S29")
    add("Methods 2.1", "Relevant grants", _int(flow["Relevant grants"]), "S29")
    add("Methods 2.1", "No amount", _int(flow["Excluded from dollar analyses: no amount in Dimensions"]), "S29")
    add("Methods 2.1", "With an amount", _int(flow["Grants with an amount"]), "S29")
    add("Methods 2.1", "Start year outside range", _int(flow["Excluded: start year outside 1999-2023"]), "S29")
    add("Methods 2.1", "Analysed grants", _int(flow["Analysed (dollar analyses)"]), "S29")
    add("Methods 2.1", "No amount, 1999-2023", _int(flow["Relevant grants without an amount, 1999-2023 (count-based checks)"]), "S29")
    add("Results 3.5", "Relevant grants 1999-2023", _int(key["relevant_grants_1999_2023"]), "key_numbers")

    # --- methods settings (code constants)
    coh = rd("S8_topic_coherence")
    add("Methods 2.3", "Topic counts tested (from)", str(int(coh.k.min())), "S8")
    add("Methods 2.3", "Topic counts tested (to)", str(int(coh.k.max())), "S8")
    add("Methods 2.3", "Chosen k", str(int(coh.loc[coh.c_v.idxmax(), "k"])), "S8")
    add("Methods 2.3", "min_df", "50", "src/topics.py vectorize(min_df=50)")
    add("Methods 2.3", "max_df", "75%", "src/topics.py vectorize(max_df=0.75)")
    stab = rd("S9_topic_stability")
    s5 = stab[stab.k == 5].agreement_pct
    add("Methods 2.3", "Seed agreement range", f"{s5.min():.0f}\u2013{s5.max():.0f}%", "S9")
    add("Methods 2.3", "Funders pooled below", "10", "phagefund.gender_frame(min_funder_grants=10)")
    add("Methods 2.3", "HHI scale", "0\u201310,000", "phagefund.hhi")
    add("Methods 2.3", "HHI threshold (convention)", "2,500", "convention, docs/methods.md")
    add("Methods 2.4", "Imputation percentiles", "25th, 50th and 75th", "robustness.impute_amounts")
    n_tab = len([f for f in T.iterdir() if f.suffix in (".csv", ".json") and f.name != "paper_numbers.csv"])
    add("Methods 2.5", "Output tables rebuilt", f"{n_tab} output tables", "outputs/tables: CSV tables + key_numbers.json, excluding paper_numbers.csv")

    # --- 3.1 growth and size
    add("Results 3.1", "Funders", str(d[pf.FUNDER].nunique()), "analysis table")
    add("Results 3.1", "Funder countries", str(d["Funder Country"].nunique()), "analysis table")
    add("Results 3.1", "Recipient institutions", str(len(pf.fractional(d, "receiver_org_list"))), "analysis table")
    rc = {c for v in d.receiver_country_list for c in pf.split_list(v)}
    add("Results 3.1", "Recipient countries", str(len(rc)), "analysis table")
    add("Results 3.1", "Total USD M", _m(usd / 1e6), "Table 1")
    add("Results 3.1", "USD M per year (25 years)", f"{usd / 1e6 / 25:.0f}", "Table 1 / 25")
    t1 = rd("Table1_by_period", index_col=0)
    add("Results 3.1", "Median grant", _int(t1.loc["All years", "Median (USD)"]), "Table 1")
    add("Results 3.1", "IQR", f"{_int(t1.loc['All years', 'Q1 (USD)'])}\u2013{_int(t1.loc['All years', 'Q3 (USD)'])}", "Table 1")
    for c, lab in [("grant_growth", "Grant growth"), ("usd_growth", "Funding growth"), ("usd_growth_real_2023", "Real growth")]:
        g = key[c]
        add("Results 3.1", lab, _pct(g["annual_growth_pct"]), "S2 / S28")
        add("Results 3.1", lab + " CI", f"{g['ci_low']:.1f}\u2013{g['ci_high']:.1f}", "S2 / S28")
    for p in t1.index:
        add("Table 1", f"{p} grants", _int(t1.loc[p, "Grants"]), "Table 1")
        add("Table 1", f"{p} USD M", _m(t1.loc[p, "Total (USD M)"]), "Table 1")
        add("Table 1", f"{p} median", _int(t1.loc[p, "Median (USD)"]), "Table 1")
        add("Table 1", f"{p} IQR", f"{_int(t1.loc[p, 'Q1 (USD)'])}\u2013{_int(t1.loc[p, 'Q3 (USD)'])}", "Table 1")
    share_late = t1.loc["2016-2023", "Total (USD M)"] / t1.loc["All years", "Total (USD M)"]
    add("Results 3.1", "Share of funding 2016-2023", "Two thirds" if abs(share_late - 2 / 3) < 0.02 else f"{share_late:.0%}", "Table 1")
    y = pf.yearly(d)
    u = y.loc[1999:2022, "usd"]
    spike = max(range(2000, 2022), key=lambda yr: u[yr] / ((u[yr - 1] + u[yr + 1]) / 2))   # largest jump above both neighbours
    high = int(u.idxmax())                                                                 # largest yearly total
    add("Results 3.1", "Peak years (largest spike, largest total)", " and ".join(str(v) for v in sorted({spike, high})), "Figure 1")
    late = y.loc[2018:2022, "usd"] / 1e6
    add("Results 3.1", "Yearly range 2018-2022 (USD M)", f"{late.min():.0f}\u2013{late.max():.0f}", "Figure 1")

    # --- 3.2 concentration
    add("Results 3.2", "US share", _pct(key["us_funders_pct"]), "S25")
    add("Results 3.2", "NIAID share", _pct(key["niaid_share_pct"]), "Table 2")
    for p, v in key["niaid_share_by_period_pct"].items():
        add("Results 3.2", f"NIAID share {p}", _pct(v), "S25")
    t2a = rd("Table2a_top_funders", index_col=0)
    for f in t2a.index:
        add("Table 2", f"{f} grants", str(int(t2a.loc[f, "Grants"])), "Table 2a")
        add("Table 2", f"{f} USD M", _m(t2a.loc[f, "Total (USD M)"]), "Table 2a")
        add("Table 2", f"{f} share", _m(t2a.loc[f, "Share (%)"]), "Table 2a")
    s6 = rd("S6_funders_by_count", index_col=0)["Grants"]
    for f in s6.index[:3]:
        add("Results 3.2", f"{f} grants (by count)", str(int(s6[f])), "S6")
    add("Results 3.2", "Funder-country HHI", _int(key["hhi_funder_countries"]), "S24")
    s27 = rd("S27_without_niaid", index_col=0)
    add("Results 3.2", "Funder-country HHI without NIAID", _int(s27.iloc[1]["Funder-country HHI"]), "S27")
    add("Results 3.2", "US share without NIAID", _pct(key["without_niaid_us_funders_pct"]), "S27")
    add("Results 3.2", "Growth without NIAID", _pct(key["without_niaid_usd_growth_pct"]), "S27")
    add("Results 3.2", "Top 10% share", _pct(key["top10pct_institutions_share_pct"]), "S24")
    add("Results 3.2", "Gini", f"{key['gini_institutions']:.2f}", "S24")
    s24 = rd("S24_concentration", index_col=0)
    add("Results 3.2", "Largest recipient share", _pct(s24.loc["Recipient institutions (fractional)", "Largest share (%)"]), "S24")
    t2b = rd("Table2b_top_recipients", index_col=0)
    for r in t2b.index:
        add("Table 2", f"{r} grants", str(int(t2b.loc[r, "Grants"])), "Table 2b")
        add("Table 2", f"{r} USD M", f"{t2b.loc[r, 'Total (USD M, fractional)']:.2f}", "Table 2b")

    # --- 3.3 geography
    t5 = rd("Table5_income_groups", index_col=0)
    # unrounded shares (Table 5 stores 2 decimals; rounding those again can differ in the last digit)
    hic_f = d.loc[d["Funder Income group"] == "High income", pf.USD].sum() / usd * 100
    hic_r = pf.fractional_aligned(d, "receiver_income_list")["share_usd"].get("High income", 0) * 100
    add("Results 3.3", "HIC funders", _pct(hic_f), "Table 5 (unrounded)")
    add("Results 3.3", "HIC recipients", _pct(hic_r), "Table 5 (unrounded)")
    add("Results 3.3", "LMIC + low recipients", _pct(key["lmic_low_recipients_pct"], 2), "Table 5")
    ns_f = d.groupby("funder Global north - south")[pf.USD].sum()
    add("Results 3.3", "GS funders USD M", _m(ns_f["Global South"] / 1e6), "S4")
    s4 = rd("S4_north_south", index_col=0)
    add("Results 3.3", "GS funders share", _pct(s4.loc["Global South", "Funders (%)"]), "S4")
    s11 = rd("S11_global_south_recipients", index_col=0)
    add("Results 3.3", "GS recipients USD M", _m(s11.loc["Total Global South", "USD (M)"]), "S11")
    add("Results 3.3", "GS recipients share", _pct(key["global_south_recipients_pct"]), "S4")
    add("Results 3.3", "China share of GS", f"{key['china_share_of_global_south_pct']:.0f}%", "S11")
    add("Results 3.3", "Domestic share", _pct(key["domestic_funding_pct"]), "S12")
    s13 = rd("S13_crossborder_funders", index_col=0)
    add("Results 3.3", "EC cross-border grants", str(int(s13.iloc[0]["Cross-border grants"])), "S13")
    add("Results 3.3", "EC cross-border USD M", _m(s13.iloc[0]["USD (M)"]), "S13")
    s26 = rd("S26_collaboration", index_col=0)["Count"]
    add("Results 3.3", "Multi-institution grants", str(int(s26["Grants with more than one recipient institution"])), "S26")
    add("Results 3.3", "Multi-country grants", str(int(s26["Grants with recipients in more than one country"])), "S26")
    add("Results 3.3", "North-South grants", str(int(s26["Grants linking Global North and Global South recipients"])), "S26")

    # --- 3.4 topics, specialisation, gender, engagement
    t3 = rd("Table3_topics", index_col=0)
    for tp in t3.index[:4]:
        add("Results 3.4", f"{tp} grants", str(int(t3.loc[tp, "Grants"])), "Table 3 (topics)")
        add("Results 3.4", f"{tp} share", _pct(t3.loc[tp, "Share of funding (%)"]), "Table 3 (topics)")
    period = pd.cut(d[pf.YEAR], [1998, 2005, 2010, 2015, 2020, 2023])
    sh = d.groupby([period, "topic"], observed=True)[pf.USD].sum().unstack().fillna(0)
    sh = sh.div(sh.sum(axis=1), axis=0) * 100
    for i, v in enumerate(sh["Antibiotic resistance strategies"]):
        add("Results 3.4", f"AR share, period {i + 1}", f"{v:.0f}%", "Figure 2")
    add("Results 3.4", "Immunotherapy share, first period", "half" if abs(sh["Immunotherapy and targeted treatments"].iloc[0] - 50) < 2 else f"{sh['Immunotherapy and targeted treatments'].iloc[0]:.0f}%", "Figure 2")
    add("Results 3.4", "Immunotherapy share, last periods", f"{sh['Immunotherapy and targeted treatments'].iloc[-1]:.0f}%", "Figure 2")
    s15 = rd("S15_topic_share_by_funder", index_col=0)
    add("Results 3.4", "NIAID grants in AR", f"{s15.loc[pf.NIAID, 'Antibiotic resistance strategies']:.0f}%", "S15")
    add("Results 3.4", "NSFC grants in immunotherapy", f"{s15.loc['National Natural Science Foundation of China', 'Immunotherapy and targeted treatments']:.0f}%", "S15")
    add("Results 3.4", "NCI grants in immunotherapy", f"{s15.loc['National Cancer Institute', 'Immunotherapy and targeted treatments']:.0f}%", "S15")
    # researchers by inferred gender
    ppl = {}
    for n, g in zip(d["Researchers"], d["researcher_gender_list"]):
        names, gs = pf.split_list(n, ","), (str(g).split(";") if isinstance(g, str) else [])
        for i, p in enumerate(names):
            gi = gs[i].strip() if i < len(gs) else ""
            if ppl.get(p) in ("Male", "Female"):
                continue
            ppl[p] = gi if gi in ("Male", "Female") else "Unknown"
    gcount = pd.Series(ppl).value_counts()
    add("Results 3.4", "Named researchers", _int(len(ppl)), "analysis table / S7")
    add("Results 3.4", "Women", str(gcount.get("Female", 0)), "analysis table")
    add("Results 3.4", "Men", str(gcount.get("Male", 0)), "analysis table")
    s19 = rd("S19_researchers_by_gender_year").set_index("year")
    fem = s19.loc[2011:2022, "Female"].sum() / s19.loc[2011:2022, ["Male", "Female"]].sum().sum()
    add("Results 3.4", "Women 2011-2022", "about a third" if 0.30 <= fem <= 0.38 else f"{fem:.0%}", "S19 / Figure S6")
    t4 = rd("Table4_gender", index_col=0)
    for g in t4.index:
        add("Table 3", f"{g} grants", str(int(t4.loc[g, "Grants"])), "Table 4 (gender)")
        add("Table 3", f"{g} USD M", _m(t4.loc[g, "Total (USD M)"]), "Table 4 (gender)")
        add("Table 3", f"{g} share", _m(t4.loc[g, "Share of funding (%)"]), "Table 4 (gender)")
        add("Table 3", f"{g} median", _int(t4.loc[g, "Median (USD)"]), "Table 4 (gender)")
    s3 = rd("S3_gender_tests", index_col=0)
    main = s3[s3.Model.str.startswith("Main")]
    fo, mx = main.loc["Female only vs Male only"], main.loc["Mixed vs Male only"]
    add("Results 3.4", "Female-only gap", f"{-fo['Adjusted difference (%)']:.0f}%", "S3")
    add("Results 3.4", "Female-only CI", f"\u2212{-fo['95% CI low (%)']:.0f} to \u2212{-fo['95% CI high (%)']:.0f}", "S3")
    add("Results 3.4", "Female-only p", f"{fo['Regression p']:.3f}", "S3")
    py = s3[s3.Model.str.startswith("Amount per year")].loc["Female only vs Male only"]
    add("Results 3.4", "Per-year gap", f"{-py['Adjusted difference (%)']:.0f}%", "S3")
    add("Results 3.4", "Per-year CI", f"\u2212{-py['95% CI low (%)']:.0f} to \u2212{-py['95% CI high (%)']:.0f}", "S3")
    add("Results 3.4", "Mixed difference", f"\u2212{-mx['Adjusted difference (%)']:.0f}%", "S3")
    add("Results 3.4", "Mixed p", f"{mx['Regression p']:.2f}", "S3")
    add("Table 3", "Mixed CI", f"\u2212{-mx['95% CI low (%)']:.0f} to +{mx['95% CI high (%)']:.0f}", "S3")
    add("Results 3.4", "Single-grant researchers", _pct(key["researchers_single_grant_pct"]), "S7 / S36")
    add("Results 3.4", "Single-grant researchers (rounded)", f"{key['researchers_single_grant_pct']:.0f}%", "S7 / S36")
    lab = pf.classify_engagement(d, col="receiver_org_list", sep=";")
    add("Results 3.4", "Institutions in one year", f"{(lab == 'Transient').mean() * 100:.0f}%", "classify_engagement on institutions")

    # --- 3.5 robustness
    s31 = rd("S30_award_types", index_col=0)
    add("Results 3.5", "Training share, no amount", f"{s31.loc['Training award', 'Without an amount (%)']:.0f}%", "S30")
    add("Results 3.5", "Training share, priced", f"{s31.loc['Training award', 'With an amount (%)']:.0f}%", "S30")
    s32 = rd("S31_count_based_shares", index_col=0)
    add("Results 3.5", "GS share of grants, all", _pct(s32.loc["Recipients in the Global South (%)", "All relevant grants"]), "S31")
    add("Results 3.5", "GS share of grants, priced", _pct(s32.loc["Recipients in the Global South (%)", "With an amount"]), "S31")
    add("Results 3.5", "LMIC share of grants, all", _pct(s32.loc["Recipients in low or lower-middle income countries (%)", "All relevant grants"]), "S31")
    s33 = rd("S32_imputed_amount_scenarios", index_col=0)
    imp = s33[[c for c in s33.columns if c.startswith("Imputed")]]
    gs = imp.loc["Recipients in the Global South (%)"]
    add("Results 3.5", "GS funding share, imputed range", f"{gs.min():.1f}\u2013{gs.max():.1f}%", "S32")
    lm = s33.loc["Recipients in low or lower-middle income countries (%)"]
    add("Results 3.5", "LMIC funding share, max under checks", f"{np.ceil(lm.max() * 10) / 10:.1f}%", "S32")
    gr = s33.loc["Funding growth 1999-2022 (%/yr)"]
    add("Results 3.5", "Growth range", f"{gr.min():.0f}\u2013{gr.max():.0f}%", "S32")
    us = s33.loc["Funding from US funders (%)"]
    add("Results 3.5", "US range", f"{us.min():.0f}\u2013{us.max():.0f}%", "S32")
    ni = s33.loc["Funding from NIAID (%)"]
    add("Results 3.5", "NIAID range", f"{ni.min():.0f}\u2013{ni.max():.0f}%", "S32")
    s35 = rd("S34_gender_subsets", index_col=0)["Female-only vs male-only (%)"]
    allg = pd.concat([s35, pd.Series([py["Adjusted difference (%)"]])])
    add("Results 3.5", "Gender gap range", f"\u2212{-allg.max():.0f}% to \u2212{-allg.min():.0f}%", "S34, S3")
    add("Results 3.5", "Projects", str(key["projects"]), "S33")
    s34 = rd("S33_projects", index_col=0)
    diff = (s34["Projects"] - s34["Grant records"]).drop(["Units", "Units built from more than one record"]).abs().max()
    add("Results 3.5", "Max change from projects (points)", "one point" if diff <= 1 else f"{diff:.1f} points", "S33")
    s37 = rd("S36_robustness_summary", index_col=0).drop("Conclusion holds if").astype(float)
    add("Results 3.5", "Checks changing a conclusion", f"{key['robustness_checks_changing_a_conclusion']} of 40", "S36")
    add("Abstract", "Checks holding", f"{40 - key['robustness_checks_changing_a_conclusion']} of 40", "S36")
    add("Results 3.5", "Transient, start-year rule", f"{s37.loc['Main analysis', 'One-year-only researchers (%)']:.0f}%", "S7")
    add("Results 3.5", "Transient, full-span rule", _pct(s37.loc["Full-span engagement rule", "One-year-only researchers (%)"]), "S7")

    # --- discussion facts from data
    ssa = {"Uganda", "Tanzania", "South Africa", "Ghana", "Nigeria", "Kenya"}
    s11c = s11.drop("Total Global South")
    others = [c for c in s11c.sort_values("USD (M)", ascending=False).index if c in ssa and c != "South Africa"]
    add("Discussion 4.2", "Sub-Saharan recipients besides South Africa", " and ".join(others), "S11")

    # --- external facts (cited, not computed)
    for v, src in [("4.95", "[1] GRAM 2019"), ("6", "[7] ASM 2026"), ("1,392", "[18] CRS IF13131"), ("six", "[18] CRS IF13131")]:
        add("External", "Cited fact", v, src)
    return pd.DataFrame(R)


NUM = re.compile(r"(?<![\w.])[\u2212-]?\d[\d,]*(?:\.\d+)?")


def check_manuscript(md_path: Path, reg: pd.DataFrame) -> pd.DataFrame:
    """Numbers in the manuscript that no registry value accounts for.

    Allowed without the registry: years 1990-2030, reference numbers in brackets, section numbers, figure and table
    numbers, and numbers inside the reference list.
    """
    text = Path(md_path).read_text()
    text = text.split("## References")[0]
    text = re.sub(r"\\?\[[\d,\u2013 \\-]+\\?\]", " ", text)                          # citations [1], [3,4]
    text = re.sub(r"(Figures?|Tables?|Supplementary (Figures?|Tables?)|Section|S)\s*S?\d+[a-c]?(\s*[\u2013-]\s*S?\d+)?", " ", text)
    text = re.sub(r"^#+ .*$", " ", text, flags=re.M)                                   # headings
    text = re.sub(r"&#\d+;", " ", text)                                               # HTML entities
    text = re.sub(r"^\s*\d+\.\s", " ", text, flags=re.M)                              # numbered-list markers
    known = set()
    for v in reg["value"]:
        for tok in NUM.findall(str(v)):
            known.add(tok.lstrip("\u2212-"))
    rows = []
    for m in NUM.finditer(text):
        tok = m.group().lstrip("\u2212-").rstrip(",")
        plain = tok.replace(",", "")
        try:
            val = float(plain)
        except ValueError:
            continue
        if 1990 <= val <= 2030 and "." not in plain:
            continue
        if tok in known:
            continue
        ctx = text[max(0, m.start() - 60): m.end() + 40].replace("\n", " ")
        rows.append({"number": tok, "context": ctx})
    return pd.DataFrame(rows, columns=["number", "context"])
