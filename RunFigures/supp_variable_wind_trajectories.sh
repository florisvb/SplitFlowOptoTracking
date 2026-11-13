#!/usr/bin/env bash
# Supplemental: variable-wind sample trajectories
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: supp_variable_wind_trajectories).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure supp_variable_wind_trajectories "Supplemental: variable-wind sample trajectories"
D=FigureGeneration/Supplemental/sup_fig_extra_real_trajectories

run_python "$D" plot_variablewind_trajectories.py

end_figure
