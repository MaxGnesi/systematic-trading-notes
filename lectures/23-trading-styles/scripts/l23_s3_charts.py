"""Lecture 23 §3, the figure: H10 by size class, H11 by kind of mark, H12 day by day, from L23_RESULTS/s3_days (written by l23_s3.py). Bands: 2,000 resamples of the out-of-sample days.
Output: figures/23_s3_styles.png."""
import json, sys
from pathlib import Path
import numpy as np
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); rng = np.random.default_rng(0)
D = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((L.RESULTS / "s3_days").glob("*.json"))}
OUT = [d for d in D if L.L22.OUT_SAMPLE[0] <= d <= L.L22.OUT_SAMPLE[1]]; K = [rng.integers(0, len(OUT), len(OUT)) for _ in range(2000)]
CLS = ["0.01-0.1", "0.1-1", "1-5", "5-20", "20+"]


def band(f):
    s = np.array([f(i) for i in K]); return f(np.arange(len(OUT))), *np.percentile(s, [2.5, 97.5], axis=0)


def h10(idx, sn):
    n, s = np.zeros(len(CLS)), np.zeros(len(CLS))
    for j in idx:
        for r in D[OUT[j]]["h10"]:
            if r["sn"] == sn and r["cls"] in CLS: c = CLS.index(r["cls"]); n[c] += r["n"]; s[c] += r["s"]
    return s / n


fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.08, subplot_titles=("H10: the move after sniper-like orders", "H11: whole minutes against fake marks", "H12: share of taker size in runs"))
for sn, name, col in ((False, "other orders", MUTED), (True, "sniper-like: sent within 100 ms after Binance moved ≥ 2 bp their way", SERIES[3])):
    m, lo, hi = band(lambda i: h10(i, sn))
    fig.add_bar(x=CLS, y=m, name=name, marker_color=col, error_y=dict(type="data", array=hi - m, arrayminus=m - lo, color=INK, thickness=1), row=1, col=1)
KIND = [("", "every minute"), ("m5_", "5 minutes"), ("m15_", "15 minutes"), ("h_", "hour")]
for c, name, col in (("a", "flow on the trend's side (H11a), BTC", SERIES[0]), ("g", "extra taker size, either side (reported), BTC", SERIES[1])):
    v = np.array([[D[d]["h11"]["real"][k + c] - D[d]["h11"]["fake"][k + c] for k, _ in KIND] for d in OUT])
    m, lo, hi = band(lambda i: v[i].mean(0))
    fig.add_bar(x=[n for _, n in KIND], y=m, name=name, marker_color=col, error_y=dict(type="data", array=hi - m, arrayminus=m - lo, color=INK, thickness=1), row=1, col=2)
days = list(D); x = np.arange(len(days)); oos = np.array([d >= L.L22.OUT_SAMPLE[0] for d in days])
fig.add_scatter(x=days, y=[100 * D[d]["h12"]["share"] for d in days], mode="lines+markers", line=dict(color=SERIES[2], width=2), marker=dict(size=6), name="runs of equal orders, real order of sizes", row=1, col=3)
fig.add_scatter(x=days, y=[100 * D[d]["h12"]["share_shuf"] for d in days], mode="lines+markers", line=dict(color=MUTED, width=2), marker=dict(size=6), name="the same day, sizes shuffled within 5 minutes", row=1, col=3)
fig.add_vrect(x0=L.L22.OUT_SAMPLE[0], x1=days[-1], fillcolor=SERIES[0], opacity=0.07, line_width=0, row=1, col=3)
fig.update_yaxes(title_text="net move in the order's direction after 10 s, bp", row=1, col=1); fig.update_xaxes(title_text="order size, BTC", row=1, col=1)
fig.update_yaxes(title_text="real mark less fake marks, BTC in the first 3 s", row=1, col=2); fig.update_xaxes(title_text="kind of whole mark (funding minutes left out)", row=1, col=2)
fig.update_yaxes(title_text="% of taker size, log scale", type="log", row=1, col=3); fig.update_xaxes(title_text="day (shaded: out of sample)", row=1, col=3)
fig.update_layout(title="What is at work on Bybit: three footprints, out of sample<br><sup>Bybit BTCUSDT perpetual, 11 October - 3 November 2025 (right panel: all days). Bars: means over the out-of-sample days; whiskers: 95% bands from resampling days</sup>",
                  barmode="group", height=560, width=1500, margin=dict(t=110, l=70, r=30, b=170), legend=dict(orientation="h", y=-0.28, x=0))
save_figure(fig, L.PREFIX + "23_s3_styles", L.FIG)
print("H10 other", np.round(h10(range(len(OUT)), False), 2), "sniper-like", np.round(h10(range(len(OUT)), True), 2))
