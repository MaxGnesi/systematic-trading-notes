"""Lecture 22 §3, layer C on our data, in sample only (20 September - 9 October): how far the mid moves after a real order, net of matched controls, by size class and by size
relative to the queue, and what the orders cost, as a distribution. Net: from each order's signed move, the mean signed move of the control moments in its cell is taken off; a cell is the
same day, hour, decile of the imbalance at the best (fixed on the controls) the mid's move over the last second, fell, unchanged or rose, both signed for the order's
side, the third of the market's activity, taker orders in the 10 s before (thirds fixed on the controls), and the quarter of the share of the last 10 s of taker size that
was on the order's side (a stream already running).
Day by day, to spare memory; bands from 2,000 resamples of days. Output: results/s3_response.json and figures/22_s3_response.png. --run recomputes from L22_OUT."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
from plotly.subplots import make_subplots
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L
from trading_models.plotting import INK, MUTED, SERIES, apply_theme, save_figure
apply_theme(); OUT = L.RESULTS / "s3_response.json"
CLASSES = [(0.01, 0.1, "0.01-0.1"), (0.1, 1, "0.1-1"), (1, 5, "1-5"), (5, 20, "5-20"), (20, 1e9, "20+")]; XB = [(0, 0.1, "<0.1"), (0.1, 0.5, "0.1-0.5"), (0.5, 1, "0.5-1"), (1, 3, "1-3"), (3, 1e9, "3+")]
M = [f"m{t}" for t in L.TAUS]
SHARE = (pl.when(pl.col("side") == 1).then("prior_buy").otherwise("prior_sell") / (pl.col("prior_buy") + pl.col("prior_sell"))).fill_nan(0.5).fill_null(0.5).alias("share")   # of the last 10 s, on our side


def in_sample_days():
    return sorted(p.stem for p in (L.OUT / "orders").glob("*.parquet") if L.IN_SAMPLE[0] <= p.stem <= L.IN_SAMPLE[1])


BOUNDS = L.RESULTS / "s3_bounds.json"
KEYS = ["side", "hour", "di", "tm", "ta", "ps"]


def bounds():
    """The cell boundaries, fixed in sample on the control moments and kept for every later day: deciles of the imbalance at the best signed for a side, thirds of activity."""
    if BOUNDS.exists(): b = json.loads(BOUNDS.read_text(encoding="utf-8")); return np.array(b["qi"]), np.array(b["qa"])
    C = pl.concat([pl.read_parquet(L.OUT / "controls" / f"{d}.parquet") for d in in_sample_days()])
    sides = pl.concat([C.with_columns(pl.lit(s).alias("side")) for s in (1, -1)]).with_columns((pl.col("side") * pl.col("imb")).alias("simb"))
    qi = np.quantile(sides["simb"].drop_nans().to_numpy(), np.linspace(0.1, 0.9, 9)); qa = np.quantile(C["act10"].to_numpy(), [1 / 3, 2 / 3])
    BOUNDS.write_text(json.dumps(dict(qi=qi.tolist(), qa=qa.tolist())), encoding="utf-8"); return qi, qa


def cell(D, qi, qa):
    return D.with_columns((pl.col("ts") // 3_600_000 % 24).alias("hour"), pl.col("simb").cut(qi.tolist(), labels=[str(i) for i in range(10)]).alias("di"), pl.col("smove").sign().cast(pl.Int8).alias("tm"),
                          pl.col("act10").cut(qa.tolist(), labels=["0", "1", "2"]).alias("ta"), pl.col("share").cut([0.25, 0.5, 0.75], labels=["0", "1", "2", "3"]).alias("ps"))


def signed(D):
    return D.with_columns((pl.col("side") * pl.col("imb")).alias("simb"), (pl.col("side") * pl.col("move1")).alias("smove"), SHARE)


def controls(day, qi, qa):
    """The day's control moments, signed for each side, averaged by cell."""
    C = pl.read_parquet(L.OUT / "controls" / f"{day}.parquet"); sides = signed(pl.concat([C.with_columns(pl.lit(s).alias("side")) for s in (1, -1)]))
    return cell(sides, qi, qa).group_by(KEYS).agg(*[(pl.col("side") * pl.col(m)).mean().alias(f"c_{m}") for m in M],
                                                  pl.when(pl.col("side") == 1).then("flow_buy1000").otherwise("flow_sell1000").mean().alias("c_flow1000"), pl.len().alias("n_ctrl"))


def net_day(day, extra=(), min_S=0.01):
    """One day's real orders of min_S BTC or more, each net of the control moments in its cell: n_m<tau> (bp) and n_flow (BTC); with size class cls and relative-size bin xb."""
    qi, qa = bounds(); ctrl = controls(day, qi, qa)
    X = pl.read_parquet(L.OUT / "orders" / f"{day}.parquet", columns=list(dict.fromkeys(["ts", "side", "S", "x", "cost_bp", "imb", "move1", "act10", "prior_buy", "prior_sell", "flow1000"] + M + list(extra)))).filter(pl.col("S") >= min_S)
    X = cell(signed(X), qi, qa).join(ctrl, on=KEYS, how="inner")
    return X.with_columns(*[(pl.col("side") * pl.col(m) - pl.col(f"c_{m}")).alias(f"n_{m}") for m in M], (pl.col("flow1000") - pl.col("c_flow1000")).alias("n_flow"),
                          pl.col("S").cut([c[0] for c in CLASSES[1:]], labels=[c[2] for c in CLASSES]).alias("cls"), pl.col("x").cut([b[0] for b in XB[1:]], labels=[b[2] for b in XB]).alias("xb"),
                          pl.lit(day).alias("day"))


def compute():
    days = in_sample_days(); qi, qa = bounds(); ctrl = pl.concat([controls(d, qi, qa) for d in days])
    per_day = []; costs = {c[2]: [] for c in CLASSES}
    for d in days:
        X = net_day(d)
        X = X.with_columns(pl.when((pl.col("S") >= 4) & (pl.col("S") < 6)).then(pl.lit("4-6")).otherwise(None).alias("kb"))   # the key chart's size, about 5 BTC
        for by in ("cls", "xb", "kb"):
            per_day.append(X.filter(pl.col(by).is_not_null()).group_by(by).agg(pl.len().alias("n"), *[pl.col(f"n_{m}").sum().alias(f"s_{m}") for m in M], pl.col("n_flow").sum().alias("s_flow"), (pl.col("S").sum()).alias("s_S"), pl.col("x").sum().alias("s_x"))
                           .rename({by: "bin"}).with_columns(pl.lit(by).alias("by"), pl.lit(d).alias("day"), pl.col("bin").cast(pl.Utf8)))
        for c in CLASSES: costs[c[2]] += X.filter(pl.col("cls") == c[2])["cost_bp"].to_list()
        print(d, X.height, flush=True)
    P = pl.concat(per_day); rng = np.random.default_rng(0); R = dict(days=days, n_ctrl_median=float(ctrl["n_ctrl"].median()), curves={}, cost={})
    for by, bins in (("cls", CLASSES), ("xb", XB), ("kb", [(4, 6, "4-6")])):
        for b in bins:
            Q = P.filter((pl.col("by") == by) & (pl.col("bin") == b[2])).sort("day")
            if Q.is_empty(): continue
            n, s = Q["n"].to_numpy(), np.stack([Q[f"s_{m}"].to_numpy() for m in M] + [Q["s_flow"].to_numpy()], 1); boot = []
            for _ in range(2000):
                k = rng.integers(0, len(n), len(n)); boot.append(s[k].sum(0) / n[k].sum())
            boot = np.array(boot); mean = s.sum(0) / n.sum()
            R["curves"][f"{by}|{b[2]}"] = dict(n=int(n.sum()), mean=mean[:-1].tolist(), lo=np.percentile(boot, 2.5, 0)[:-1].tolist(), hi=np.percentile(boot, 97.5, 0)[:-1].tolist(),
                                               flow=float(mean[-1]), flow_lo=float(np.percentile(boot[:, -1], 2.5)), flow_hi=float(np.percentile(boot[:, -1], 97.5)), S_mean=float(Q["s_S"].sum() / n.sum()), x_mean=float(Q["s_x"].sum() / n.sum()))
    for k, v in costs.items(): v = np.array(v); R["cost"][k] = dict(n=len(v), p50=float(np.percentile(v, 50)), p90=float(np.percentile(v, 90)), p99=float(np.percentile(v, 99)), mean=float(v.mean()))
    OUT.write_text(json.dumps(R), encoding="utf-8")
    return R


if __name__ == "__main__":
    R = compute() if "--run" in sys.argv or not OUT.exists() else json.loads(OUT.read_text(encoding="utf-8"))
    for k, v in R["curves"].items(): print(k, v["n"], [round(x, 3) for x in v["mean"]], "flow", round(v["flow"], 3))
    for k, v in R["cost"].items(): print("cost", k, {a: round(b, 3) for a, b in v.items()})
    x = [f"{t / 1000:g}" for t in L.TAUS]; cols = [MUTED] + SERIES[:4]
    fig = make_subplots(rows=1, cols=3, column_widths=[0.38, 0.38, 0.24], horizontal_spacing=0.08, subplot_titles=("How far does the mid move after a real order? By size", "By size relative to the queue at the best", "What does an order cost?"))
    for col, (by, bins) in ((1, ("cls", CLASSES)), (2, ("xb", XB))):
        for b, c in zip(bins, cols):
            v = R["curves"].get(f"{by}|{b[2]}")
            if not v: continue
            fig.add_scatter(x=x, y=v["hi"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip", row=1, col=col)
            fig.add_scatter(x=x, y=v["lo"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=f"rgba({int(c[1:3], 16)},{int(c[3:5], 16)},{int(c[5:7], 16)},0.15)", showlegend=False, hoverinfo="skip", row=1, col=col)
            fig.add_scatter(x=x, y=v["mean"], mode="lines+markers", line=dict(color=c, width=2), marker=dict(color=c, size=7), name=(f"{b[2]} BTC" if by == "cls" else f"x {b[2]}") + f" ({v['n']:,})", row=1, col=col)
        fig.update_xaxes(title_text="seconds after the order", type="category", row=1, col=col); fig.update_yaxes(title_text="mid move in the order's direction, net, bp", row=1, col=col)
        fig.add_hline(y=0, line=dict(color=INK, width=1, dash="dot"), row=1, col=col)
    for q, sym, nm in (("p50", "circle", "median"), ("p90", "diamond", "90th percentile"), ("p99", "x", "99th percentile")):
        fig.add_scatter(x=[c[2] for c in CLASSES], y=[R["cost"][c[2]][q] for c in CLASSES], mode="lines+markers", line=dict(color=SERIES[0], width=1.5, dash="solid" if q == "p50" else "dot"),
                        marker=dict(color=SERIES[0], size=9, symbol=sym), name=f"cost: {nm}", row=1, col=3)
    fig.update_xaxes(title_text="order size, BTC", row=1, col=3); fig.update_yaxes(title_text="average fill against the mid before, bp", type="log", row=1, col=3)
    fig.update_layout(title=f"Section 3: the response to real orders on Bybit, in sample<br><sup>BTCUSDT perpetual, {R['days'][0]} to {R['days'][-1]} ({len(R['days'])} days); orders of 0.01 BTC or more, net of control moments in the same "
                      "day, hour, imbalance decile, last-second move, activity and the share of the last 10 s on the order's side. Bands: 95% over resampled days</sup>", height=540, width=1600, margin=dict(t=110, l=70, r=30, b=150), legend=dict(orientation="h", y=-0.25, x=0))
    save_figure(fig, L.PREFIX + "22_s3_response", L.FIG)
