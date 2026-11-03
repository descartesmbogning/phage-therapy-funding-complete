# Datasheet: global phage therapy research funding, 1999–2023 (aggregate tables)

This datasheet follows the questions of *Datasheets for Datasets* (Gebru et al., Communications of the ACM, 2021), shortened to what applies to aggregate tables.

## Motivation
- **Why was it created?** To measure who funds phage therapy research, how much, where the money goes, and on what topics. Funding for this field had not been measured globally at grant level.
- **Who created it?** Maxime Descartes Mbogning Fonkou (CognosX), with Nathan Yanwou, Roland Bamou and Idriss Tsayem N.
- **Funding:** see the paper's funding statement.

## Composition
- **What do the files hold?** Aggregate tables only:
  - the tables behind every figure and number in the paper (`outputs/tables/`);
  - the data behind the interactive explorer (`outputs/explorer/cube.csv`);
  - public reference tables (`data/reference/`).
- **What is the unit?** Summed grants and US dollars by group (year, country, funder, topic, income group, team type).
  - In the explorer cube, a grant shared by k recipient institutions counts 1/k for each.
  - Many cube rows describe a single grant, because the cube is cross-classified by year, funder, recipient country and topic.
- **Scope:** 802 grants with a recorded amount (USD 318.6 million) that started in 1999–2023. They come from 1,521 records returned by a Dimensions search on 13 February 2024. A further 272 relevant grants have no amount; they appear only in the sensitivity tables (S30–S32).
- **What is left out?**
  - grant-level records, grant titles and grant IDs;
  - researcher names and the inferred gender of individuals;
  - the Dimensions export itself.
- **Missing values:** see Table S1 (completeness of the analysis table).
- **Sensitive data:** none at the individual level. Team gender appears only as counts and shares of grants.

## Collection
- **Source:** the Dimensions grants database (Digital Science), searched on 13 February 2024. The full query is in `docs/methods.md`.
- **Screening:** titles and abstracts were screened by hand for therapeutic use of phages (Figure S11, Table S29).
- **Enrichment:**
  - institutions harmonised with GRID/ROR and checked by hand;
  - country income groups from the World Bank (FY2024); Global North/South from World Population Review (2024);
  - topics from LDA (k = 5);
  - gender inferred from first names (Gender API, with manual checks).
- **Ethics:** see the paper's ethics statement.

## Preprocessing
- Amounts are nominal US dollars as converted by Dimensions. Constant-dollar growth uses the US CPI-U (Table S28).
- Each grant is dated by its start year. 2023 is incomplete because of indexing lag.
- Every step is in the notebooks (`notebooks/01`–`08`), and the build stops if totals do not match the paper.

## Uses
- **Suitable for:**
  - describing and comparing funding by country, funder, topic and period;
  - reproducing the paper's tables and figures;
  - teaching;
  - linking to other funding or output data at an aggregate level.
- **Not suitable for:**
  - judging individual researchers or institutions;
  - estimating total phage therapy investment, since amounts are recorded amounts only and private funding is mostly absent;
  - causal claims.
- **Known biases:**
  - Dimensions covers NIH, European and Japanese funders well, but many national funders in low- and middle-income countries poorly.
  - Funders in Brazil and Russia often report no amount.
  - Name-based gender inference is binary and less reliable for some languages.
  - Topic assignments vary between model runs (Table S9).

## Distribution
- **Where:** GitHub (`descartesmbogning/phage-therapy-funding-complete`), archived on Zenodo with a DOI for each release. The explorer is at https://cognosx.ca/phage-funding.
- **Licence:** data CC BY 4.0 (`LICENSE-data.md`); code MIT (`LICENSE`).
  - The tables are summaries derived from Dimensions; the Dimensions export is not redistributed.

## Maintenance
- **Maintainer:** Maxime Descartes Mbogning Fonkou (contact@cognosx.ca).
- **Updates:** new releases are listed in `CHANGELOG.md`, each with its own Zenodo version DOI. Errors can be reported as GitHub issues.
- **Technical note:** eight tables (Tables 5, S1, S2, S4, S5, S16, S18, S28) have an unnamed first column that holds row labels. `docs/data_dictionary.csv` describes it. Frictionless validation reports it as a blank header; all other files validate.
