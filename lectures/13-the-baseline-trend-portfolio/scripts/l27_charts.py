"""Lecture 13's section charts, from saved results only (no recomputation):
  27_total       volatility target against constant leverage: drawdowns and gross exposure, out of sample 2013-2026 (OUT/l27_daily.parquet);
  27_crisis_today   today's portfolio replayed through the same falls (results/stress.json).
Usage: python l27_charts.py [function names]. Output: figures/27_total.png, 27_crisis_today.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l27 as M
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure


def load(name):
    return json.loads((M.RESULTS / name).read_text(encoding="utf-8"))


def total_chart():
    D = pd.read_parquet(M.OUT / "l27_daily.parquet")
    gross = {"volatility target": D.gross_U * D.ctot, "constant leverage": D.gross_U * D.lev_scale.shift(1).fillna(D.lev_scale.iloc[0])}
    ret = {"volatility target": D["rule"], "constant leverage": D["constant_leverage"]}
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.1, subplot_titles=("Drawdown from the previous peak", "Gross exposure, times capital"))
    for i, (nm, r) in enumerate(ret.items()):
        w = (1 + r).cumprod(); dd = w / w.cummax() - 1
        fig.add_scatter(x=dd.index, y=dd, mode="lines", line=dict(color=SERIES[i], width=1.5), name=nm, legendgroup=nm, row=1, col=1)
        g = gross[nm].rolling(21).median()
        fig.add_scatter(x=g.index, y=g, mode="lines", line=dict(color=SERIES[i], width=1.5), name=nm, legendgroup=nm, showlegend=False, row=1, col=2)
    fig.update_yaxes(tickformat=".0%", title_text="drawdown", row=1, col=1); fig.update_yaxes(title_text="gross exposure / capital (21-day median)", rangemode="tozero", row=1, col=2)
    fig.update_layout(title="Scaling the total: volatility target or constant leverage<br><sup>the same portfolio (equal risk in every market and class), out of sample "
                            "2013-2026; volatility target: total scaled each year to 10% on its past three years; constant leverage: gross exposure held each day at the "
                            "past three years' median<br>excess returns over cash, 5 bp per trade; our calculation</sup>",
                      height=560, width=1250, margin=dict(t=125, l=70, r=30, b=90), legend=dict(orientation="h", y=-0.15, x=0))
    save_figure(fig, M.PREFIX + "27_total", M.FIG)






def crisis_today_chart():
    S = load("stress.json"); name = lambda p, t: f"{p[:7]} to {t[:7]}"
    eps = [e for e in S["episodes"] if e["plain"]["markets"] >= 15]; lab = [name(e["peak"], e["trough"]) for e in eps]
    fig = make_subplots(rows=1, cols=1)
    fig.add_bar(y=lab, x=[e["plain"]["ret"] for e in eps], orientation="h", marker_color=INK, name="today's portfolio", showlegend=False)
    fig.add_vline(x=0, line=dict(color=MUTED, width=1))
    fig.update_yaxes(autorange="reversed"); fig.update_xaxes(tickformat=".0%", title_text="return over the fall")
    fig.update_layout(title="Today's portfolio replayed through past crises<br><sup>end-2025 markets and held speeds, scales from 2023-2025, through each fall of the "
                            "S&P 500 of more than 15%; excess returns over cash, 5 bp per trade</sup>",
                      height=440, width=1000, margin=dict(t=110, l=150, r=30, b=70))
    save_figure(fig, M.PREFIX + "27_crisis_today", M.FIG)


if __name__ == "__main__":
    apply_theme()
    only = sys.argv[1:]
    for f in (total_chart, crisis_today_chart):
        if not only or f.__name__ in only: f()

# The take-profit chart moved to Lecture 8 (scripts/takeprofit_chart.py), the crisis-speeds chart to Lecture 12 (scripts/l26_crisis_chart.py), 2026-11-16.
