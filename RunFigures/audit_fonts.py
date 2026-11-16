"""Audit font sizes and typefaces in figure SVGs.

Reports every visible text item with its *rendered* size in points (all parent
transforms applied) and its font family. Handles:

  - Inkscape <text>/<tspan> (including inherited / percentage font sizes)
  - matplotlib text saved as live text (svg.fonttype='none')
  - matplotlib text saved as glyph paths (<use xlink:href="#Helvetica-2a">)
  - MathJax equations inserted in Inkscape (MJX-* glyphs)

Text baked into raster <image>s, or already converted to plain paths, cannot be
measured; check those by eye.

Note: an Inkscape family of generic `sans-serif` is resolved at export time
(on macOS it becomes Verdana in the PDF) -- treat it as a mismatch.

Usage (from the repo root):

    python RunFigures/audit_fonts.py                      # summary of FinalFigures/svgs/*.svg
    python RunFigures/audit_fonts.py Figure_5.svg         # names resolve in FinalFigures/svgs/
    python RunFigures/audit_fonts.py path/to/any.svg --outliers
    python RunFigures/audit_fonts.py --tsv > fonts.tsv    # one row per text item

Options:
    --outliers   list only items whose size is not 6/8/10 pt, whose family is not
                 Helvetica/Arial, or whose aspect ratio is distorted (>3%).
                 Computer Modern is accepted on pi labels (house style).
    --tsv        dump every item as tab-separated rows instead of a summary
    --all        include hidden and off-page (pasteboard) items
    --sizes      allowed sizes for --outliers (default "6,8,10")
    --families   allowed families for --outliers (default "Helvetica,Arial")

Requires fontTools (installed with matplotlib) only for decoding the text of
glyph-path labels; sizes and families are measured without it.

Glyph-path text is decoded back to characters on a best-effort basis (matplotlib
versions differ in how they name glyphs); Computer Modern glyphs (π ticks) often
are decoded via matplotlib's bundled BaKoMa fonts (π, −, digits).
"""
import argparse
import csv
import logging
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DIR = REPO / 'FinalFigures' / 'svgs'

SVG = '{http://www.w3.org/2000/svg}'
XL = '{http://www.w3.org/1999/xlink}href'
INK = '{http://www.inkscape.org/namespaces/inkscape}'

# Glyph ids written by matplotlib (optionally prefixed by figurefirst, e.g.
# "r2_sham_wt_Helvetica-13", optionally suffixed by Inkscape de-duplication "-3")
# and by MathJax ("MJX-48-NCM-N-63").
GLYPH_RE = re.compile(
    r'#(?:[A-Za-z0-9]+_)*?'
    r'(MJX-\d+-\w+-\w+|DejaVuSans(?:-Bold|-Oblique)?|DejaVuSerif(?:-Italic|-Bold)?'
    r'|Cmmi10|Cmr10|Cmsy10|Cmex10|Helvetica(?:-Bold|-Oblique)?|NimbusSanL-Regu|NimbusSanL-Bold'
    r'|Times-Roman|Times-Italic|Times-Bold|Arial\w*)'
    r'-([0-9a-fA-F]+)(?:-\d+)?$')
MPL_HINT = re.compile(r'^(figure_\d|axes_\d|text_\d|xtick_|ytick_|legend_|matplotlib|patch_|line2d_)')
CTRL = re.compile(r'[\x00-\x1f⁠-⁯]')
logging.getLogger('fontTools').setLevel(logging.ERROR)  # harmless warnings from Helvetica.ttc

FIELDS = ['file', 'kind', 'source', 'layer', 'id', 'size_pt', 'family', 'weight', 'style',
          'aniso', 'hidden', 'on_page', 'x_mm', 'y_mm', 'text']


# ---- glyph decoding (best effort, only used for readable output) -----------
def _font_files():
    try:
        import matplotlib
        mpl = os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf')
    except ImportError:
        mpl = ''
    return {
        'DejaVuSans': (os.path.join(mpl, 'DejaVuSans.ttf'), None),
        'DejaVuSerif': (os.path.join(mpl, 'DejaVuSerif.ttf'), None),
        'Cmmi10': (os.path.join(mpl, 'cmmi10.ttf'), None),
        'Cmr10': (os.path.join(mpl, 'cmr10.ttf'), None),
        'Cmsy10': (os.path.join(mpl, 'cmsy10.ttf'), None),
        'Helvetica': ('/System/Library/Fonts/Helvetica.ttc', 0),
    }


_FONTFILES = None
_rev = {}


def _revmap(fam):
    """glyph index -> character for a font family."""
    global _FONTFILES
    if fam in _rev:
        return _rev[fam]
    if _FONTFILES is None:
        _FONTFILES = _font_files()
    m = {}
    path, idx = _FONTFILES.get(fam, (None, None))
    if path and os.path.exists(path):
        try:
            from fontTools.ttLib import TTFont
            f = TTFont(path, fontNumber=idx) if idx is not None else TTFont(path)
            name2cp = {}
            for cp, gn in f.getBestCmap().items():
                name2cp.setdefault(gn, cp)
            for i, gn in enumerate(f.getGlyphOrder()):
                if gn in name2cp:
                    m[i] = chr(name2cp[gn])
        except Exception:
            pass
    _rev[fam] = m
    return m


CM_FAMILIES = ('Cmmi10', 'Cmr10', 'Cmsy10', 'Cmex10')
_cm_maps = {}


def _cm_decode(fam, codes):
    """Computer Modern (matplotlib's BaKoMa fonts) -> characters via glyph names.

    Depending on the matplotlib version the glyph id is a character code or a
    glyph index; both are tried and the more math-like reading is kept."""
    if fam not in _cm_maps:
        by_code, by_index = {}, {}
        try:
            import matplotlib
            from fontTools.agl import toUnicode
            from fontTools.ttLib import TTFont
            ft = TTFont(os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf', fam.lower() + '.ttf'))

            def ch(gn):
                return {'minus': '−'}.get(gn) or toUnicode(gn) or '?'
            by_code = {cp: ch(gn) for cp, gn in ft.getBestCmap().items()}
            by_index = {i: ch(gn) for i, gn in enumerate(ft.getGlyphOrder())}
        except Exception:
            pass
        _cm_maps[fam] = (by_code, by_index)
    by_code, by_index = _cm_maps[fam]
    if not by_code:
        return None
    reads = [''.join(m.get(c, '?') for c in codes) for m in (by_code, by_index)]
    return max(reads, key=lambda r: sum(2 * (c in 'π−0123456789') + (c in '+=/()') for c in r) - 2 * r.count('?'))


def decode(fam, hexes):
    codes = [int(h, 16) for h in hexes]
    if fam.startswith('Cm'):
        cm = _cm_decode(fam, codes)
        if cm is not None:
            return cm
    as_char = ''.join(chr(c) for c in codes)                       # older matplotlib: char code
    rm = _revmap(fam)
    as_index = ''.join(rm.get(c, '?') for c in codes)              # newer matplotlib: glyph index
    as_mac = ''.join(chr(c + 29) if 0 < c < 0x60 else '?' for c in codes)  # Mac standard glyph order

    def score(s):
        common = 'etaoinshrdlcumpfgwybvETAOINSHRDLCUMPFGWYBV0123456789 .-−()°%'
        return sum((ch in common) * 2 + ch.isalnum() for ch in s) / max(len(s), 1)

    if fam.startswith('Cm'):
        return as_index if rm else as_char
    return max([as_index, as_char, as_mac], key=score)


# ---- transforms ------------------------------------------------------------
I = (1, 0, 0, 1, 0, 0)


def mul(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1],
            a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def parse_tf(s):
    m = I
    if not s:
        return m
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', s):
        v = [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?', args)]
        if name == 'matrix':
            t = tuple(v)
        elif name == 'translate':
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale':
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate':
            a = math.radians(v[0])
            c, s_ = math.cos(a), math.sin(a)
            t = (c, s_, -s_, c, 0, 0)
            if len(v) == 3:
                t = mul(mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == 'skewX':
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == 'skewY':
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = mul(m, t)
    return m


def scales(m):
    return math.hypot(m[0], m[1]), math.hypot(m[2], m[3])


# ---- style -----------------------------------------------------------------
def style_of(el):
    d = {}
    for k in ('font-size', 'font-family', 'font-weight', 'font-style', 'display', 'visibility', 'opacity'):
        if el.get(k) is not None:
            d[k] = el.get(k)
    for part in (el.get('style') or '').split(';'):
        if ':' not in part:
            continue
        k, v = (x.strip() for x in part.split(':', 1))
        if k == 'font':  # shorthand, e.g. "400 8px 'Helvetica'"
            mm = re.match(r"(?:(italic|oblique|normal)\s+)?(?:(bold|normal|\d00)\s+)?([\d.]+px)\s+(.*)", v)
            if mm:
                if mm.group(1):
                    d['font-style'] = mm.group(1)
                if mm.group(2):
                    d['font-weight'] = mm.group(2)
                d['font-size'] = mm.group(3)
                d['font-family'] = mm.group(4)
        else:
            d[k] = v
    return d


def size_px(val, parent):
    m = re.match(r'([-+\d.eE]+)\s*(px|pt|%|em)?', val.strip())
    if not m:
        return parent
    x = float(m.group(1))
    u = m.group(2) or 'px'
    return {'px': x, 'pt': x * 96 / 72, '%': parent * x / 100, 'em': parent * x}[u]


def inherit(sty, s):
    ns = dict(sty)
    if 'font-size' in s:
        ns['font-size'] = size_px(s['font-size'], sty.get('font-size', 16))
    for k in ('font-family', 'font-weight', 'font-style'):
        if k in s:
            ns[k] = s[k]
    return ns


def layer_name(stack):
    return ' / '.join(e.get(INK + 'label') or e.get('id') or '' for e in stack
                      if e.get(INK + 'groupmode') == 'layer')


def _to_inches(s):
    m = re.match(r'([\d.]+)\s*(in|mm|cm|pt|px)?', s)
    return float(m.group(1)) * {'in': 1, 'mm': 1 / 25.4, 'cm': 1 / 2.54, 'pt': 1 / 72, 'px': 1 / 96}[m.group(2) or 'px']


# ---- extraction ------------------------------------------------------------
def extract(path):
    """Return a list of dicts (keys = FIELDS), one per run of uniformly styled text."""
    root = ET.parse(path).getroot()
    vb = root.get('viewBox')
    w_in = _to_inches(root.get('width')) if root.get('width') else float(vb.split()[2]) / 96
    h_in = _to_inches(root.get('height')) if root.get('height') else float(vb.split()[3]) / 96
    vbw = float(vb.split()[2]) if vb else w_in * 96
    u2pt = w_in * 72 / vbw                     # one user unit, in points
    u2mm = u2pt / 72 * 25.4
    page_w, page_h = w_in * 25.4, h_in * 25.4
    fname = os.path.basename(path)
    rows = []

    def add(kind, source, stack, ident, size, fam, weight, style, aniso, hidden, X, Y, text):
        x_mm, y_mm = X * u2mm, Y * u2mm
        on_page = -5 < x_mm < page_w + 2 and -5 < y_mm < page_h + 2
        rows.append(dict(zip(FIELDS, [fname, kind, source, layer_name(stack), ident, round(size, 2),
                                      fam, weight, style, round(aniso, 3), hidden, on_page,
                                      round(x_mm, 1), round(y_mm, 1), CTRL.sub('', text)])))

    def ctx(stack):
        ids = [e.get('id') for e in stack if e.get('id')]
        is_mpl = any(MPL_HINT.match(i) for i in ids)
        near = next((i for i in reversed(ids) if MPL_HINT.match(i) or i.startswith(('text', 'g'))),
                    ids[-1] if ids else '')
        return is_mpl, near

    def emit_text(el, m, sty, stack, hidden):
        runs = []

        def rec(e, st, mm):
            s = style_of(e)
            if s.get('display') == 'none':
                return
            st2 = inherit(st, s)
            mm2 = mul(mm, parse_tf(e.get('transform'))) if e is not el else mm
            if e.text and e.text.strip():
                runs.append((e.text.strip(), st2, mm2))
            for c in e:
                rec(c, st2, mm2)
                if c.tail and c.tail.strip():
                    runs.append((c.tail.strip(), st2, mm2))

        rec(el, sty, m)
        if not runs:
            return
        is_mpl, near = ctx(stack)
        groups = []
        for t, st, mm in runs:
            sx, sy = scales(mm)
            key = (round(st.get('font-size', 16) * sy * u2pt, 2),
                   st.get('font-family', '?').replace("'", '').replace('"', '').strip(),
                   st.get('font-weight', 'normal'), st.get('font-style', 'normal'))
            if groups and groups[-1][0] == key:
                groups[-1][1].append(t)
            else:
                groups.append([key, [t], sx / sy if sy else 1])

        def num(v):
            try:
                return float(re.split(r'[ ,]', v.strip())[0])
            except Exception:
                return 0.0
        x0, y0 = num(el.get('x') or '0'), num(el.get('y') or '0')
        t1 = el.find(SVG + 'tspan')
        if t1 is not None and t1.get('x') is not None and t1.get('y') is not None:
            # a tspan's absolute x/y override the parent's (Inkscape often leaves stale ones there)
            x0, y0 = num(t1.get('x')), num(t1.get('y'))
        X = m[0] * x0 + m[2] * y0 + m[4]
        Y = m[1] * x0 + m[3] * y0 + m[5]
        for key, ts, aniso in groups:
            add('svgtext', 'mpl' if is_mpl else 'inkscape', stack, el.get('id') or near,
                key[0], key[1], key[2], key[3], aniso, hidden, X, Y, ' '.join(ts))

    def emit_glyphs(uses, m, stack, hidden):
        _, near = ctx(stack)
        items = []
        for u in uses:
            mm = GLYPH_RE.match(u.get(XL))
            f, hx = mm.group(1), mm.group(2)
            sx, sy = scales(mul(m, parse_tf(u.get('transform'))))
            if f.startswith('MJX'):                # MathJax: 1000 units per em
                f = 'MathJax-' + f.split('-')[2]
                sz = 1000 * sy * u2pt
            else:                                  # matplotlib: glyphs scaled by size/100
                sz = 100 * sy * u2pt
            items.append((f, hx, round(sz, 2), sx / sy if sy else 1))
        groups = []
        for f, hx, sz, an in items:              # merge consecutive same font/size
            if groups and groups[-1][0] == f and groups[-1][2] == sz:
                groups[-1][1].append(hx)
            else:
                groups.append([f, [hx], sz, an])
        decoded = []
        for f, hexes, sz, an in groups:
            if f.startswith('MathJax'):
                txt, source = ''.join(chr(int(h, 16)) for h in hexes), 'inkscape-mathjax'
            else:
                base = {'DejaVuSerif-Italic': 'DejaVuSerif', 'NimbusSanL-Regu': 'Helvetica'}.get(f, f)
                txt, source = decode(base, hexes), 'mpl'
            decoded.append((f, sz, an, txt, source))
        label = ''.join(d[3] for d in decoded)
        for f, sz, an, txt, source in decoded:
            if f in CM_FAMILIES and 'π' in label:
                txt = label           # each font run of a pi label reports the whole label
            add('glyph', source, stack, near, sz, f, '', '', an, hidden, m[4], m[5], txt)

    def walk(el, ctm, sty, stack, hidden):
        tag = el.tag.replace(SVG, '')
        if tag in ('defs', 'clipPath', 'mask', 'marker', 'pattern', 'symbol', 'metadata', 'title', 'desc', 'style'):
            return
        s = style_of(el)
        h = (hidden or s.get('display') == 'none' or s.get('visibility') == 'hidden'
             or s.get('opacity') in ('0', '0.0'))
        ns = inherit(sty, s)
        m = mul(ctm, parse_tf(el.get('transform')))
        stack2 = stack + [el]
        if tag == 'text':
            emit_text(el, m, ns, stack2, h)
            return
        uses = [c for c in el if c.tag == SVG + 'use' and GLYPH_RE.match(c.get(XL) or '')]
        if uses:
            emit_glyphs(uses, m, stack2, h)
        for c in el:
            if c.tag != SVG + 'use':
                walk(c, m, ns, stack2, h)

    walk(root, I, {'font-size': 16}, [], False)
    return rows


# ---- reporting -------------------------------------------------------------
def is_outlier(r, sizes, families):
    if r['family'].startswith('MathJax'):
        return round(r['size_pt'], 1) not in sizes
    if r['family'] in CM_FAMILIES and ('\\pi' in r['text'] or 'π' in r['text']):
        # house style: pi labels are deliberately Computer Modern math
        return round(r['size_pt'], 1) not in sizes or abs(r['aniso'] - 1) > 0.03
    family = re.sub(r'-(Bold|Oblique|Italic|BoldOblique|BoldItalic)$', '', r['family'])  # weight/style variants
    return (round(r['size_pt'], 1) not in sizes or family not in families
            or abs(r['aniso'] - 1) > 0.03)


def summarize(rows, show_rows=False):
    by_file = OrderedDict()
    for r in rows:
        by_file.setdefault(r['file'], []).append(r)
    for f, rs in by_file.items():
        print(f'===== {f}')
        if show_rows:
            for r in sorted(rs, key=lambda r: (r['layer'], r['y_mm'], r['x_mm'])):
                an = f" aspect={r['aniso']:.2f}" if abs(r['aniso'] - 1) > 0.03 else ''
                print(f"  {r['source']:16s} {r['family']:18s} {r['weight'] or '-':6s} {r['size_pt']:5.1f}pt{an}"
                      f"  layer={r['layer']} id={r['id']} @({r['x_mm']:.0f},{r['y_mm']:.0f})mm :: {r['text'][:50]}")
            continue
        groups = OrderedDict()
        for r in sorted(rs, key=lambda r: (r['source'], r['family'], r['weight'], r['size_pt'])):
            groups.setdefault((r['source'], r['family'], r['weight'] or '-', round(r['size_pt'], 1)), []).append(r)
        for (src, fam, wt, sz), g in groups.items():
            an = sorted({f"{r['aniso']:.2f}" for r in g if abs(r['aniso'] - 1) > 0.03})
            layers = ','.join(sorted({r['layer'] for r in g}))[:50]
            ex = ' | '.join(list(OrderedDict.fromkeys(r['text'][:22] for r in g))[:8])
            print(f"  {src:16s} {fam:18s} {wt:6s} {sz:5.1f}pt n={len(g):3d}"
                  f"{' ASPECT ' + ','.join(an) if an else ''}  layers={layers} :: {ex}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('svgs', nargs='*', help=f'SVG files or directories (default: {DEFAULT_DIR})')
    ap.add_argument('--outliers', action='store_true', help='only list non-standard items, one per line')
    ap.add_argument('--tsv', action='store_true', help='dump all items as TSV')
    ap.add_argument('--all', action='store_true', help='include hidden and off-page items')
    ap.add_argument('--sizes', default='6,8,10')
    ap.add_argument('--families', default='Helvetica,Arial')
    a = ap.parse_args()

    paths = []
    for p in (a.svgs or [str(DEFAULT_DIR)]):
        pp = Path(p)
        if not pp.exists() and (DEFAULT_DIR / p).exists():
            pp = DEFAULT_DIR / p
        paths += sorted(pp.glob('*.svg')) if pp.is_dir() else [pp]

    rows = []
    for p in paths:
        rows += extract(str(p))
    if not a.all:
        rows = [r for r in rows if r['on_page'] and not r['hidden']]

    if a.tsv:
        w = csv.DictWriter(sys.stdout, FIELDS, delimiter='\t')
        w.writeheader()
        w.writerows(rows)
    elif a.outliers:
        sizes = {float(s) for s in a.sizes.split(',')}
        fams = set(a.families.split(','))
        summarize([r for r in rows if is_outlier(r, sizes, fams)], show_rows=True)
    else:
        summarize(rows)


if __name__ == '__main__':
    main()
