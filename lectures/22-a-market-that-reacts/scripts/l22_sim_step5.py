"""Lecture 22 §2, teaching simulation, step 5: trend followers that act at the close of a bar, and H11 tested where the answer is known. A crowd of followers on minute and five-minute bars,
eight rules, k of each, 0.2 BTC each, up to 2 s late; value traders who act beyond a gap of 1, 3 or 5 ticks; a market maker that widens its quotes by 2 ticks around each whole minute, or not.
The measures see only public trades and quotes. Scored: H11a (flow with the trend after the mark), H11b (spread before it), and the size burst reported beside them, against the followers' true share.
Invented data, 2 seeds of 6 hours per world."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_sim as Sim, l22_styles as St
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); BLUE, ORANGE, GREEN = SERIES[0], SERIES[1], SERIES[2]; OUT = L.RESULTS / "sim_step5.json"; SEEDS = range(1); T_END = 12 * 3_600_000; UNIT = 1_800_000; REL = range(-10, 20)
RULES = ((1, 50), (20, 50), (5, 20), (1, 20))
WORLDS = [(k, g, 0) for k in (0, 1, 5, 20) for g in (1.0, 3.0, 5.0)] + [(k, 3.0, 2) for k in (0, 5, 20)]
if "--smoke" in sys.argv: T_END, SEEDS, OUT = 4_500_000, range(1), Path(__file__).resolve().parents[3].parent / "l21" / "step5_smoke.json"
PROFILE = [(0, 3.0, 0), (0, 3.0, 2), (20, 3.0, 0), (20, 3.0, 2)]


def world(seed, k, gap, widen):
    m = Sim.Market(seed=seed); m.band = -1
    m.players += [Sim.Noise(limit=12.0, depth=8.0), Sim.FairValue(), Sim.Value(gap=gap), Sim.MarketMaker(widen=widen)]
    m.players += [Sim.TrendFollower(fast=f, slow=s, size=0.2, clock=c, lag=2000) for _ in range(k) for f, s in RULES for c in (60_000, 300_000)]; m.run(T_END)
    return m


def profile(T, Q, X):
    """By second from the mark, -10 to 19: taker size, taker flow on the trend's side and spread, averaged over marks."""
    tr = X.select(pl.col("t").alias("mk"), "trend")
    rel = lambda D, c: D.with_columns(((pl.col("t") + 10_000 + c) % 60_000 - 10_000 - c).alias("rel")).with_columns((pl.col("t") - pl.col("rel")).alias("mk"), (pl.col("rel") - c).floordiv(1000).alias("s")).join(tr, on="mk")
    A = rel(T, 0).group_by("s").agg(pl.col("size").sum().alias("g"), (pl.col("side") * pl.col("size") * pl.col("trend")).sum().alias("w")).sort("s")
    B = rel(Q.with_columns((pl.col("ask") - pl.col("bid")).alias("spr")), 1).group_by("s").agg(pl.col("spr").mean()).sort("s")
    n = X.height; A = A.filter(pl.col("s").is_in(list(REL))); B = B.filter(pl.col("s").is_in(list(REL)))
    return dict(g=(A["g"] / n).to_list(), w=(A["w"] / n).to_list(), spr=B["spr"].to_list())


def compute():
    R = dict(worlds=[], profiles={})
    for k, gap, wid in WORLDS:
        data, share, prof = [], [], []
        for s in SEEDS:
            m = world(s, k, gap, wid); T = m.public_trades(); Q = pl.DataFrame(m.quotes, schema=["t", "bid", "ask"], orient="row").drop_nulls()
            O = T.group_by("t", "side").agg(pl.col("size").sum().round(3).alias("q")).sort("t"); data.append((O, Q))
            share.append(float(T.filter(pl.col("taker") == "trend")["size"].sum() / T["size"].sum()))
            if (k, gap, wid) in PROFILE: prof.append(profile(T, Q, St.marks(O, Q)))
        P = St.placebo(data, unit=UNIT)
        r = dict(k=k, gap=gap, widen=wid, share=float(np.mean(share)), units=P["units"]) | {f"{x}_{y}": P[x][y] for x in "axg" for y in ("diff", "t", "p")}
        R["worlds"].append(r); print({x: (round(y, 4) if isinstance(y, float) else y) for x, y in r.items()}, flush=True)
        if prof: R["profiles"][f"{k}|{gap}|{wid}"] = {x: np.mean([p[x] for p in prof], axis=0).tolist() for x in prof[0]}
    OUT.write_text(json.dumps(R), encoding="utf-8")
    return R


R = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() and "--run" not in sys.argv and "--smoke" not in sys.argv else compute()
W = R["worlds"]; P = R["profiles"]; rel = list(REL)
fig = make_subplots(rows=1, cols=4, horizontal_spacing=0.065, subplot_titles=("Flow with the trend, by second from the mark", "Spread, by second from the mark",
                    "H11a: is the flow with the trend found?", "H11b: is the maker's widening found?"))
for key, nm, c, d in (("0|3.0|0", "left two: no followers", MUTED, "solid"), ("20|3.0|0", "left two: 20 followers of each rule (about 8% of taker size)", BLUE, "solid"), ("0|3.0|2", "left two: no followers, maker widens", MUTED, "dot"), ("20|3.0|2", "left two: 20 of each, maker widens", BLUE, "dot")):
    fig.add_scatter(x=rel, y=P[key]["w"], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=6), name=nm, row=1, col=1)
    fig.add_scatter(x=rel, y=P[key]["spr"], mode="lines+markers", line=dict(color=c, width=2, dash=d), marker=dict(color=c, size=6), showlegend=False, row=1, col=2)
for c in (1, 2):
    fig.add_vline(x=-0.5, line=dict(color=INK, width=1, dash="dot"), row=1, col=c); fig.update_xaxes(title_text="seconds from the whole minute", row=1, col=c)
fig.update_yaxes(title_text="BTC per second, on the trend's side", row=1, col=1); fig.update_yaxes(title_text="spread, ticks", row=1, col=2)
CROWD = ["none", "1 of each", "5 of each", "20 of each"]
for gap, c in ((1.0, ORANGE), (3.0, BLUE), (5.0, GREEN)):
    w = sorted([x for x in W if x["gap"] == gap and x["widen"] == 0], key=lambda x: x["k"])
    fig.add_scatter(x=CROWD, y=[x["a_t"] for x in w], mode="lines+markers", line=dict(color=c, width=2), marker=dict(color=c, size=8), name=f"H11a: value traders act beyond {gap:g} tick" + ("s" if gap > 1 else ""), row=1, col=3)
    if gap == 3.0: fig.add_scatter(x=CROWD, y=[x["g_t"] for x in w], mode="lines+markers", line=dict(color=MUTED, width=2, dash="dash"), marker=dict(color=MUTED, size=7), name="H11a panel: size burst at the mark, any side, value 3 ticks (reported)", row=1, col=3)
for wid, d, nm in ((0, "solid", "H11b: maker does not widen"), (2, "dot", "H11b: maker widens 2 ticks around the minute")):
    w = sorted([x for x in W if x["gap"] == 3.0 and x["widen"] == wid and x["k"] in (0, 5, 20)], key=lambda x: x["k"])
    fig.add_scatter(x=[CROWD[(0, 1, 5, 20).index(x["k"])] for x in w], y=[x["x_t"] for x in w], mode="lines+markers", line=dict(color=BLUE, width=2, dash=d), marker=dict(color=BLUE, size=8), name=nm, row=1, col=4)
for c in (3, 4):
    fig.add_hline(y=1.72, line=dict(color=INK, width=1, dash="dot"), row=1, col=c)
    fig.update_xaxes(title_text="crowd of followers (8 rules, 0.2 BTC each)", categoryorder="array", categoryarray=CROWD, row=1, col=c)
    fig.update_yaxes(title_text="t, minute less fake marks", row=1, col=c)
fig.update_layout(title="Step 5: trend followers at the close of a bar, and H11 tested with the answer known<br><sup>Invented; 12 hours per world. Followers on minute and 5-minute bars, eight rules, 0.2 BTC each, up to 2 s late. "
                  "Left: value traders act beyond 3 ticks. Right: t of the excess at the minute over fake marks 10-50 s after it, unit by unit (30 minutes stand for a day); dotted line at t = 1.72, p = 5% one-sided</sup>", height=520, width=1600, margin=dict(t=110, l=70, r=30, b=140), legend=dict(orientation="h", y=-0.28, x=0))
if "--smoke" not in sys.argv: save_figure(fig, L.PREFIX + "22_sim_step5", L.FIG)
for x in W: print({a: (round(b, 3) if isinstance(b, float) else b) for a, b in x.items()})
