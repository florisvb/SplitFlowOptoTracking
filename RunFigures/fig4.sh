#!/usr/bin/env bash
# Figure 4: autoencoder
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: fig4).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure fig4 "Figure 4: autoencoder"
D=FigureGeneration/Main/fig_4_autoencoder

# Writes test.svg (from f4_template.svg).
run_notebook "$D" f4_autoencoder.ipynb

end_figure
