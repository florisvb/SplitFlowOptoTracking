#!/usr/bin/env bash
# Figure 1: unifying-algorithm math
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: fig1).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure fig1 "Figure 1: unifying-algorithm math"
D=FigureGeneration/Main/fig_1_math_figure

require_latex  # B sets text.usetex=True

run_notebook "$D" A_figure_math_affine_explanation.ipynb
run_notebook "$D" B_figure_math_consolidate_params.ipynb

# Not included: C_f1_example_trajectories.ipynb draws into an "algorithms" layer of
# unifying_math_v2.svg, which is not part of the current Figure 1 (unifying_math_v4.svg).

end_figure
