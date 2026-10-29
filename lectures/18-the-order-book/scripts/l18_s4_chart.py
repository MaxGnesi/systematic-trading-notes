"""Lecture 18 figure 18_04: a gap in Bybit's book feed, 25 September 2025, 06:20:10.9-06:20:22.0 UTC. The best bid and ask of the reconstructed book
in the minute around the gap (the book is rebuilt from the day's first snapshot and reset at the snapshot that ends the gap), and every trade (dots,
coloured by aggressor), which continued during the gap. From the Parquet tables and the gap register."""
import sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
from trading_models.plotting import INK, MUTED, SERIES, GRID, apply_theme, save_figure

apply_theme()
FIG = L18.FIG
ROOT = L18.PARQUET; DAY = "2025-09-25"
g = pl.read_csv(L18.gaps_path()).filter(pl.col("day") == DAY).row(0, named=True)
G0, G1 = g["start_ms"], g["end_ms"]; W0, W1 = G0 - 30_000, G1 + 30_000
b = pl.read_parquet(ROOT / "orderbook" / "BTCUSDT" / f"{DAY}.parquet", columns=["ts", "snap", "side", "tick", "size"]).filter(pl.col("ts") <= W1)
ts, sn, sd, tk, sz = (b[c].to_numpy() for c in ("ts", "snap", "side", "tick", "size"))
starts = np.flatnonzero(np.r_[True, np.diff(ts) != 0]); bids, asks = {}, {}; out = []
for k, a in enumerate(starts):
    e = starts[k + 1] if k + 1 < len(starts) else len(b)
    if sn[a] == 1: bids.clear(); asks.clear()
    for s, p, q in zip(sd[a:e].tolist(), tk[a:e].tolist(), sz[a:e].tolist()):
        bk = bids if s == 1 else asks
        if q == 0: bk.pop(p, None)
        else: bk[p] = q
    if ts[a] >= W0: out.append((ts[a], max(bids) / 10, min(asks) / 10))
B = pl.DataFrame(out, schema=["ts", "bid", "ask"], orient="row")
T = pl.read_parquet(ROOT / "trades" / "BTCUSDT" / f"{DAY}.parquet", columns=["ts", "side", "tick", "size"]).filter(pl.col("ts").is_between(W0, W1))
sec = lambda x: (np.asarray(x) - G0) / 1000
fig = make_subplots(rows=1, cols=1)
fig.add_annotation(x=(G1 - G0) / 2000, y=1.02, yref="paper", text=f"no book messages for {g['seconds']} s", showarrow=False, font=dict(size=11, color=INK))
for col, c, nm in (("bid", "#2a63b0", "best bid (reconstructed book)"), ("ask", "#c0436f", "best ask (reconstructed book)")):
    x = sec(B["ts"]); y = B[col].to_numpy().astype(float)
    pre = x < 0; post = x >= (G1 - G0) / 1000
    fig.add_scatter(x=x[pre], y=y[pre], mode="lines", line=dict(color=c, width=1.6, shape="hv"), name=nm)
    fig.add_scatter(x=x[post], y=y[post], mode="lines", line=dict(color=c, width=1.6, shape="hv"), showlegend=False)
for s, c, nm in ((1, SERIES[2], "trade, buyer aggressive"), (-1, SERIES[1], "trade, seller aggressive")):
    t = T.filter(pl.col("side") == s)
    fig.add_scatter(x=sec(t["ts"]), y=t["tick"].to_numpy() / 10, mode="markers", marker=dict(color=c, size=np.clip(4 + 10 * np.sqrt(t["size"].to_numpy()), 4, 20), opacity=0.8,
                    line=dict(width=0)), name=nm)
fig.add_vrect(x0=0, x1=(G1 - G0) / 1000, fillcolor=GRID, opacity=0.7, layer="below", line_width=0)
fig.add_annotation(x=(G1 - G0) / 1000, y=B.filter(pl.col("ts") >= G1)["bid"][0], text="a fresh snapshot<br>restarts the book", showarrow=True, ax=70, ay=55,
                   font=dict(size=11, color=MUTED))
fig.update_xaxes(title_text="seconds from the start of the gap (06:20:10.9 UTC)")
fig.update_yaxes(title_text="price, USDT", tickformat=",.0f")
fig.update_layout(title="A gap in the book feed: Bybit BTCUSDT, 25 September 2025<br><sup>The book's messages stopped for 11 seconds while trading went on; "
                        "the book is unknown inside the gap and restarts at the next snapshot</sup>", height=520, width=1200, margin=dict(t=110, l=80, b=100),
                  legend=dict(orientation="h", y=-0.2, x=0))
save_figure(fig, L18.PREFIX + "18_04_feed_gap", FIG)
print("ok", len(B), len(T))
