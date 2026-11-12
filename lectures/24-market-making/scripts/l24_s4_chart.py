"""Lecture 24 §4, the tests (results/tests.json): each tested design's result before fees less the baseline's, day by day on the 24 out-of-sample days,
with the pooled difference and its 90% bootstrap band. Output: figures/24_s4_tests.png."""
import json, sys
from pathlib import Path
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure

T = json.loads((L.RESULTS / "tests.json").read_text(encoding="utf-8")); D = T["designs"]; base = D["baseline"]["per_day_bp"]
ROWS = [("H1", "Binance guard, 2 bp"), ("H2", "Avellaneda-Stoikov, κ = 5, c = 2"), ("H3", "1 tick behind the best"), ("H4", "ping-pong, target and stop")]
apply_theme(); fig = make_subplots(rows=1, cols=1)
for i, (h, name) in enumerate(ROWS):
    t = T["tests"][h]; d = D[t["design"]]["per_day_bp"]; x = [d[k] - base[k] for k in sorted(base)]
    fig.add_scatter(x=x, y=[name] * len(x), mode="markers", marker=dict(color=SERIES[i], size=9, opacity=0.55), name=f"{name}: one day", showlegend=False)
    lo, hi = t["ci90"]
    fig.add_scatter(x=[t["diff_bp"]], y=[name], mode="markers", marker=dict(color=INK, size=13, symbol="diamond"), showlegend=i == 0, name="pooled over the 24 days",
                    error_x=dict(type="data", symmetric=False, array=[hi - t["diff_bp"]], arrayminus=[t["diff_bp"] - lo], color=INK, thickness=2, width=8))
fig.add_vline(x=0, line=dict(color=MUTED, width=1))
fig.update_xaxes(title_text="result before fees less the baseline's, bp of the value traded")
fig.update_yaxes(autorange="reversed")
fig.update_layout(title="The four tests, day by day<br><sup>Bybit BTCUSDT perpetual, 24 out-of-sample days (11 October - 3 November 2025), whole days; dots: single days; "
                        "diamond and bar: pooled difference and its 90% bootstrap band over days</sup>",
                  height=480, width=1250, margin=dict(t=100, l=260, r=30, b=110), legend=dict(orientation="h", y=-0.22, x=0))
save_figure(fig, L.PREFIX + "24_s4_tests", L.FIG)
