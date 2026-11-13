#!/usr/bin/env bash
# Supplemental: unifying analysis, all WT split-flow flies
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: supp_unifying_analysis_flies).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure supp_unifying_analysis_flies "Supplemental: unifying analysis, all WT split-flow flies"
D=FigureGeneration/Supplemental/sup_fig_unifying_analysis

run_notebook "$D" A_figure_align_course_directions_flies_allwtsplitflow.ipynb
run_notebook "$D" B_figure_unifying_algo_results_allwtsplitflow.ipynb
run_notebook "$D" C_MI_plots_flies_allwtsplitflow.ipynb

end_figure
