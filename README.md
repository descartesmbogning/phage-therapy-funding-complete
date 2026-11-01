# Global phage therapy research funding, 1999–2023

Code, results and documentation for the paper *Twenty-five years of phage therapy funding: rapid growth, narrow base*.

The analysis covers 802 phage therapy research grants with a recorded amount (USD 318.6 million) from a Dimensions search of 13 February 2024. A further 272 relevant grants without an amount are used in robustness checks. The method follows the phage therapy patent landscape study by Mbogning Fonkou & Kong, [*Nat. Biotechnol.* 42, 1781–1791 (2024)](https://www.nature.com/articles/s41587-024-02493-9).

**Every number, table and figure in the paper is produced by the code here.** Notebook 07 recomputes each number the paper quotes and checks the text against it.

## Quick start

**To look at the results**, no installation is needed. Open `outputs/figures/` and `outputs/tables/`. `outputs/tables/key_numbers.json` holds the headline values, and `outputs/tables/paper_numbers.csv` lists every number in the paper with its source.

**To rebuild everything**, you need the input files described in `data/README.md` (grant-level data cannot be shared publicly):
```bash
conda env create -f environment.yml
conda activate phagefund
# put the input files in data/raw/
./run_all.sh
```
`run_all.sh` runs the seven notebooks in order and writes every figure and table to `outputs/`. It takes about half an hour, mostly the topic model.

## Main findings
| Finding | Value | Source |
|---|---|---|
| Growth in grants per year, 1999–2022 (log-linear) | +12.2% per year (95% CI 10.0–14.5) | Fig. 1, Table S2 |
| Growth in funding per year, 1999–2022 (nominal USD) | +16.6% per year (95% CI 12.6–20.7) | Fig. 1, Table S2 |
| Growth in funding per year, constant 2023 USD | +14.1% per year (95% CI 10.2–18.2) | Table S28 |
| Share of funding from US funders | 47.7% | Fig. 5, Table S25 |
| Share of funding from NIAID (14% → 17% → 23% across three periods) | 21.0% | Table 2a, Table S25 |
| Concentration across funder countries (HHI, 0–10,000) | 2,501 (highly concentrated) | Table S24 |
| Funding received by the top 10% of recipient institutions | 53.4% (Gini 0.68) | Fig. 5, Table S24 |
| Funding from high-income countries | 98.3% | Fig. 4, Table 5 |
| Funding received by low- and lower-middle-income countries | 0.33% | Fig. 4, Table 5 |
| Funding received by the Global South (73% of it by China) | 2.1% | Tables S4, S11 |
| Global South share of all 1,074 relevant grants, counting grants | 17.5% | Table S31 |
| Grants linking Global North and Global South recipients | 7 of 802 | Table S26 |
| Female-only vs male-only grant size, adjusted for team size, grant length, year, funder and topic | −19% (95% CI −32 to −2) | Fig. 3, Table S3 |
| Researchers who held a single grant | 83.9% | Table S7 |
| Headline conclusions that hold across the 40 robustness checks | 37 of 40 | Fig. S12, Table S36 |

## What is in the repository
```
├── notebooks/                     run in this order by run_all.sh
│   ├── 02_topic_modelling.ipynb   topic model: coherence, stability, topic of each grant
│   ├── 01_preprocessing.ipynb     builds the analysis table (802 grants)
│   ├── 03_main_analysis.ipynb     Figures 1–4, Tables 1–5, Tables S1–S13
│   ├── 04_supplementary_figures.ipynb   Figures S2–S10, Tables S14–S23
│   ├── 05_concentration_and_sensitivity.ipynb   Figure 5, Tables S24–S28
│   ├── 06_robustness.ipynb        Figures S11–S12, Tables S29–S36
│   └── 07_paper_numbers.ipynb     every number quoted in the paper, checked against the text
├── src/
│   ├── preprocess.py              joins grants, institutions, gender and topics
│   ├── topics.py                  text cleaning, LDA, coherence, stability
│   ├── phagefund.py               growth, fractional counting, concentration, gender models, engagement
│   ├── robustness.py              award types, grants without an amount, imputation, projects
│   ├── paper_numbers.py           the paper's numbers and the manuscript check
│   └── figures.py                 figure style and plotting blocks
├── outputs/
│   ├── figures/                   Fig1–Fig5, FigS1–S12 (PNG 300 dpi and PDF; FigS10 is interactive HTML)
│   └── tables/                    Tables 1–5, S1–S36, key_numbers.json, paper_numbers.csv
├── data/
│   ├── README.md                  every input file, what it holds and how to obtain it
│   └── reference/                 public: country classification, CPI-U, cross-check templates
├── docs/methods.md                search query and methods in full
├── environment.yml
└── run_all.sh
```
`data/raw/`, `data/interim/` and `data/processed/` stay empty in the repository: they hold grant-level data and personal names (see `data/README.md`).

## Figure and table map
| Paper item | Notebook | Output |
|---|---|---|
| Figure 1: grants and funding per year | 03 | `Fig1_trends` |
| Figure 2: topic share by period | 03 | `Fig2_topics` |
| Figure 3: gender | 03 | `Fig3_gender` |
| Figure 4: income groups and countries | 03 | `Fig4_geography` |
| Figure 5: concentration (US and NIAID shares, Lorenz curve, top 10 funders by topic) | 05 | `Fig5_concentration` |
| Table 1: grants by period | 03 | `Table1_by_period.csv` |
| Table 2: top funders and recipients | 03 | `Table2a_top_funders.csv`, `Table2b_top_recipients.csv` |
| Table 3: topics | 03 | `Table3_topics.csv` |
| Table 4: gender | 03 | `Table4_gender.csv` |
| Table 5: income groups | 03 | `Table5_income_groups.csv` |
| Figure S1, Tables S8–S10: topic coherence, stability, topic words | 02 | `FigS1_topic_coherence`, `S8`–`S10` |
| Tables S1–S7: data quality, growth, gender tests, geography, engagement | 03 | `S1`–`S7` |
| Tables S11–S13: Global South by country, domestic vs cross-border, cross-border funders | 03 | `S11`–`S13` |
| Figure S2: grants per year, top 15 funders | 04 | `FigS2_funders_by_year`, `S14` |
| Figure S3: each funder's grants by topic | 04 | `FigS3_topic_by_funder`, `S15` |
| Figure S4: topics by recipient country | 04 | `FigS4_topic_by_recipient`, `S16` |
| Figure S5: topic similarity | 04 | `FigS5_topic_similarity`, `S17`, `S18` |
| Figure S6: named researchers by gender per year | 04 | `FigS6_researchers_by_gender`, `S19` |
| Figure S7: team gender by topic | 04 | `FigS7_team_gender_by_topic`, `S20` |
| Figure S8: researcher engagement over time | 04 | `FigS8_researcher_engagement`, `S21` |
| Figure S9: institution engagement by topic | 04 | `FigS9_institution_engagement_by_topic`, `S22` |
| Figure S10: funder country → recipient country flows | 04 | `FigS10_country_flows.html`, `S23` |
| Tables S24–S25: concentration; US and NIAID shares by period | 05 | `S24`, `S25` |
| Table S26: collaboration counts | 05 | `S26_collaboration.csv` |
| Table S27: growth and concentration without NIAID | 05 | `S27_without_niaid.csv` |
| Table S28: growth in constant 2023 USD | 05 | `S28_real_growth.csv` |
| Figure S11, Table S29: screening flow | 06 | `FigS11_screening_flow`, `S29_screening_flow.csv` |
| Table S30: award types, grants with and without an amount | 06 | `S30_award_types.csv` |
| Table S31: count-based shares including grants without an amount | 06 | `S31_count_based_shares.csv` |
| Table S32: dollar shares with imputed or recovered amounts | 06 | `S32_imputed_amount_scenarios.csv` |
| Table S33: yearly records merged into projects | 06 | `S33_projects.csv` |
| Table S34: gender gap in subsets | 06 | `S34_gender_subsets.csv` |
| Table S35: topic shares from topic probabilities | 06 | `S35_topic_probability_shares.csv` |
| Figure S12, Table S36: robustness summary | 06 | `FigS12_robustness`, `S36_robustness_summary.csv` |
| Every number quoted in the paper | 07 | `paper_numbers.csv` |

In the manuscript, Figure 6 is `FigS11_screening_flow`, Table 3 is `Table4_gender` with `S3_gender_tests`, and Supplementary Tables S37 and S38 are `Table3_topics` and `Table5_income_groups`.

## Paper numbers
`outputs/tables/paper_numbers.csv` lists every number the paper quotes: its section, what it measures, the value as printed (computed, never typed) and its source table or code. When the manuscript text is available at `manuscript/manuscript.md`, notebook 07 also reports any number in the text without code behind it, and any computed value the text does not print as computed.

## Limitations
- **Coverage.** Dimensions covers NIH, European and Japanese funders well but many national funders in low- and middle-income countries poorly.
- **Missing amounts.** 272 relevant grants have no amount, mostly from Brazil, Russia and Belgium, and 43% of them are training awards. Dollar shares are shares of *recorded* funding (Tables S30–S32).
- **Amounts.** Nominal USD as converted by Dimensions; constant-dollar growth is in Table S28.
- **Engagement.** Engagement labels depend on the activity rule (Table S7); the share of researchers with a single grant does not.
- **Gender.** Inferred from first names, so binary.
- **Topics.** About 60% of grants keep the same topic when the random seed changes (Table S9). Read topic results as trends (Table S35).

## Licence and citation
Code: MIT (`LICENSE`). Cite with `CITATION.cff`.
Grant-level data are not redistributed (Dimensions terms of use); see `data/README.md`.
