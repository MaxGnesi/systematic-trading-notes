"""Lecture 13 (also used by Lectures 11 and 12): a stylised diagram of the build. The risk budget is planned top-down (total,
classes, markets, speeds); the portfolio is computed bottom-up. Three versions, one per lecture: Lecture 13's shows the weighing at every
level; Lecture 11's highlights the markets (which enter), Lecture 12's the speeds (which run), with the other levels greyed.
Output: figures/27_build.png, ../11-choosing-the-markets/figures/build_markets.png, ../12-trend-speeds-by-asset-class/figures/build_speeds.png.
Usage: python l27_build_diagram.py"""
import sys
import os
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402

LEVELS = [  # (y, boxes: (x, label), fill)
    (4, [(5.0, "<b>Total</b><br>10% a year")], "#dbe8f7"),
    (3, [(1.0, "Equity"), (3.0, "Government<br>bonds"), (5.0, "Credit"), (7.0, "Commodities"), (9.0, "Currencies")], "#e7f3ec"),
    (2, [(-0.2, "SPY"), (0.9, "EFA"), (2.0, "EEM"), (3.1, "…")], "#fdecdf"),
    (1, [(-0.9, "61 d"), (0.1, "89 d"), (1.1, "127 d"), (2.1, "179 d"), (3.1, "…")], "#f6f5f1"),
]
LABEL = {4: "The total", 3: "Groups (asset classes, or clusters<br>found in the data, §4.2): equal risk each", 2: "Markets in a class: equal risk each", 1: "Speeds in a market: equal risk each"}

FOCUS = {2: "<b>Lecture 11: which markets enter</b><br>chosen before any weight", 1: "<b>Lecture 12: which speeds run</b><br>chosen before any weight"}
GREY = "#f2f2f2"


def draw(focus=None):
    """focus: None (all levels, Lecture 13), or the level to highlight (2 markets, 1 speeds)."""
    f = go.Figure()
    w, h = 0.36, 0.28
    # links
    links = [((5.0, 4), (x, 3)) for x, _ in LEVELS[1][1]] + [((1.0, 3), (x, 2)) for x, _ in LEVELS[2][1]] + [((-0.2, 2), (x, 1)) for x, _ in LEVELS[3][1]]
    for (x0, y0), (x1, y1) in links:
        f.add_shape(type="line", x0=x0, y0=y0 - h, x1=x1, y1=y1 + h, line=dict(color=MUTED, width=1.5))
    for y, boxes, fill in LEVELS:
        for x, lab in boxes:
            bw = 0.9 if y == 3 else (1.1 if y == 4 else 0.42)
            on = focus is None or focus == y
            f.add_shape(type="rect", x0=x - bw, x1=x + bw, y0=y - h, y1=y + h, fillcolor=fill if on else GREY,
                        line=dict(color=INK if on else MUTED, width=3 if focus == y else 1.2))
            f.add_annotation(x=x, y=y, text=lab, showarrow=False, font=dict(size=13 if y > 1 else 12, color=INK if on else MUTED))
        txt = FOCUS[y] if focus == y else LABEL[y]
        f.add_annotation(x=10.4, y=y, text=txt, showarrow=False, xanchor="left", font=dict(size=13, color=INK if (focus is None or focus == y) else MUTED))
    # the two directions
    f.add_annotation(x=-1.6, y=1.0, ax=-1.6, ay=4.0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.4,
                     arrowwidth=3, arrowcolor=SERIES[0], text="")
    f.add_annotation(x=-1.95, y=2.5, text="<b>Risk budget</b><br>planned<br>top-down", showarrow=False, xanchor="right", font=dict(size=13, color=SERIES[0]))
    f.add_annotation(x=15.2, y=4.0, ax=15.2, ay=1.0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.4,
                     arrowwidth=3, arrowcolor=SERIES[1], text="")
    f.add_annotation(x=15.55, y=2.5, text="<b>Portfolio</b><br>computed<br>bottom-up", showarrow=False, xanchor="left", font=dict(size=13, color=SERIES[1]))
    f.update_xaxes(visible=False, range=[-3.4, 17.2]); f.update_yaxes(visible=False, range=[0.5, 4.5])
    title = {None: "The build: one rule, equal risk, at every level<br><sup>the budget is shared from the total downwards; the portfolio is built from the speeds upwards, because a blend is calmer than its parts and must be measured before it is scaled</sup>",
             2: "The build: this lecture chooses the markets<br><sup>which boxes exist at the market level; Lecture 12 chooses the speeds, Lecture 13 weighs every level by equal risk and scales the total</sup>",
             1: "The build: this lecture chooses the speeds<br><sup>which boxes exist at the speed level, in the markets of Lecture 11; Lecture 13 weighs every level by equal risk and scales the total</sup>"}[focus]
    f.update_layout(title=title, height=520, width=1250, margin=dict(t=90, l=20, r=20, b=20), showlegend=False)
    return f


if __name__ == "__main__":
    apply_theme()
    L = HERE.parents[1]
    save_figure(draw(), os.environ.get("L27_PREFIX", "") + "27_build", HERE.parent / "figures")
    save_figure(draw(2), os.environ.get("L27_PREFIX", "") + "build_markets", L / "11-choosing-the-markets" / "figures")
    save_figure(draw(1), os.environ.get("L27_PREFIX", "") + "build_speeds", L / "12-trend-speeds-by-asset-class" / "figures")
    print("ok")
