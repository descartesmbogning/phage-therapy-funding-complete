# Methods

## 1. Search (Dimensions, 13 Feb 2024, no date limit)
```
(title:(Bacteriophage OR Bacteriophages OR phage OR phages OR "phago virus" OR "phagovirus" OR siphophage* OR Microbacteriophage* OR Mycobacteriophage* OR Mycobacteriophage OR Microbacteriophage OR multiphage* OR multiphage OR "multi-phage*" OR "phage-based" OR "bacteriophage-based" OR phageome OR phagotherapy OR "Monophage Therapy" OR "Polyphage" OR Coliphage OR prophage OR staphylophage OR phageome OR PHAGOTHERAPY)) AND ((abstract:(therap* OR Therapy OR THERAPEUTIC OR treat* OR Treatment OR antibacterial OR antibacteria* OR "anti-bacterial" OR antimicrobial OR cocktail* OR cocktail OR prophylax* OR Prophylaxis OR Antifungal OR Antiviral OR PHAGOTHERAPY)) OR (title:(therap* OR Therapy OR THERAPEUTIC OR treat* OR Treatment OR antibacterial OR antibacteria* OR "anti-bacterial" OR antimicrobial OR cocktail* OR cocktail OR prophylax* OR Prophylaxis OR Antifungal OR Antiviral OR PHAGOTHERAPY)))
```

## 2. Screening (notebook 06, Figure S11, Table S29)
| Step | Removed | Left |
|---|---|---|
| Dimensions search | | 1,521 |
| Not about therapeutic use of phages (titles and abstracts) | 391 | 1,130 |
| No funding amount in Dimensions | 312 | 818 |
| Start year outside 1999–2023 | 16 | 802 |

Dollar results use the 802 grants with a recorded amount. The 272 relevant grants without an amount that started in 1999–2023 are used in the robustness checks (section 7). The counts are read from the screening columns of the export (`includes ?`, `funding?`), so the flow diagram is generated, not typed.

## 3. Enrichment
- **Institutions.** Harmonised with GRID/ROR in Dimensions, then checked by hand. Missing co-recipients were added.
- **Countries.** Funder and recipient countries get a World Bank income group (fiscal year 2024) and a Global North/South label (World Population Review 2024) from one table, `data/reference/country_classification.csv`.
  - Georgia, Russia, Ukraine, Singapore and Qatar are labelled differently by different sources; they keep the source label and are flagged in the table.
  - The European Commission and the European Research Council are coded as funder country "European Union".
- **Gender.** Researcher gender is inferred from first names with Gender API; ambiguous names were checked by hand.

## 4. Topics (notebook 02)
1. **Text.** Title, abstract and keywords, using the English translations.
2. **Stopwords.** WordCloud list, NLTK stopwords in all languages, and "amp".
3. **Duplicates.** Exact duplicate texts are fitted once; each duplicate takes its twin's topic.
4. **Lemmas.** Nouns, adjectives and verbs only (spaCy `en_core_web_md`).
5. **Term counts.** Tokens longer than 2 characters, `min_df=50`, `max_df=0.75`.
6. **LDA.** scikit-learn, online learning, `learning_offset=50`, seed 111.
7. **Choice of k.** Mean c_v coherence over the top 30 words, k = 2–12; highest at k = 5 (Figure S1).
8. **Labels.** Topics were labelled from their top words and the abstracts that fit each topic best:
   - 0: Bacterial genetics and mechanisms
   - 1: Antibiotic resistance strategies
   - 2: Immunotherapy and targeted treatments
   - 3: one grant, reported as Unclassified
   - 4: Infectious disease control
9. **Stability.** Refitting with five other seeds keeps 51–68% of grants in the same topic (Table S9), so results are reported for topic totals, not single grants.
10. **Stored assignment.** Model fits vary slightly with library versions, so the topic of each grant used in the paper is stored (`data/raw/lda_topic_assignment.pkl`). Notebook 02 refits the model, compares the refit with the stored assignment, and saves the refit's topic probabilities for the robustness checks.

## 5. Analysis (notebook 03)
- **Growth.** Log-linear fit of yearly counts and USD totals over 1999–2022, reported as % per year with a 95% CI. 2023 is excluded from the fit because of indexing lag.
- **Fractional counting.** A grant with *k* recipient institutions gives 1/*k* of its amount to each one, and through it to that institution's country and income group. Each grant has one funder.
- **Domestic vs cross-border.** A grant is domestic when every recipient institution is in the funder's country (Table S12): 88.7% of funding. Splitting multi-country grants fractionally instead gives 91.4%, because 30 of the 65 cross-border grants also include a recipient in the funder's country.
- **Gender.**
  - Exclusive groups by the genders of named researchers: male only, female only, mixed, and gender unknown (59 grants list no researcher; 1 lists researchers whose gender could not be inferred).
  - Groups are compared with Mann–Whitney tests.
  - Main model: OLS of log(amount) on group, log team size, log grant length (years), start year, funder (funders with fewer than 10 grants pooled) and topic, with HC1 robust errors. Table S3 also reports the amount per year of grant and a simple model (team size, US funder, start year).
- **Engagement types** (as in the patent study). In each year an entity is active it is a **Newcomer** (not active before, active later, or first seen in 2023), **Continuant** (active before and after), **Terminator** (active before, not after) or **Transient** (active in one year only). The summary uses each entity's last label. Because the shares depend on whether a grant counts in its start year only or in every year it runs (Table S7), the share of researchers who held a single grant is the main retention measure.

## 6. Concentration, collaboration and sensitivity (notebook 05)
- **Concentration.**
  - Herfindahl–Hirschman index (HHI): the sum of squared percentage shares, 0–10,000, for funders, funder countries and recipient countries (fractional counting). By convention, above 2,500 is highly concentrated and 1,500–2,500 moderately concentrated.
  - Gini coefficient and the share received by the top 10% of recipient institutions (fractional counting). With 525 institutions, the top 10% is the 52 largest.
  - Shares from US funders and from NIAID, for 1999–2008, 2009–2015 and 2016–2023.
- **Collaboration.** Counts only: grants with more than one recipient institution or country, grants linking Global North and Global South recipients, co-investigator pairs.
- **Without NIAID.** Growth, the US share and the HHIs re-estimated with NIAID grants removed.
- **Constant dollars.** Amounts converted to 2023 USD with the annual average CPI-U (all items, U.S. city average, 1982–84 = 100), by grant start year (`data/reference/cpi_u_annual.csv`: 1999–2021 from the BLS CPI-U historical table; 2022 = 292.655 and 2023 = 304.702 from BLS data as published by the Idaho Department of Labor). Dimensions had already converted other currencies to USD, so only US inflation is removed.

## 7. Robustness (notebook 06)
- **Award types.** Each record is classed as a research grant, a training award (studentship, scholarship, fellowship, thesis, graduate-programme record) or capacity funding (USDA formula funds) from its programme name and source link (`robustness.award_type`). 43% of the grants without an amount are training awards, against 8% of grants with one (Table S30).
- **Grants without an amount.** The 272 relevant grants with no amount enter three checks:
  - count-based shares, each grant counted once and split equally across its recipient countries (Table S31);
  - imputation: each missing amount takes the median (central), 25th percentile (low) or 75th percentile (high) of priced grants from the same funder (at least 3), else the same funder country and award type, else the same award type. Training awards are 0 in the low and central scenarios and the 25th percentile of priced training awards in the high scenario (Table S32);
  - recovery: amounts found by hand on funder websites, saved in `data/raw/recovered_amounts.csv`, are used when present.
- **Projects.** Records with the same funder and the same English (translated) title whose years follow on are merged into one project, with amounts summed (Table S33).
- **Other definitions.**
  - Amounts spread evenly over grant years.
  - Income group at grant start: China lower-middle income until 2009 and Thailand until 2010 (to be checked against the World Bank historical classification, OGHIST).
  - OECD DAC list of ODA recipients (2024–25) instead of Global South.
  - Engagement: share of researchers with one active year among those first seen 2001–2019, and share with a single grant.
  - Topic shares from the refitted model's topic probabilities (Table S35).
  - Gender model without funders in Japan and China (name inference is less reliable there) and without training awards (Table S34).
- **Validation samples and cross-checks.** The notebook writes private samples for a second screener (15% of 1,521, stratified), hand-coding of topics (100 grants) and checking of inferred gender (100 names, blind), and reports Cohen's kappa once they are filled. Public templates hold yearly NIH totals (for comparison with NIH RePORTER) and World Bank price level ratios (for a PPP check).
- **Summary.** Figure S12 and Table S36 show each headline under each check, with the rule used to judge whether its conclusion holds.

## 8. Paper numbers (notebook 07)
`src/paper_numbers.py` recomputes every number quoted in the manuscript and records its source (`outputs/tables/paper_numbers.csv`). Notebook 07 checks the manuscript text against it in both directions.
