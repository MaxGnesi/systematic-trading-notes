"""Lecture 22 §4, H8: a condition on layer E (the market moves away from large size added at the best). Out of sample, at zero fee, at 300 control moments a day: a round trip
that posts a bid at the best bid as large as the queue there (x = 100%), sells 0.001 BTC at the best ask 1 s later and cancels the bid, against the same round trip without the bid.
With layer E on, the book moves up by E(tau) after the bid: E(1 s) = 0.25 bp and E(10 s) = 0.38 bp, Lecture 21's measurement for additions of 100% or more (its H8; measured on these same
days, there being no in-sample estimate; any positive E gives the same verdict as long as the bid is rarely filled), rising linearly over the first second. The bid is filled, generously,
by any sell trade whose price, moved by the shift, reaches it (touch); what it buys is held and marked to the mid 10 s after the bid. H8 holds if the round trip with the bid earns no more
than without it; p: share of 2,000 resamples of days at or below zero. Output: results/s4_h8.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L
OUT = L.RESULTS / "s4_h8.json"; E1, E10 = 0.25, 0.38; N = 300; B = 2000; rng = np.random.default_rng(8); Q = 0.001
OOS = sorted(p.stem for p in (L.OUT / "controls").glob("*.parquet") if L.OUT_SAMPLE[0] <= p.stem <= L.OUT_SAMPLE[1])


def one_day(d):
    S = pl.read_parquet(L.STATE / f"{d}.parquet").sort("ts"); st, bid, ask, qb = S["ts"].to_numpy(), S["bid"].to_numpy(), S["ask"].to_numpy(), S["q_bid"].to_numpy()
    T = pl.read_parquet(L.TRADES / f"{d}.parquet", columns=["ts", "side", "tick", "size"]).filter(pl.col("side") == -1).sort("ts"); tt, tk, tz = T["ts"].to_numpy(), T["tick"].to_numpy(), T["size"].to_numpy()
    C = pl.read_parquet(L.OUT / "controls" / f"{d}.parquet", columns=["ts"])["ts"].to_numpy(); t0s = np.sort(np.random.default_rng(int(d.replace("-", ""))).choice(C, min(N, len(C)), replace=False))
    at = lambda arr, t: arr[np.searchsorted(st, t, "right") - 1]; out = []
    for t0 in t0s:
        pb, size, mid0 = at(bid, t0), at(qb, t0), (at(bid, t0) + at(ask, t0)) / 2; e = lambda bp: bp * mid0 / 1e4      # bp to ticks
        i, j = np.searchsorted(tt, t0, "right"), np.searchsorted(tt, t0 + 1000, "right"); filled = 0.0
        for k in range(i, j):                                                         # a seller reaches our bid once the shift has moved the record up
            if tk[k] + e(E1) * min((tt[k] - t0) / 1000, 1.0) <= pb: filled = min(size, filled + tz[k])
        ask1 = at(ask, t0 + 1000); mid10 = (at(bid, t0 + 10_000) + at(ask, t0 + 10_000)) / 2
        gain = Q * e(E1) * 0.1                                                          # USDT (a tick is 0.1): the 0.001 BTC sells E(1 s) higher
        inv = filled * ((mid10 + e(E10)) - pb) * 0.1                                     # USDT: what the bid bought, marked 10 s later
        out.append(dict(t0=int(t0), size=float(size), filled=filled, gain=gain, inv=inv, diff=gain + inv, notional=Q * mid0 * 0.1))
    return out


if __name__ == "__main__":
    if "--run" in sys.argv or not OUT.exists():
        per = {d: one_day(d) for d in OOS}; days = list(per)
        stat = lambda i: np.mean([r["diff"] for j in i for r in per[days[j]]]); st = stat(range(len(days)))
        bs = np.array([stat(rng.integers(0, len(days), len(days))) for _ in range(B)]); allr = [r for d in days for r in per[d]]
        R = dict(E=[E1, E10], n=len(allr), H8=dict(p_violated=float(np.mean(bs <= 0)), mean_diff_usdt=float(st), ci=np.percentile(bs, [2.5, 97.5]).tolist(),
                 share_bid_touched=float(np.mean([r["filled"] > 0 for r in allr])), share_diff_positive=float(np.mean([r["diff"] > 0 for r in allr])),
                 mean_gain_bp=float(np.mean([r["gain"] / r["notional"] * 1e4 for r in allr])), median_diff_usdt=float(np.median([r["diff"] for r in allr]))))
        OUT.write_text(json.dumps(R, default=float), encoding="utf-8")
    else: R = json.loads(OUT.read_text(encoding="utf-8"))
    print(R["H8"], "n", R["n"])
