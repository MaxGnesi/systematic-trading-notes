"""Lecture 12 §8.2: return of each speed in each S&P 500 fall of more than 15%, ETFs, from results/crisis.json (scripts/l26_crisis.py).
Output: figures/26_crisis_speeds.png. Usage: python l26_crisis_chart.py"""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402
RES, FIG = Path(os.environ.get("L27_RESULTS", HERE.parent / "results")), HERE.parent / "figures"   # the notebook may redirect


def load(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


def crisis_speeds_chart():
    C = load("crisis.json"); sp = C["speeds"]
    name = lambda p, t: f"{p[:7]} to {t[:7]}"
    fig = make_subplots(rows=1, cols=1)
    quick = [e for e in C["episodes"] if e.get("etf") and (pd.Timestamp(e["trough"]) - pd.Timestamp(e["peak"])).days < 120]
    slow = [e for e in C["episodes"] if e.get("etf") and e not in quick]
    for group, col in ((quick, SERIES[1]), (slow, SERIES[0])):
        for j, e in enumerate(group):
            fig.add_scatter(x=sp, y=[e["etf"]["by_speed"][h] for h in sp], mode="lines+markers", line=dict(color=col, width=2, dash=("solid", "dash", "dot")[j % 3]),
                            marker=dict(size=6), name=f"{name(e['peak'], e['trough'])} (S&P {e['spx_fall']:.0%}, {'quick crash' if group is quick else 'long bear market'})")
    i0, i1 = sp.index("43"), sp.index("359"); fig.add_vrect(x0=i0 - 0.5, x1=i1 + 0.5, fillcolor=MUTED, opacity=0.1, line_width=0)
    fig.add_hline(y=0, line=dict(color=MUTED, width=1))
    fig.update_xaxes(type="category", title_text="speed, trading days (shaded: Lecture 12's held speeds)")
    fig.update_yaxes(tickformat=".0%", title_text="return over the fall, stream at 10% risk")
    fig.update_layout(title="Which speeds work in crises<br><sup>every fall of the S&P 500 of more than 15% from peak to trough 2000-2026; each of the twelve speeds "
                            "averaged over the three rules<br>and over all ETFs with data (each class the same weight; 2000-02: only 42 funds, mostly equity); "
                            "excess returns over cash, 5 bp per trade</sup>",
                      height=620, width=1100, margin=dict(t=125, l=70, r=30, b=170), legend=dict(orientation="h", y=-0.22, x=0))
    save_figure(fig, os.environ.get("L26_PREFIX", "") + "26_crisis_speeds", FIG)


if __name__ == "__main__":
    apply_theme(); crisis_speeds_chart()
