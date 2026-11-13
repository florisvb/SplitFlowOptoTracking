#!/usr/bin/env bash
# Shared helpers for the per-figure scripts in RunFigures/.
# This file is sourced, not run directly.
#
# Environment variables (all optional):
#   DRY_RUN=1        only check that every notebook/script exists; execute nothing
#   NB_TIMEOUT=600   per-cell timeout in seconds for nbconvert (default -1 = none)
#   LOG_DIR=...      where executed notebooks + logs go (default RunFigures/logs)
#   USE_ACTIVE_ENV=1 use whatever python/jupyter is on PATH; don't auto-activate .venv

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$REPO_ROOT/RunFigures"
LOG_DIR="${LOG_DIR:-$RUN_DIR/logs}"
DRY_RUN="${DRY_RUN:-0}"
NB_TIMEOUT="${NB_TIMEOUT:--1}"

# --- Python environment ------------------------------------------------------
# Use an already-active virtualenv / non-base conda env; otherwise activate the
# repo's .venv if there is one.
if [[ "${USE_ACTIVE_ENV:-0}" != 1 && -z "${VIRTUAL_ENV:-}" \
      && ( -z "${CONDA_DEFAULT_ENV:-}" || "${CONDA_DEFAULT_ENV:-}" == base ) \
      && -f "$REPO_ROOT/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.venv/bin/activate"
fi

# --- Helpers -----------------------------------------------------------------
begin_figure() {   # begin_figure "<id>" "<description>"
    FIGURE_ID="$1"
    FIGURE_T0=$SECONDS
    echo "=== [$FIGURE_ID] $2"
}

end_figure() {
    echo "=== [$FIGURE_ID] finished in $((SECONDS - FIGURE_T0)) s"
}

# run_notebook <dir relative to repo root> <notebook.ipynb>
# Executes the notebook from its own directory (the notebooks use relative
# paths). The executed copy and the nbconvert log go to $LOG_DIR/<figure id>/,
# so the source notebook is not modified.
run_notebook() {
    local rel_dir="$1" nb="$2"
    local dir="$REPO_ROOT/$rel_dir" name="${2%.ipynb}"
    local out="$LOG_DIR/$FIGURE_ID"
    if [[ ! -f "$dir/$nb" ]]; then
        echo "ERROR: notebook not found: $rel_dir/$nb" >&2
        return 1
    fi
    if [[ "$DRY_RUN" == 1 ]]; then
        echo "  [dry-run] $rel_dir/$nb"
        return 0
    fi
    mkdir -p "$out"
    echo "  -> $rel_dir/$nb"
    local t0=$SECONDS
    if ! ( cd "$dir" && jupyter nbconvert --to notebook --execute "$nb" \
              --ExecutePreprocessor.timeout="$NB_TIMEOUT" \
              --ExecutePreprocessor.kernel_name=python3 \
              --output-dir "$out" --output "$name" ) > "$out/$name.log" 2>&1; then
        echo "  FAILED: $rel_dir/$nb  (log: ${out#"$REPO_ROOT"/}/$name.log)" >&2
        tail -n 15 "$out/$name.log" | sed 's/^/     | /' >&2
        return 1
    fi
    echo "     ok ($((SECONDS - t0)) s)"
}

# run_python <dir relative to repo root> <script.py> [args...]
run_python() {
    local rel_dir="$1" script="$2"; shift 2
    local dir="$REPO_ROOT/$rel_dir" out="$LOG_DIR/$FIGURE_ID"
    if [[ ! -f "$dir/$script" ]]; then
        echo "ERROR: script not found: $rel_dir/$script" >&2
        return 1
    fi
    if [[ "$DRY_RUN" == 1 ]]; then
        echo "  [dry-run] $rel_dir/$script $*"
        return 0
    fi
    mkdir -p "$out"
    echo "  -> $rel_dir/$script $*"
    local t0=$SECONDS
    if ! ( cd "$dir" && python "$script" "$@" ) > "$out/${script%.py}.log" 2>&1; then
        echo "  FAILED: $rel_dir/$script  (log: ${out#"$REPO_ROOT"/}/${script%.py}.log)" >&2
        tail -n 15 "$out/${script%.py}.log" | sed 's/^/     | /' >&2
        return 1
    fi
    echo "     ok ($((SECONDS - t0)) s)"
}

# Notebooks that fit the unifying-algorithm MIQP live need a full Gurobi license.
require_gurobi() {
    if ! python -c "import gurobipy; gurobipy.Model()" >/dev/null 2>&1; then
        echo "  WARNING: Gurobi license not usable (set GRB_LICENSE_FILE);" \
             "notebooks that fit the MIQP live will fail." >&2
        [[ "$DRY_RUN" == 1 ]] || return 1
    fi
}

# Notebooks that set matplotlib text.usetex=True need a system LaTeX.
require_latex() {
    if ! command -v latex >/dev/null 2>&1; then
        echo "  WARNING: 'latex' not on PATH; usetex notebooks will fail." >&2
        [[ "$DRY_RUN" == 1 ]] || return 1
    fi
}
