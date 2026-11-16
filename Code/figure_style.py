"""House font style for all manuscript figures.

Usage (first cell of a figure notebook, after any other rcParams):

    from splitflow.figure_style import apply_house_style
    apply_house_style()

Sets Helvetica (falling back to Arial) at 6 pt for all text. Mathtext such as
$R^2$ or $10^{-50}$ is also set in Helvetica, except labels containing $\\pi$
(e.g. tick labels $-\\pi$, $\\pi/2$): their math part is drawn in Computer Modern
so pi looks like a proper math symbol, while plain labels ("0", "Time (s)")
stay Helvetica.

House style (see FinalFigures/font_inconsistencies.md):
    panel letters 10 pt bold, panel titles 8 pt bold, everything else 6 pt.

Check a finished SVG with:  python RunFigures/audit_fonts.py <figure>.svg --outliers
"""
import functools

import matplotlib
from matplotlib.text import Text

FONT_FAMILY = ['Helvetica', 'Arial']
BASE_SIZE = 6
PI_MATH_FONTSET = 'cm'   # math font for any text containing \\pi


def apply_house_style(size=BASE_SIZE):
    rc = matplotlib.rcParams
    rc['font.family'] = 'sans-serif'
    rc['font.sans-serif'] = FONT_FAMILY + [f for f in rc['font.sans-serif'] if f not in FONT_FAMILY]
    rc['font.size'] = size
    rc['font.weight'] = 'normal'
    rc['text.usetex'] = False
    rc['mathtext.fontset'] = 'custom'
    rc['mathtext.rm'] = 'Helvetica'
    rc['mathtext.sf'] = 'Helvetica'
    rc['mathtext.it'] = 'Helvetica:italic'
    rc['mathtext.bf'] = 'Helvetica:bold'
    # 'rm' (not 'regular'): upright Helvetica for $0$, $R^2$ under the custom fontset,
    # and upright CM digits with the CM math pi for the \pi labels below.
    rc['mathtext.default'] = 'rm'
    _use_math_font_for_pi()


def _pi_math_font(text):
    if r'\pi' in text.get_text():
        fp = text.get_fontproperties()
        if fp.get_math_fontfamily() != PI_MATH_FONTSET:
            fp = fp.copy()
            fp.set_math_fontfamily(PI_MATH_FONTSET)
            text._fontproperties = fp   # set directly: set_fontproperties would recurse via stale


def _use_math_font_for_pi():
    """Draw the mathtext of any Text containing \\pi with PI_MATH_FONTSET.

    Hooked into Text.set_text (so layout is measured with the right font) and
    Text.draw (in case the font properties are replaced afterwards). Covers
    tick labels made by formatters, so the plotting code needs no changes.
    Installed once per session.
    """
    if getattr(Text.draw, '_house_pi', False):
        return
    original_draw, original_set_text = Text.draw, Text.set_text

    @functools.wraps(original_draw)
    def draw(self, renderer):
        _pi_math_font(self)
        return original_draw(self, renderer)

    @functools.wraps(original_set_text)
    def set_text(self, s):
        original_set_text(self, s)
        _pi_math_font(self)

    draw._house_pi = True
    Text.draw, Text.set_text = draw, set_text
