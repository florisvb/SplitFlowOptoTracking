#!/usr/bin/env bash
# Copy each figure's final SVG (as listed in RunFigures/figures.yaml) into
# FinalFigures/svgs/, then render a PDF and a PNG of each into
# FinalFigures/pdfs/ and FinalFigures/pngs/.
#
# Usage:
#   RunFigures/collect_final_figures.sh               # all figures
#   RunFigures/collect_final_figures.sh fig5 fig1     # only these ids
#
# Environment variables (optional):
#   PNG_DPI=300            PNG resolution
#   INKSCAPE=/path/to/inkscape   converter to use (default: auto-detect)
# Converter: Inkscape if found (on PATH or /Applications/Inkscape.app), else
# cairosvg (needs the cairo library, e.g. `brew install cairo`).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

YAML="$RUN_DIR/figures.yaml"
OUT="$REPO_ROOT/FinalFigures"
PNG_DPI="${PNG_DPI:-300}"

# --- choose a converter --------------------------------------------------------
if [[ -z "${INKSCAPE:-}" ]]; then
    if command -v inkscape >/dev/null 2>&1; then
        INKSCAPE="$(command -v inkscape)"
    elif [[ -x /Applications/Inkscape.app/Contents/MacOS/inkscape ]]; then
        INKSCAPE=/Applications/Inkscape.app/Contents/MacOS/inkscape
    fi
fi
if [[ -n "${INKSCAPE:-}" ]]; then
    echo "Converter: $("$INKSCAPE" --version 2>/dev/null | head -n1)"
    to_pdf() { "$INKSCAPE" "$1" --export-type=pdf --export-filename="$2" >/dev/null 2>&1; }
    to_png() { "$INKSCAPE" "$1" --export-type=png --export-filename="$2" --export-dpi="$PNG_DPI" \
                   --export-background=white --export-background-opacity=1 >/dev/null 2>&1; }
else
    # cairosvg finds Homebrew's cairo only if told where it is.
    export DYLD_FALLBACK_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH:-}:/opt/homebrew/lib:/usr/local/lib"
    if ! python -c "import cairosvg" >/dev/null 2>&1; then
        echo "ERROR: no SVG converter found. Install Inkscape, or cairosvg + cairo." >&2
        exit 1
    fi
    echo "Converter: cairosvg (Inkscape not found)"
    to_pdf() { python -c "import sys,cairosvg; cairosvg.svg2pdf(url=sys.argv[1], write_to=sys.argv[2])" "$1" "$2"; }
    to_png() { python -c "import sys,cairosvg; cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[2], dpi=float(sys.argv[3]), background_color='white')" "$1" "$2" "$PNG_DPI"; }
fi

# --- read figures.yaml -> "id<TAB>name<TAB>svg" lines ---------------------------
ENTRIES="$(python - "$YAML" "$@" <<'EOF'
import sys, yaml
cfg = yaml.safe_load(open(sys.argv[1]))
wanted = set(sys.argv[2:])
entries = (cfg.get('main') or []) + (cfg.get('supplemental') or [])
ids = [e['id'] for e in entries]
unknown = wanted - set(ids)
if unknown:
    sys.exit(f"ERROR: unknown figure id(s): {', '.join(sorted(unknown))}")
names = [e['name'] for e in entries]
dupes = {n for n in names if names.count(n) > 1}
if dupes:
    sys.exit(f"ERROR: duplicate name(s) in figures.yaml: {', '.join(sorted(dupes))}")
for e in entries:
    if not wanted or e['id'] in wanted:
        print(f"{e['id']}\t{e['name']}\t{e['svg']}")
EOF
)"

mkdir -p "$OUT/svgs" "$OUT/pdfs" "$OUT/pngs"

ok=(); bad=()
while IFS=$'\t' read -r id name svg; do
    src="$REPO_ROOT/$svg"
    printf '%-34s ' "$id"
    if [[ ! -f "$src" ]]; then
        echo "MISSING  $svg"; bad+=("$id"); continue
    fi
    cp "$src" "$OUT/svgs/$name.svg"
    if ! to_pdf "$OUT/svgs/$name.svg" "$OUT/pdfs/$name.pdf"; then
        echo "PDF conversion failed"; bad+=("$id"); continue
    fi
    if ! to_png "$OUT/svgs/$name.svg" "$OUT/pngs/$name.png"; then
        echo "PNG conversion failed"; bad+=("$id"); continue
    fi
    echo "ok       -> $name.{svg,pdf,png}"
    ok+=("$id")
done <<< "$ENTRIES"

echo
echo "Collected ${#ok[@]} figure(s) into ${OUT#"$REPO_ROOT"/}/"
if [[ ${#bad[@]} -gt 0 ]]; then
    echo "Problems (${#bad[@]}): ${bad[*]}" >&2
    exit 1
fi
