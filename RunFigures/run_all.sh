#!/usr/bin/env bash
# Run every per-figure script in RunFigures/, in manuscript order.
#
# Usage:
#   RunFigures/run_all.sh             # run everything (slow: hours)
#   RunFigures/run_all.sh --dry-run   # only check that all notebooks/scripts exist
#   RunFigures/run_all.sh fig5 supp_own_fit   # run only these figures
#
# A failing figure does not stop the others; a summary is printed at the end
# and the exit code is non-zero if any figure failed.
# Afterwards, run RunFigures/collect_final_figures.sh to gather the SVG/PDF/PNGs.

set -uo pipefail
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FIGURES=(
    fig1 fig2 fig3 fig4 fig5
    supp_tunnel_methods
    supp_altitude_response
    supp_course_direction
    supp_extra_real_trajectories
    supp_variable_wind_trajectories
    supp_synthetic_trajectories
    supp_sorted_trajectories
    supp_unifying_analysis_flies
    supp_variable_wind_unifying
    supp_variable_wind_surge
    supp_shuffled_synthetic
    supp_own_fit
    supp_all_animal_trajectories
    supp_all_animal_slopes
)

SELECTED=()
for arg in "$@"; do
    case "$arg" in
        --dry-run) export DRY_RUN=1 ;;
        -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
        *) SELECTED+=("${arg%.sh}") ;;
    esac
done
[[ ${#SELECTED[@]} -gt 0 ]] && FIGURES=("${SELECTED[@]}")

passed=(); failed=()
t0=$SECONDS
for fig in "${FIGURES[@]}"; do
    script="$RUN_DIR/$fig.sh"
    if [[ ! -f "$script" ]]; then
        echo "ERROR: no script $fig.sh" >&2; failed+=("$fig"); continue
    fi
    if bash "$script"; then passed+=("$fig"); else failed+=("$fig"); fi
    echo
done

echo "================ summary ($((SECONDS - t0)) s) ================"
echo "passed (${#passed[@]}): ${passed[*]:-}"
echo "failed (${#failed[@]}): ${failed[*]:-}"
[[ ${#failed[@]} -eq 0 ]]
