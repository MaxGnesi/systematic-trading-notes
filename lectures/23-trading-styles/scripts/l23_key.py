"""Lecture 23, the key chart: what we see against who traded. Top: four minutes of Lecture 22's laboratory market, taker orders coloured by the trader who sent them. Middle: the
same orders as the public feed shows them, grey, with three footprints marked by our measures: runs of equal orders at regular gaps (Lecture 22, H12), orders sent within 100 ms
after the outside price moved 2 ticks or more their way (the laboratory's hidden value standing in for Binance), and the first 3 s after each whole minute (H11). Bottom: four real
minutes of Bybit with the same measures, Binance standing in for the outside price. Output: results/key.json and figures/23_key.png. --run recomputes."""
import io, json, sys, zipfile
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
import l22_sim as Sim, l22_styles as St
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "key.json"; WIN = 240_000
COL = {"twap": SERIES[1], "sniper": SERIES[3], "trend": SERIES[0], "value": SERIES[2], "noise": MUTED}
NAME = {"twap": "slicer (TWAP)", "sniper": "sniper", "trend": "trend followers (bar close)", "value": "value traders", "noise": "noise traders"}


def marks(t, side, ext_t, ext_p, jump):
    """Sniper-like: the outside price moved `jump` or more in the order's direction over the 100 ms before it. Clock: within 3 s after a whole minute."""
    a = np.searchsorted(ext_t, t, "right") - 1; b = np.searchsorted(ext_t, t - 100, "right") - 1
    move = np.where((a >= 0) & (b >= 0), ext_p[np.maximum(a, 0)] - ext_p[np.maximum(b, 0)], 0.0)
    return side * move >= jump, (t % 60_000) < 3_000


def lab():
    m = Sim.Market(seed=5); m.band = -1; fv = Sim.FairValue(jump=5.0, jump_rate=0.05); fair = []
    crowd = [Sim.TrendFollower(fast=f, slow=s, size=0.2, clock=60_000, lag=2000) for _ in range(4) for f, s in ((1, 20), (5, 20))]
    m.players += [Sim.Noise(limit=12.0, depth=8.0), fv, Sim.Value(gap=3.0), Sim.MarketMaker(), Sim.Sniper(theta=3.0, size=0.5), Sim.Twap(rate=((0, 0.3),))] + crowd
    for T in range(100, 1_500_001, 100): m.run(T); fair.append((T, m.fair))
    O = m.public_trades().group_by("t", "side", "taker").agg(pl.col("size").sum().round(3).alias("q")).sort("t")
    best = None
    for a in range(900_000, 1_500_000 - WIN, 30_000):                                   # the window with the most TWAP orders found by the run rule, minutes 15 to 25
        W = O.filter(pl.col("t").is_between(a, a + WIN)); _, lab_ = St.runs(W.select("t", "side", "q"))
        if lab_.size and (best is None or (lab_ >= 0).sum() > best[0]): best = ((lab_ >= 0).sum(), a)
    a = best[1]; W = O.filter(pl.col("t").is_between(a - 600_000, a + WIN))                 # 10 min before, so that runs already under way are found
    _, run = St.runs(W.select("t", "side", "q")); F = np.array(fair); sn, ck = marks(W["t"].to_numpy(), W["side"].to_numpy(), F[:, 0], F[:, 1], 2.0)
    W = W.with_columns(pl.Series("run", run), pl.Series("sniper_like", sn), pl.Series("clock", ck)).filter(pl.col("t") >= a)
    return dict(t0=a, t=W["t"].to_list(), q=W["q"].to_list(), side=W["side"].to_list(), owner=W["taker"].to_list(), run=W["run"].to_list(), sniper_like=W["sniper_like"].to_list(), clock=W["clock"].to_list())


def bybit(day="2025-10-01"):
    X = pl.read_parquet(L.L22.OUT / "orders" / f"{day}.parquet", columns=["ts", "side", "S", "mid0"]).rename({"ts": "t", "S": "q"}).sort("t")
    _, run = St.runs(X.select("t", "side", "q")); X = X.with_columns(pl.Series("run", run))
    with zipfile.ZipFile(L.L22.BN_RAW / f"{L.L22.SYM}-aggTrades-{day}.zip") as z:
        B = pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), columns=["price", "transact_time"]).sort("transact_time")
    bt, bp = B["transact_time"].to_numpy(), B["price"].to_numpy(); t = X["t"].to_numpy()
    a = np.searchsorted(bt, t, "right") - 1; b = np.searchsorted(bt, t - 100, "right") - 1
    mv = np.where((a >= 0) & (b >= 0), (bp[np.maximum(a, 0)] - bp[np.maximum(b, 0)]) / bp[np.maximum(a, 0)] * 1e4, 0.0)
    X = X.with_columns(pl.Series("sniper_like", X["side"].to_numpy() * mv >= 2.0), pl.Series("clock", (t % 60_000) < 3_000))
    best = None; d0 = int(np.datetime64(f"{day}T00:00:00", "ms").astype(np.int64))
    for s in range(d0 + 3_600_000, d0 + 86_400_000 - WIN, 60_000):                      # the window with the most orders in runs, at least one sniper-like order
        W = X.filter(pl.col("t").is_between(s, s + WIN)); k = int((W["run"] >= 0).sum())
        if W["sniper_like"].sum() > 0 and (best is None or k > best[0]): best = (k, s)
    s = best[1]; W = X.filter(pl.col("t").is_between(s, s + WIN))
    return dict(day=day, t0=s, t=W["t"].to_list(), q=W["q"].to_list(), side=W["side"].to_list(), run=W["run"].to_list(), sniper_like=W["sniper_like"].to_list(), clock=W["clock"].to_list())


if __name__ == "__main__":
    R = dict(lab=lab(), bybit=bybit()) if "--run" in sys.argv or not OUT.exists() else json.loads(OUT.read_text(encoding="utf-8"))
    OUT.write_text(json.dumps(R), encoding="utf-8")
    fig = make_subplots(rows=3, cols=1, shared_xaxes=False, vertical_spacing=0.12, subplot_titles=("The laboratory market: who sent each order", "The same orders as the public feed shows them, with our footprint measures",
                                                                                                "Bybit, four real minutes: what we see"))
    for row, key, coloured in ((1, "lab", True), (2, "lab", False), (3, "bybit", False)):
        D = R[key]; t = (np.array(D["t"]) - D["t0"]) / 60_000; q = np.array(D["q"]); run = np.array(D["run"]); sn = np.array(D["sniper_like"]); ck = np.array(D["clock"])
        if coloured:
            own = np.array(D["owner"])
            for o in ("noise", "value", "trend", "sniper", "twap"):
                k = own == o; fig.add_scatter(x=t[k], y=q[k], mode="markers", marker=dict(color=COL[o], size=5 if o in ("noise", "value") else 8, opacity=0.5 if o in ("noise", "value") else 0.95),
                                              name=NAME[o], legendgroup="own", row=row, col=1)
        else:
            fig.add_scatter(x=t, y=q, mode="markers", marker=dict(color=MUTED, size=4, opacity=0.45), name="taker orders, owner unknown", showlegend=row == 2, legendgroup="feed", row=row, col=1)
            for k, i in enumerate(sorted(set(run[run >= 0].tolist()))):
                s = run == i; fig.add_scatter(x=t[s], y=q[s], mode="lines+markers", line=dict(color=SERIES[1], width=1.5), marker=dict(color=SERIES[1], size=8), name="a run of equal orders at regular gaps",
                                              showlegend=row == 2 and k == 0, legendgroup="run", row=row, col=1)
            fig.add_scatter(x=t[sn], y=q[sn], mode="markers", marker=dict(color=SERIES[3], size=10, symbol="x"), name="sent just after the outside price moved its way",
                            showlegend=row == 2, legendgroup="sn", row=row, col=1)
        for mnt in range(0, 5): fig.add_vrect(x0=mnt, x1=mnt + 0.05, fillcolor=SERIES[0], opacity=0.12, line_width=0, row=row, col=1)
        fig.update_yaxes(type="log", title_text="order size, BTC", row=row, col=1); fig.update_xaxes(title_text="minutes", range=[0, 4], row=row, col=1)
    fig.update_layout(title=f"Who else trades: what we see, and who did it<br><sup>Top two: Lecture 22's laboratory market, invented, the same four minutes; bottom: Bybit BTCUSDT, {R['bybit']['day']}, "
                      "in sample. Blue bands: the first 3 s after each whole minute. Outside price: the laboratory's hidden value, or Binance's last trade</sup>",
                      height=1050, width=1300, margin=dict(t=110, l=70, r=30, b=150), legend=dict(orientation="h", y=-0.08, x=0))
    save_figure(fig, L.PREFIX + "23_key", L.FIG)
    for key in ("lab", "bybit"):
        D = R[key]; run = np.array(D["run"]); print(key, len(D["t"]), "orders | in runs", int((run >= 0).sum()), "| runs", len(set(run[run >= 0].tolist())), "| sniper-like", int(np.sum(D["sniper_like"])),
                                                   "| in clock seconds", int(np.sum(D["clock"])))
    own = np.array(R["lab"]["owner"]); run = np.array(R["lab"]["run"]); sn = np.array(R["lab"]["sniper_like"])
    print("lab truth: orders in runs that are TWAP", round(float(np.mean(own[run >= 0] == "twap")), 2) if (run >= 0).any() else None, "| sniper-like that are sniper", round(float(np.mean(own[sn] == "sniper")), 2) if sn.any() else None,
          "| TWAP orders found in runs", round(float(np.mean(run[own == "twap"] >= 0)), 2))
