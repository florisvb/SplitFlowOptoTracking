#!/usr/bin/env bash
# Figure 2: wind tunnel and CFD
# Runs the plotting notebooks for this figure (no data re-analysis).
# Final SVG: see figures.yaml (id: fig2).
# Needs Data/wind_tunnel_data/ and Data/CFD/2D_PlanarSlices/XZslice/ from Dryad.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

begin_figure fig2 "Figure 2: wind tunnel and CFD"
D=FigureGeneration/Main/fig_2_wind_tunnel_CFD

# Order matters: this notebook starts fig2_tunnel_methods.svg from
# fig2_template.svg and fills panels B, C, E, F, G and H ...
run_notebook "$D" fig2_wind_tunnel_plots.ipynb
# ... and this one adds panel J to the same file.
run_notebook "$D" fig2_CFD.ipynb

end_figure
