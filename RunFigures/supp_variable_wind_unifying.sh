#!/usr/bin/env bash
# Supplemental: variable wind, unifying analysis
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: supp_variable_wind_unifying).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure supp_variable_wind_unifying "Supplemental: variable wind, unifying analysis"
D=FigureGeneration/Supplemental/supp_fig_variable_wind_unifying

run_notebook "$D" AB_varwind_figure_align_course_directions.ipynb
run_notebook "$D" C_variable_wind_slope_axis_ratio.ipynb
run_notebook "$D" D_MI_plots_var_wind.ipynb

end_figure
