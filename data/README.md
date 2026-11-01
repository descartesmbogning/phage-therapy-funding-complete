# Data

Only `reference/` is in the repository. The other folders hold grant-level data that cannot be shared: the Dimensions terms of use do not allow the export to be redistributed without written approval from Digital Science, and the researcher file contains personal names with inferred gender.

## Inputs (`raw/`, private)
| File | Rows | Content | How to obtain |
|---|---|---|---|
| `dimensions_export_2024-02-13.xlsx` | 1,521 | The Dimensions export, with the screening columns `includes ?` (1 relevant; 0 or −1 not relevant) and `funding?` ("no fund" = no amount) | Run the query in `docs/methods.md` (Dimensions subscription), or ask the authors |
| `grants_screened.xlsx` | 818 | Relevant grants with an amount, hand-enriched (funder income group and North/South) | As above |
| `grants_topic_corpus.xlsx` | 818 | Titles, abstracts and keywords of the same grants, used by the topic model | As above |
| `receiver_metadata.xlsx` | 535 | One row per recipient institution: country, region, type, income group, North/South | Authors (no personal data; can be shared on request) |
| `gender_lookup.xlsx` | ~1,150 | Researcher name and inferred gender (Gender API plus manual checks) | Authors only |
| `lda_topic_assignment.pkl` | 799 | Topic of each grant from the LDA model used in the paper (k = 5) | Authors |
| `original/data_clean_2024-03.xlsx` | 1,130 / 818 | The screening workbook (relevant grants; grants with an amount) | Authors |

Optional, filled by hand (see below): `recovered_amounts.csv`, `validation_screening.xlsx`, `validation_topics.xlsx`, `validation_gender.xlsx`.

## Public reference tables (`reference/`)
| File | Content |
|---|---|
| `country_classification.csv` | Country → World Bank income group (FY2024), Global North/South, OECD DAC ODA-recipient status, with notes where sources disagree |
| `cpi_u_annual.csv` | Annual average CPI-U 1999–2023 (BLS), for constant-dollar growth |
| `nih_reporter_crosscheck.csv` | Yearly NIH totals in this dataset, with an empty column for the same search in NIH RePORTER |
| `ppp_price_level_2023.csv` | Recipient countries, with an empty column for the World Bank price level ratio (indicator PA.NUS.PPPC.RF) |

## Generated files (private)
| File | Written by |
|---|---|
| `interim/topic_assignments.csv` | 02: Grant ID and topic |
| `interim/topic_probabilities_refit.csv` | 02: topic probabilities of the refitted model |
| `processed/phage_funding_analysis.csv` | 01: the analysis table (802 grants) |
| `interim/amount_recovery_worksheet.xlsx` | 06: grants without an amount, with the funder's page; fill and save as `raw/recovered_amounts.csv` (columns `Grant ID`, `recovered_usd`) |
| `interim/validation_screening_sample.xlsx` | 06: stratified 15% of the 1,521 records for a second screener; save filled as `raw/validation_screening.xlsx` |
| `interim/validation_topics_sample.xlsx` | 06: 100 grants (25 per topic) to hand-code; save filled as `raw/validation_topics.xlsx` |
| `interim/validation_gender_sample.xlsx` | 06: 100 researcher names (blind) to check; save filled as `raw/validation_gender.xlsx` |

Notebook 08 writes only public, aggregate files: `outputs/explorer/cube.csv`, `docs/data_dictionary.csv` and `datapackage.json`.

Re-run notebook 06 after adding any filled file; it uses them automatically.
