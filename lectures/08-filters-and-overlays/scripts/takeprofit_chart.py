"""Lecture 8 §4.8: Sharpe ratio and monthly skew against the take-profit threshold k, ETFs and capstone futures, from results/takeprofit.json
(scripts/takeprofit.py). Output: figures/08_08_takeprofit.png. Usage: python takeprofit_chart.py"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402
RES, FIG = HERE.parent / "results", HERE.parent / "figures"


def load(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


def takeprofit_chart():
    T = load("takeprofit.json"); ks = ["None", "2.0", "3.0", "4.0", "5.0"]; xs = ["none", "2", "3", "4", "5"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("Sharpe ratio after costs", "Skew of monthly returns"))
    for c, (m, name) in enumerate((("sharpe", "Sharpe"), ("skew_monthly", "skew"))):
        for i, (d, lab) in enumerate((("etf", "ETFs, out of sample 2013-2026"), ("futures", "capstone futures 2003-2022"))):
            fig.add_scatter(x=xs, y=[T[d][k][m] for k in ks], mode="lines+markers", line=dict(color=SERIES[i], width=2), marker=dict(size=9),
                            name=lab, legendgroup=d, showlegend=c == 0, row=1, col=c + 1)
            fig.add_scatter(x=xs[1:], y=[T[d][f"{k[0]}r"][m] for k in ks[1:]], mode="markers", marker=dict(color=SERIES[i], size=9, symbol="circle-open", line=dict(width=2)),
                            name=lab + ", re-entry after a one-unit pullback", legendgroup=d + "r", showlegend=c == 0, row=1, col=c + 1)
    for c in (1, 2): fig.update_xaxes(type="category", title_text="take-profit threshold k (units of the speed's risk)", row=1, col=c)
    fig.update_layout(title="Taking profits per speed<br><sup>each held stream goes flat when its open gain exceeds k times its risk over its own horizon "
                            "(daily volatility at entry × √speed), until its signal changes; breakout on closes in all versions</sup>",
                      height=560, width=1250, margin=dict(t=110, l=70, r=30, b=110), legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(fig, "08_08_takeprofit", FIG)


if __name__ == "__main__":
    apply_theme(); takeprofit_chart()
