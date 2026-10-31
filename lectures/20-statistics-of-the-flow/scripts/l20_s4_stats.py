"""Lecture 20 Section 4: H8 and H9 (results/hypotheses.md) around the tariff post of 10 October 2025, 20:50:01.702 UTC.
H8: net aggressive flow (taker buys - sells, BTC) in the hour before the post, Bybit and Binance, against every one-hour window of the other 44 days
aligned to the same clock phase (start at hh:50:01.702). H9: over the two hours before the post, (a) VPIN (true side, average of its values at the
bucket ends in the window), (b) the Hawkes branching ratio of Bybit taker orders fitted on the window, (c) Kyle's lambda (slope of the mid change on
the trade imbalance over 10 s intervals, ticks per BTC), against the aligned two-hour windows of the other 44 days.
p = (1 + reference windows at least as extreme) / (1 + reference windows). Reported beside: OFI at the best and taker sells of at least $1M.
Output: L20_OUT/s4/stats.json, L20_OUT/s4/windows.parquet."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl

OUT = L20.S4
from l20_s3_hawkes import fit
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
DAYS = L20.days(); CASC = "2025-10-10"
POST = int(np.datetime64("2025-10-10T20:50:01.702", "ms").astype(np.int64)); H1, H2 = 3_600_000, 7_200_000
PHASE = POST % H1                                                        # 50 min 1.702 s past the hour

SH = POST % 1000                                                         # seconds shifted by 702 ms, so that windows start exactly at hh:50:01.702


def per_second(v, d):
    o = pl.read_parquet(L20.ORD / f"{v}_{d}.parquet", columns=["ts", "side", "size"] + (["price"] if v == "binance" else ["tick"]))
    usd = (pl.col("price") if v == "binance" else pl.col("tick") / 10) * pl.col("size")
    return o.with_columns(((pl.col("ts") - SH) // 1000).alias("s")).group_by("s").agg(
        (pl.col("side") * pl.col("size")).sum().alias(f"ti_{v}"), ((pl.col("side") == -1) & (usd >= 1e6)).sum().alias(f"big_sells_{v}"))


AGG = None
for v in ("bybit", "binance"):
    x = pl.concat([per_second(v, d) for d in DAYS]).group_by("s").agg(pl.all().sum())
    AGG = x if AGG is None else AGG.join(x, on="s", how="full", coalesce=True)
AGG = AGG.fill_null(0).sort("s")
TS_BY = np.unique(np.concatenate([pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts"])["ts"].to_numpy() for d in DAYS]))
SEC = pl.concat([pl.read_parquet(L20.BOOK10 / f"{d}.parquet", columns=["sec", "ofi_1", "mid2", "reset"]) for d in DAYS]).sort("sec").unique("sec", keep="last", maintain_order=True)
VB = pl.read_parquet(L20.S3 / "vpin_buckets.parquet").with_columns((2 * pl.col("buy_share") - 1).abs().alias("imb"))
VB = VB.with_columns(pl.col("imb").rolling_mean(window_size=50).alias("vpin")).drop_nulls("vpin")
t_first = int(np.datetime64(f"{DAYS[0]}T00:00:00", "ms").astype(np.int64)); t_last = int(np.datetime64(f"{DAYS[-1]}T23:59:59", "ms").astype(np.int64))
casc0 = int(np.datetime64(f"{CASC}T00:00:00", "ms").astype(np.int64))


def starts(length):
    """Window starts aligned to the clock phase of the pre-window, covering the sample; those on 10 October flagged."""
    s0 = POST - length; first = s0 - ((s0 - t_first) // length) * length
    return [s for s in range(first, t_last - length + 2, length)]


def window_stats(s, length, hawkes):
    e = s + length; out = {"start": s}
    w = AGG.filter((pl.col("s") >= (s - SH) // 1000) & (pl.col("s") < (e - SH) // 1000))
    for c in ("ti_bybit", "ti_binance", "big_sells_bybit", "big_sells_binance"): out[c] = float(w[c].sum())
    sc = SEC.filter((pl.col("sec") >= s // 1000) & (pl.col("sec") < e // 1000))
    out["ofi"] = float(sc["ofi_1"].sum()); out["resets"] = int(sc["reset"].sum())
    vb = VB.filter((pl.col("t_end") >= s) & (pl.col("t_end") < e)); out["vpin"] = float(vb["vpin"].mean()) if vb.height else np.nan
    if hawkes:
        x = TS_BY[np.searchsorted(TS_BY, s):np.searchsorted(TS_BY, e)]
        out["hawkes_n"] = fit((x - s) / 1000.0, length / 1000.0)[2] if len(x) > 100 else np.nan
        # Kyle's lambda: mid change on the trade imbalance, 10 s intervals
        k = sc.with_columns((pl.col("sec") // 10).alias("k")).group_by("k").agg(pl.col("mid2").last(), pl.col("reset").max()).sort("k")
        k = k.with_columns(((pl.col("mid2") - pl.col("mid2").shift(1)) / 2).alias("dm"), (pl.col("k") - pl.col("k").shift(1)).alias("dk"))
        ti = AGG.filter((pl.col("s") >= (s - SH) // 1000) & (pl.col("s") < (e - SH) // 1000)).with_columns(((pl.col("s") * 1000 + SH) // 10000).alias("k")).group_by("k").agg(
            pl.col("ti_bybit").sum().alias("ti"))
        k = k.join(ti, on="k", how="left").with_columns(pl.col("ti").fill_null(0.0)).filter((pl.col("dk") == 1) & (pl.col("reset") == 0))
        X = np.column_stack([np.ones(k.height), k["ti"].to_numpy()]); out["kyle_lambda"] = float(np.linalg.lstsq(X, k["dm"].to_numpy(), rcond=None)[0][1])
    return out


def pval(pre, ref, higher=True):
    ref = np.array([r for r in ref if r == r]); ext = (ref >= pre) if higher else (ref <= pre)
    return float((1 + ext.sum()) / (1 + len(ref))), int(len(ref))


R = {}
W1 = pl.DataFrame([window_stats(s, H1, False) for s in starts(H1)])
W2 = pl.DataFrame([window_stats(s, H2, True) for s in starts(H2)])
for W, L, name in ((W1, H1, "1h"), (W2, H2, "2h")):
    W = W.with_columns((pl.col("start") == POST - L).alias("pre"), ((pl.col("start") + L > casc0) & (pl.col("start") < casc0 + 86_400_000)).alias("on_casc"))
    W.write_parquet(OUT / f"windows_{name}.parquet")
    pre = W.filter(pl.col("pre")).to_dicts()[0]; ref = W.filter(~pl.col("on_casc") & (pl.col("resets") == 0))
    R[name] = dict(pre=pre, n_ref=ref.height, ref_q=dict((c, ref[c].quantile(0.5)) for c in W.columns if c not in ("start", "pre", "on_casc")))
    if name == "1h":
        R["H8a_p"], _ = pval(pre["ti_bybit"], ref["ti_bybit"].to_list(), higher=False)
        R["H8b_p"], _ = pval(pre["ti_binance"], ref["ti_binance"].to_list(), higher=False)
        R["big_sells_p"] = {v: pval(pre[f"big_sells_{v}"], ref[f"big_sells_{v}"].to_list())[0] for v in ("bybit", "binance")}
        R["ofi_p"] = pval(pre["ofi"], ref["ofi"].to_list(), higher=False)[0]
        R["ti_rank"] = {v: float((ref[f"ti_{v}"] <= pre[f"ti_{v}"]).mean()) for v in ("bybit", "binance")}
    else:
        R["H9a_p"], _ = pval(pre["vpin"], ref["vpin"].to_list()); R["H9b_p"], _ = pval(pre["hawkes_n"], ref["hawkes_n"].to_list())
        R["H9c_p"], _ = pval(pre["kyle_lambda"], ref["kyle_lambda"].to_list())
        R["H9_pct"] = {c: float((ref[c] < pre[c]).mean()) for c in ("vpin", "hawkes_n", "kyle_lambda")}
    print(name, "pre", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in pre.items()}, "n_ref", ref.height, flush=True)
(OUT / "stats.json").write_text(json.dumps(R, default=float))
print({k: v for k, v in R.items() if k.endswith("_p") or k in ("H9_pct", "ti_rank", "big_sells_p")})
