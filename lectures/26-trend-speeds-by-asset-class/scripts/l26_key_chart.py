"""Lecture 26's key chart: left, the pass share of each speed for the rule (one set for all markets, the same vote per asset class) at the end-2025
review, one line per trend rule; right, Sharpe ratio after costs out of sample 2013-2026 of the rule and its comparisons, per class and in total
(results/select.json, results/tests.json). Output: figures/26_key.png."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l26 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

if __name__ == "__main__":
    apply_theme(); S = json.loads((L.RESULTS / "select.json").read_text(encoding="utf-8")); T = json.loads((L.RESULTS / "tests.json").read_text(encoding="utf-8"))
    fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.1,
                        subplot_titles=("Which speeds pass on both halves? End-2025 review", "Out of sample 2013-2026: Sharpe ratio after costs"))
    w = pd.Series(S["reviews"]["2025"]["weights"]["one_set"]); x = [str(h) for h in L.SPEEDS]
    for i, (rule, name) in enumerate((("ewma", "EWMA crossover"), ("breakout", "breakout"), ("return", "past return"))):
        fig.add_scatter(x=x, y=[w[f"{rule}_{h}"] for h in L.SPEEDS], mode="lines+markers", line=dict(color=SERIES[i], width=2), name=name, legendgroup="r", row=1, col=1)
    i0, i1 = L.SPEEDS.index(61), L.SPEEDS.index(179); fig.add_vrect(x0=i0 - 0.5, x1=i1 + 0.5, fillcolor=SERIES[0], opacity=0.07, line_width=0, row=1, col=1)
    fig.update_xaxes(type="category", title_text="speed, trading days (two weeks to two years)", row=1, col=1)
    fig.update_yaxes(title_text="share of 500 random halves passed", range=[0, 1], row=1, col=1)
    sh = T["sharpe"]; rows = ["Equity", "Rates", "Credit", "Commodities", "FX", "total"]; lab = ["Equity", "Govt bonds", "Credit", "Commodities", "Currencies", "<b>Total</b>"]
    for name, v, c, sym in (("the rule: one set, same vote per class", "one_set", INK, "diamond"), ("speeds chosen per class", "class", SERIES[1], "circle"),
                            ("all 36 streams, equal risk", "all36", MUTED, "square")):
        fig.add_scatter(x=[sh[v][r] for r in rows], y=lab, mode="markers", marker=dict(color=c, size=12 if v == "one_set" else 10, symbol=sym), name=name, legendgroup="v", row=1, col=2)
    fig.add_vline(x=0, line=dict(color=MUTED, width=1), row=1, col=2)
    fig.update_yaxes(autorange="reversed", row=1, col=2); fig.update_xaxes(title_text="Sharpe ratio after 5 bp, excess returns", row=1, col=2)
    fig.update_layout(title="Trend speeds across the board<br><sup>116 ETFs, three trend rules at twelve speeds; left: share of 500 random halves of years and markets in "
                            "which each speed works on both halves (shaded: 61-179 days)<br>right: speeds chosen each year on past data only, traded the next year on "
                            "Lecture 25's markets, classes at equal risk</sup>", height=640, width=1250, margin=dict(t=125, l=70, r=30, b=110), legend=dict(orientation="h", y=-0.2, x=0))
    save_figure(fig, L.PREFIX + "26_key", L.FIG)
