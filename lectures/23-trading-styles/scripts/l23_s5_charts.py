"""Lecture 23 §5, the figure: what each footprint costs the makers (H21) and how fast a stale quote is taken after a move on Binance (H22), out of sample.
From L23_RESULTS/s5_tests.json (written by l23_s5.py --tests). Output: figures/23_s5_quotes.png."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); R = json.loads((L.RESULTS / "s5_tests.json").read_text(encoding="utf-8"))["out"]; A, B = R["H21"], R["H22"]
FP = [("sliced", "sliced"), ("sniper", "sniper-like"), ("large", "large, 1 BTC+"), ("other", "other")]
fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08, subplot_titles=("H21: who the makers lose to", "The makers' result per BTC filled", "H22: how fast a stale quote is taken"))
fig.add_bar(x=[n for _, n in FP], y=[100 * A["size_share"][f] for f, _ in FP], marker_color=MUTED, name="share of taker size", row=1, col=1)
fig.add_bar(x=[n for _, n in FP], y=[100 * A["adverse_share"][f] for f, _ in FP], marker_color=SERIES[3], name="share of the makers' adverse move, 10 s", row=1, col=1)
for k, (h, n) in enumerate((("m1000", "after 1 s"), ("m10000", "after 10 s"), ("m60000", "after 60 s"))):
    fig.add_bar(x=[n_ for _, n_ in FP], y=[A["maker"][f][h] for f, _ in FP], marker_color=[SERIES[0], SERIES[4], INK][k], name=f"makers' result {n}", row=1, col=2)
x = np.arange(2.5, 1000, 5)
for j, n, col, dash in (("2", "after a Binance move of 2 bp+", SERIES[3], "solid"), ("5", "after a Binance move of 5 bp+", SERIES[1], "solid")):
    h = np.array(B[j]["hist"]); fig.add_scatter(x=x + 2.5, y=100 * np.cumsum(h) / B[j]["n"], mode="lines", line=dict(color=col, width=2, dash=dash), name=n, row=1, col=3)
h = np.array(B["2"]["hist_rand"]); fig.add_scatter(x=x + 2.5, y=100 * np.cumsum(h) / B["2"]["n"], mode="lines", line=dict(color=MUTED, width=2), name="at random moments of the same hours", row=1, col=3)
fig.add_vline(x=50, line=dict(color=INK, dash="dot", width=1), row=1, col=3)
fig.add_annotation(x=50, y=8, text="50 ms: Lecture 21's<br>central latency", showarrow=False, xanchor="left", xshift=4, font=dict(size=11, color=INK), row=1, col=3)
fig.update_yaxes(title_text="% of the total", row=1, col=1); fig.update_xaxes(title_text="footprint of the taker order", row=1, col=1)
fig.update_yaxes(title_text="makers' result, bp per BTC", row=1, col=2); fig.update_xaxes(title_text="footprint of the taker order", row=1, col=2)
fig.update_yaxes(title_text="% with a Bybit taker order in the move's direction", range=[0, 100], row=1, col=3); fig.update_xaxes(title_text="delay after the move, ms", range=[0, 200], row=1, col=3)
fig.update_layout(title="What our quotes meet: who the makers lose to, and how little time a quote has<br><sup>Bybit BTCUSDT perpetual and Binance BTCUSDT, 11 October - 3 November 2025, out of sample</sup>",
                  barmode="group", height=560, width=1500, margin=dict(t=110, l=70, r=30, b=170), legend=dict(orientation="h", y=-0.28, x=0))
save_figure(fig, L.PREFIX + "23_s5_quotes", L.FIG)
c = np.cumsum(B["2"]["hist"]) / B["2"]["n"]; print("median delay ms, 2 bp:", 5 * (np.searchsorted(c, 0.5) + 1), "| 5 bp:", 5 * (np.searchsorted(np.cumsum(B["5"]["hist"]) / B["5"]["n"], 0.5) + 1))
