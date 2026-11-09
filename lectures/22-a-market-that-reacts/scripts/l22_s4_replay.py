"""Lecture 22 §4, H7: runs of real orders, out of sample. A run: orders on one side, starting with any order, that add up to 5 BTC or more within 10 s of the first, with no order of
1 BTC or more on the other side in between; found greedily, without overlap. The record after a run's start already contains the run, so both replays use the book as it stood at the start:
the plain replay walks every order of the run into that book as it was; the hybrid replay walks them in turn with layers A, B and C. The error is the predicted average price of the run
less its actual average price, in bp, signed for the side. H7: the mean absolute error of the hybrid is below that of the plain replay; p from 2,000 resamples of days. Busy days hold
thousands of runs, so a fixed random sample of 300 runs per day is replayed (fixed before any result).
Output: results/s4_replay.json. --run recomputes; --days N limits the run to the first N out-of-sample days (a test)."""
import json, sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L, l22_hybrid as H
OUT = L.RESULTS / "s4_replay.json"; B = 2000; rng = np.random.default_rng(7)
OOS = sorted(p.stem for p in (L.OUT / "orders").glob("*.parquet") if L.OUT_SAMPLE[0] <= p.stem <= L.OUT_SAMPLE[1])


def runs(day):
    O = pl.read_parquet(L.OUT / "orders" / f"{day}.parquet", columns=["ts", "side", "S", "avg", "mid0"]).sort("ts"); t, sd, S = O["ts"].to_numpy(), O["side"].to_numpy(), O["S"].to_numpy()
    out = []; i = 0; n = len(t)
    while i < n:
        j = i; tot = 0.0; ok = True
        while j < n and t[j] <= t[i] + 10_000:
            if sd[j] != sd[i] and S[j] >= 1: ok = False; break
            if sd[j] == sd[i]: tot += S[j]
            if tot >= 5: break
            j += 1
        if ok and tot >= 5 and j < n:
            idx = [k for k in range(i, j + 1) if sd[k] == sd[i]]; out.append(idx); i = j + 1
        else: i += 1
    return O, out


PER_DAY = 300


PARENT = "--parent" in sys.argv                                                    # follow-up after H7: a run's impact from its cumulative size
if PARENT: OUT = L.RESULTS / "s4_replay_parent.json"


def one_day(day, resp, refill):
    """A fixed random sample of PER_DAY runs per day (seeded by the date): busy days hold thousands of runs, and every run needs two replays."""
    O, R = runs(day); res = []; n_all = len(R)
    if len(R) > PER_DAY: R = [R[i] for i in sorted(np.random.default_rng(int(day.replace("-", ""))).choice(len(R), PER_DAY, replace=False))]
    for idx in R:
        t0, side = int(O["ts"][idx[0]]), int(O["side"][idx[0]]); sizes = O["S"].to_numpy()[idx]; times = O["ts"].to_numpy()[idx]
        actual = float((O["avg"].to_numpy()[idx] * sizes).sum() / sizes.sum()); mid0 = float(O["mid0"][idx[0]])
        pred = {}
        for name, layers in (("plain", ""), ("hybrid", "ABC")):
            h = H.Hybrid(day, t0 - 1, t0 - 1, layers=layers, resp=resp, refill=refill, parent=PARENT); paid = 0.0; got = 0.0
            for tt, z in zip(times, sizes):
                if name == "plain": h.ours = []                                       # the plain replay keeps no memory of earlier orders
                f, left = h.market_order(int(tt), side, float(z)); paid += sum(p * q for p, q in f); got += sum(q for _, q in f)
            pred[name] = paid / got if got else np.nan
        res.append(dict(n_all=n_all, t0=t0, side=side, n=len(idx), S=float(sizes.sum()), secs=float((times[-1] - times[0]) / 1000), actual=actual,
                        err_plain=side * (pred["plain"] - actual) / mid0 * 1e4, err_hybrid=side * (pred["hybrid"] - actual) / mid0 * 1e4))
    return res


if __name__ == "__main__":
    if "--run" in sys.argv or not OUT.exists():
        nd = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else len(OOS); resp, refill = H.fit_response(), H.fit_refill(); per = {}
        for d in OOS[:nd]:
            t1 = time.time(); per[d] = one_day(d, resp, refill); print(d, len(per[d]), "runs", round(time.time() - t1), "s", flush=True)
        days = list(per); stat = lambda i: np.mean([abs(r["err_plain"]) - abs(r["err_hybrid"]) for j in i for r in per[days[j]]])
        st = stat(range(len(days))); bs = np.array([stat(rng.integers(0, len(days), len(days))) for _ in range(B)])
        allr = [r for d in days for r in per[d]]
        R = dict(days=days, runs=len(allr), H7=dict(p=float(np.mean(bs <= 0)), stat=float(st), ci=np.percentile(bs, [2.5, 97.5]).tolist(),
                 mae_plain=float(np.mean([abs(r["err_plain"]) for r in allr])), mae_hybrid=float(np.mean([abs(r["err_hybrid"]) for r in allr])),
                 bias_plain=float(np.mean([r["err_plain"] for r in allr])), bias_hybrid=float(np.mean([r["err_hybrid"] for r in allr])), what="mean |error| plain minus hybrid, bp"), per=per)
        if "--days" not in sys.argv: OUT.write_text(json.dumps(R, default=float), encoding="utf-8")
    else: R = json.loads(OUT.read_text(encoding="utf-8"))
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in R["H7"].items()}, "runs", R["runs"])
