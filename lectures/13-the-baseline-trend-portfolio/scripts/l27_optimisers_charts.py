"""Lecture 13 §2.3 charts, from results/optimisers_many.json (no new computation).
figures/27_opt_resampled.png: how far each method's weights move when the in-sample history is resampled (the example market, SPY).
figures/27_opt_distribution.png: each method's out-of-sample Sharpe ratio minus equal risk contributions', across 86 markets (median and middle half).
Usage: python l27_optimisers_charts.py"""
import json, sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure  # noqa: E402

RES, FIG = HERE.parent / "results", HERE.parent / "figures"
D = json.loads((RES / "optimisers_many.json").read_text(encoding="utf-8"))
ORDER = ["Equal weight", "Equal risk contributions", "HRP", "NCO (equal risk contributions)", "Minimum variance, long only",
         "Maximum Sharpe, shrunk, long only", "Maximum Sharpe, long only", "Spectral risk parity, long only"]
SHORT = {"NCO (equal risk contributions)": "NCO", "Minimum variance, long only": "Minimum variance", "Maximum Sharpe, shrunk, long only": "Maximum Sharpe, shrunk",
         "Maximum Sharpe, long only": "Maximum Sharpe", "Spectral risk parity, long only": "Spectral risk parity"}
SPEEDS = ["43 days", "89 days", "179 days"]

if __name__ == "__main__":
    apply_theme()
    # 1. resampled weights in the example market: mean and 5th-95th percentile of each speed's weight
    W = D["resampled"]["SPY"]["weights"]
    f = make_subplots(rows=1, cols=3, subplot_titles=SPEEDS, shared_yaxes=True, horizontal_spacing=0.04)
    names = [SHORT.get(m, m) for m in ORDER]
    for j in range(3):
        mean = [W[m]["mean"][j] for m in ORDER]; lo = [W[m]["p5"][j] for m in ORDER]; hi = [W[m]["p95"][j] for m in ORDER]
        f.add_scatter(x=mean, y=names, mode="markers", marker=dict(size=11, color=SERIES[j]), showlegend=False,
                      error_x=dict(type="data", symmetric=False, array=[h - m for h, m in zip(hi, mean)], arrayminus=[m - l for m, l in zip(mean, lo)],
                                   color=SERIES[j], thickness=2.5, width=6), row=1, col=j + 1)
        f.add_vline(x=1 / 3, line=dict(color=MUTED, dash="dot", width=1), row=1, col=j + 1)
    f.update_xaxes(range=[-0.05, 1.05], tickformat=".0%")
    f.update_yaxes(autorange="reversed")
    f.update_layout(title="How far the weights move when history is resampled<br><sup>risk weights on three trend speeds of one market (SPY, history to 2025 resampled 200 times in 21-day blocks): dot = average, bar = 5th to 95th percentile</sup>",
                    height=520, width=1150, margin=dict(t=110, l=190, r=30, b=60), font=dict(size=14))
    save_figure(f, "27_opt_resampled", FIG)

    # 2. distribution across markets of the out-of-sample Sharpe ratio difference with equal risk contributions
    S = D["summary"]; order2 = [m for m in ORDER if m != "Equal risk contributions"]
    names2 = [SHORT.get(m, m) for m in order2]
    med = [S[m]["median"] for m in order2]; q1 = [S[m]["q1"] for m in order2]; q3 = [S[m]["q3"] for m in order2]
    g = go.Figure()
    g.add_scatter(x=med, y=names2, mode="markers", marker=dict(size=12, color=SERIES[0]), name="median",
                  error_x=dict(type="data", symmetric=False, array=[b - a for a, b in zip(med, q3)], arrayminus=[a - b for a, b in zip(med, q1)],
                               color=SERIES[0], thickness=2.5, width=6))
    g.add_vline(x=0, line=dict(color=INK, width=1.5))
    g.update_yaxes(autorange="reversed"); g.update_xaxes(title_text="Sharpe ratio minus equal risk contributions', out of sample 2013-2026")
    g.update_layout(title="Across 86 markets: each method against equal risk contributions<br><sup>three trend speeds per market; dot = median difference, bar = middle half of the markets</sup>",
                    height=460, width=1000, margin=dict(t=100, l=190, r=30, b=80), font=dict(size=14), showlegend=False)
    save_figure(g, "27_opt_distribution", FIG)
    print("ok")
