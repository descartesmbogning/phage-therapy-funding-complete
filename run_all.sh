#!/usr/bin/env bash
# Rebuild topics, the analysis table, and every figure and table, in order.
set -euo pipefail
cd "$(dirname "$0")/notebooks"
for nb in 02_topic_modelling 01_preprocessing 03_main_analysis 04_supplementary_figures 05_concentration_and_sensitivity 06_robustness 07_paper_numbers; do
  echo "Running $nb"
  jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 "$nb.ipynb"
done
echo "Done. See outputs/figures and outputs/tables."
