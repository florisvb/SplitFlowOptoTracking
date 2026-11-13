#!/usr/bin/env bash
# Figure 5: unifying-algorithm analysis
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: fig5).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure fig5 "Figure 5: unifying-algorithm analysis"
D=FigureGeneration/Main/fig_5_unifying_algo_analysis/generate_figure_5

require_gurobi  # A and B fit the MIQP live

# Order matters: each notebook fills a different layer of the shared
# unifying_analysis_translationTrue.svg.
run_notebook "$D" A_figure_math_explanation.ipynb
run_notebook "$D" B_figure_example_trajectories.ipynb
run_notebook "$D" C_figure_align_course_directions.ipynb
run_notebook "$D" D_figure_unifying_algo_results_slope_axis.ipynb
run_notebook "$D" E_variable_wind_slope_axis_ratio.ipynb
run_notebook "$D" FG_variable_wind_quantification.ipynb
# Fills the r2_* layers of the same SVG.
run_notebook "$D" r2_distribution_summary.ipynb

end_figure
