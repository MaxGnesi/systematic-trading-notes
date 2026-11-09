"""Lecture 22, the key chart, in sample: what a plain replay and the hybrid replay say about a market buy of 5 BTC, beside what real orders of that size did.
The real order: among buys of 4-6 BTC in sample that came against or without a stream (less than half of the last 10 s of taker size on their side) and with no other order of 1 BTC
or more from 30 s before to 60 s after, the one whose mid path over 60 s is closest to the average of all such orders. The injected order: the same 5 BTC buy at a control moment of the
same day and hour with no order of 1 BTC or more within 60 s either way. Output: results/key.json and figures/22_key.png. --run recomputes."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_hybrid as H, l22_s3_response as S3
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "key.json"; GRID = np.arange(-5_000, 60_001, 250); SIZE = 5.0


def quiet(ts, big, a, b):
    """True where no order of 1 BTC or more falls between ts + a and ts + b, the moment itself left out."""
    i, j = np.searchsorted(big, ts + a, "left"), np.searchsorted(big, ts + b, "right"); own = np.isin(ts, big)
    return (j - i - own.astype(int)) == 0


def compute():
    days = S3.in_sample_days(); cand = []
    for d in days:
        X = pl.read_parquet(L.OUT / "orders" / f"{d}.parquet", columns=["ts", "side", "S", "prior_buy", "prior_sell", "m1000", "m10000", "m60000", "cost_bp"])
        big = np.sort(X.filter(pl.col("S") >= 1)["ts"].to_numpy())
        Y = X.filter((pl.col("side") == 1) & (pl.col("S") >= 4) & (pl.col("S") < 6) & (pl.col("prior_buy") < pl.col("prior_sell")))
        Y = Y.filter(pl.Series(quiet(Y["ts"].to_numpy(), big, -30_000, 60_000))); cand.append(Y.with_columns(pl.lit(d).alias("day")))
    C = pl.concat(cand); avg = np.array([C[c].mean() for c in ("m1000", "m10000", "m60000")])
    C = C.with_columns(sum(((pl.col(c) - a) ** 2) for c, a in zip(("m1000", "m10000", "m60000"), avg)).alias("dist")).sort("dist"); ex = C.row(0, named=True)
    day, t0 = ex["day"], ex["ts"]
    S = pl.read_parquet(L.STATE / f"{day}.parquet").filter(pl.col("ts").is_between(t0 - 10_000, t0 + 70_000)).sort("ts"); st = S["ts"].to_numpy()
    mid = ((S["bid"] + S["ask"]) / 2).to_numpy(); q5 = S["q_ask5"].to_numpy(); i0 = np.searchsorted(st, t0, "left") - 1
    at = lambda arr, t: arr[np.maximum(np.searchsorted(st, t, "right") - 1, 0)]
    real_mid = ((at(mid, t0 + GRID) - mid[i0]) / mid[i0] * 1e4).tolist(); real_depth = at(q5, t0 + GRID).tolist(); depth0 = float(q5[i0])
    K = pl.read_parquet(L.OUT / "controls" / f"{day}.parquet", columns=["ts"]); big = np.sort(pl.read_parquet(L.OUT / "orders" / f"{day}.parquet", columns=["ts", "S"]).filter(pl.col("S") >= 1)["ts"].to_numpy())
    kt = K["ts"].to_numpy(); kt = kt[quiet(kt, big, -60_000, 60_000) & (np.abs(kt - t0) < 3_600_000)]; tc = int(kt[np.argmin(np.abs(kt - t0))])
    out = {}
    for name, layers in (("plain", ""), ("hybrid", "ABC")):
        h = H.Hybrid(day, tc - 6_000, tc + 61_000, layers=layers); m0 = h.mid(tc); f, left = h.market_order(tc, 1, SIZE)
        rec = H.Hybrid(day, tc - 6_000, tc + 61_000, layers="")                       # the record itself, to take the market's own move out
        path, dep = [], []
        for g in GRID:
            t = tc + g
            if g < 0: path.append(0.0); dep.append(0.0); continue
            path.append((h.mid(t) - rec.mid(t)) / m0 * 1e4); dep.append(sum(h.missing(t, -1, k) for k in range(len(h.ours[0][3]))))   # what our order took that is still missing
        out[name] = dict(mid=path, depth=dep, cost=H.cost_bp(f, 1, m0))
    F = pl.concat([pl.read_parquet(L.OUT / "refill" / f"{d}.parquet").with_columns(pl.lit(d).alias("day")) for d in days]).filter(pl.col("met") > 0)
    O = pl.concat([pl.read_parquet(L.OUT / "orders" / f"{d}.parquet", columns=["ts", "side", "S"]).filter((pl.col("S") >= 4) & (pl.col("S") < 6)).with_columns(pl.lit(d).alias("day")) for d in days])
    F = F.join(O, on=["day", "ts", "side"]).group_by("probe").agg(((1 - pl.col("near") / pl.col("met")) * SIZE).median().alias("missing"), pl.len()).sort("probe")
    curves = json.loads(S3.OUT.read_text(encoding="utf-8"))["curves"]["kb|4-6"]; fit = H.fit_response()
    R = dict(day=day, t0=int(t0), S=ex["S"], cost=ex["cost_bp"], n_cand=C.height, tc=tc, grid=GRID.tolist(), real_mid=real_mid, real_depth=real_depth, depth0=depth0, inj=out,
             avg=dict(taus=list(L.TAUS), mean=curves["mean"], lo=curves["lo"], hi=curves["hi"], n=curves["n"]), fit5=[fit[t][0] * SIZE ** fit[t][1] for t in L.TAUS], real_missing=dict(probe=F["probe"].to_list(), missing=F["missing"].to_list(), n=int(F["len"][0])))
    OUT.write_text(json.dumps(R), encoding="utf-8")
    return R


if __name__ == "__main__":
    R = compute() if "--run" in sys.argv or not OUT.exists() else json.loads(OUT.read_text(encoding="utf-8"))
    print(R["day"], R["t0"], "S", R["S"], "cost", round(R["cost"], 3), "candidates", R["n_cand"], "| injected cost plain", round(R["inj"]["plain"]["cost"], 3), "hybrid", round(R["inj"]["hybrid"]["cost"], 3))
    g = np.array(R["grid"]) / 1000; taus = [t / 1000 for t in R["avg"]["taus"]]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, subplot_titles=("Where is the mid after a market buy of 5 BTC?", "How much of what we took is still missing near the best?"))
    fig.add_scatter(x=g, y=R["real_mid"], mode="lines", line=dict(color=MUTED, width=1.5), name="one real buy of about 5 BTC (the market's own moves included)", row=1, col=1)
    a = R["avg"]; m = taus[:4]
    fig.add_scatter(x=m, y=a["hi"][:4], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip", row=1, col=1)
    fig.add_scatter(x=m, y=a["lo"][:4], mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(120,120,120,0.18)", showlegend=False, hoverinfo="skip", row=1, col=1)
    fig.add_scatter(x=m, y=a["mean"][:4], mode="markers", marker=dict(color=INK, size=9, symbol="diamond"), name=f"real buys and sells of 4-6 BTC, average net move ({a['n']:,})", row=1, col=1)
    fig.add_scatter(x=g, y=R["inj"]["plain"]["mid"], mode="lines", line=dict(color=SERIES[1], width=2.5), name="our 5 BTC buy, plain replay", row=1, col=1)
    fig.add_scatter(x=g, y=R["inj"]["hybrid"]["mid"], mode="lines", line=dict(color=SERIES[0], width=2.5), name="our 5 BTC buy, hybrid replay", row=1, col=1)
    fig.add_vline(x=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=1); fig.add_hline(y=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=1)
    fig.update_xaxes(title_text="seconds after the order", row=1, col=1); fig.update_yaxes(title_text="mid move since the order, bp", row=1, col=1)
    rm = R["real_missing"]; fig.add_scatter(x=[p / 1000 for p in rm["probe"]], y=rm["missing"], mode="markers", marker=dict(color=INK, size=9, symbol="diamond"),
                                            name=f"real orders of 4-6 BTC, median, scaled to 5 BTC ({rm['n']:,})", row=1, col=2)
    fig.add_scatter(x=g, y=R["inj"]["plain"]["depth"], mode="lines", line=dict(color=SERIES[1], width=2.5), showlegend=False, row=1, col=2)
    fig.add_scatter(x=g, y=R["inj"]["hybrid"]["depth"], mode="lines", line=dict(color=SERIES[0], width=2.5), showlegend=False, row=1, col=2)
    fig.add_vline(x=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=2)
    fig.update_xaxes(title_text="seconds after the order", row=1, col=2); fig.update_yaxes(title_text="BTC still missing, of the 5 BTC taken", rangemode="tozero", row=1, col=2)
    fig.update_layout(title="A market that reacts: the same 5 BTC buy in a plain replay and in the hybrid replay<br><sup>Bybit BTCUSDT perpetual, in sample. Grey: one real buy, "
                      f"{R['day']}, chosen as the closest to the average path of {R['n_cand']:,} comparable buys (its mid did not move again for a minute). Our buy injected at a quiet moment of the same day; its mid net of the market's own moves</sup>",
                      height=540, width=1500, margin=dict(t=110, l=70, r=30, b=140), legend=dict(orientation="h", y=-0.22, x=0))
    save_figure(fig, L.PREFIX + "22_key", L.FIG)
