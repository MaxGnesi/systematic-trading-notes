"""Lecture 13's section charts, from saved results only (no recomputation):
  27_total       volatility target against constant leverage: drawdowns and gross exposure, out of sample 2013-2026 (OUT/l27_daily.parquet);
  27_takeprofit  Sharpe ratio and monthly skew against the take-profit threshold k, ETFs and capstone futures (results/takeprofit.json);
  27_crisis_speeds  return of each speed in each S&P 500 fall of more than 15% (ETFs, results/crisis.json; used in Lecture 12 §8.2);
  27_crisis_today   today's portfolio replayed through the same falls (results/stress.json).
27_takeprofit is used in Lecture 8 §4.8.
Usage: python l27_charts.py [function names]. Output: figures/27_total.png, 27_takeprofit.png, 27_crisis_speeds.png, 27_crisis_today.png."""
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
    save_figure(fig, M.PREFIX + "27_takeprofit", M.FIG)


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
    save_figure(fig, M.PREFIX + "27_crisis_speeds", M.FIG)


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
    for f in (total_chart, takeprofit_chart, crisis_speeds_chart, crisis_today_chart):
        if not only or f.__name__ in only: f()
