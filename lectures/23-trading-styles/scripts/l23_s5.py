"""Lecture 23 §5: what our quotes meet. H21: the makers' adverse move (size x the mid's move in the taker's direction, gross) by footprint, against each footprint's share of taker size.
H22: after a Binance move (2 bp or more from the last price at least 100 ms before, the first in 1 s), the delay to the first Bybit taker order in its direction, against random moments of the same hour.
Per day to L23_RESULTS/s5_days/DAY.json. Usage: python l23_s5.py [DAY ...] (default: all days); python l23_s5.py --tests."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
import l22_styles as St, l23_s3 as S3
DAYS = L.RESULTS / "s5_days"; DAYS.mkdir(parents=True, exist_ok=True)
FP = ("sliced", "sniper", "large", "other"); HZ = ("m1000", "m10000", "m60000"); LAT = (10, 50, 100); H = 3_600_000


def h21(day, bt, bp):
    O = pl.read_parquet(L.L22.OUT / "orders" / f"{day}.parquet", columns=["ts", "side", "S", "cost_bp"] + list(HZ)).rename({"ts": "t", "S": "q"}).sort("t").with_columns(pl.col("q").round(3))
    _, run = St.runs(O); sn = S3.sniper_like(O["t"].to_numpy(), O["side"].to_numpy(), bt, bp); q = O["q"].to_numpy()
    fp = np.where(run >= 0, 0, np.where(sn, 1, np.where(q >= 1, 2, 3)))
    O = O.with_columns(pl.Series("fp", fp)).filter(pl.all_horizontal(pl.col(list(HZ)).is_not_nan()))
    G = O.group_by("fp").agg(pl.col("q").sum().alias("size"), (pl.col("q") * pl.col("cost_bp")).sum().alias("cost"), *[(pl.col("q") * pl.col("side") * pl.col(h)).sum().alias(h) for h in HZ])
    return {FP[r["fp"]]: {k: r[k] for k in ("size", "cost") + HZ} for r in G.iter_rows(named=True)}


def first_after(t0, side0, t, side):
    """For each moment t0 with direction side0, the delay in ms to the first order of t with that side at or after t0 (inf if none)."""
    out = np.full(len(t0), np.inf)
    for s in (1, -1):
        ts = t[side == s]; k = side0 == s; j = np.searchsorted(ts, t0[k], "left"); ok = j < len(ts)
        d = np.full(k.sum(), np.inf); d[ok] = ts[j[ok]] - t0[k][ok]; out[k] = d
    return out


def h22(day, bt, bp, rng):
    O = pl.read_parquet(L.L22.OUT / "orders" / f"{day}.parquet", columns=["ts", "side"]).sort("ts"); t, side = O["ts"].to_numpy(), O["side"].to_numpy()
    j = np.searchsorted(bt, bt - 100, "right") - 1; ok = j >= 0; mv = np.zeros(len(bt)); mv[ok] = (bp[ok] - bp[j[ok]]) / bp[j[ok]] * 1e4   # against the last price at least 100 ms before
    out = {}
    for jump in (2.0, 5.0):
        i = np.nonzero(np.abs(mv) >= jump)[0]; keep = []; last = -10**15
        for k in i:
            if bt[k] - last >= 1000: keep.append(k)
            last = bt[k] if bt[k] - last >= 1000 else last
        i = np.array(keep, dtype=int); te, de = bt[i], np.sign(mv[i]).astype(int)
        hk = te // H; tr = np.array([rng.integers(h * H, (h + 1) * H) for h in hk]) if len(hk) else np.array([], int); dr = rng.choice([-1, 1], len(tr))   # random moments, same hours
        d, dr_ = first_after(te, de, t, side), first_after(tr, dr, t, side)
        out[str(int(jump))] = dict(n=len(te), real={str(l): int((d <= l).sum()) for l in LAT}, rand={str(l): int((dr_ <= l).sum()) for l in LAT},
                                   hist=np.histogram(np.minimum(d, 1000), bins=np.arange(0, 1001, 5))[0].tolist(), hist_rand=np.histogram(np.minimum(dr_, 1000), bins=np.arange(0, 1001, 5))[0].tolist())
    return out


def tests():
    rng = np.random.default_rng(0); D = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(DAYS.glob("*.json"))}; R = {}
    for name, (a, b) in (("in", L.L22.IN_SAMPLE), ("out", L.L22.OUT_SAMPLE)):
        days = [d for d in D if a <= d <= b]; K = [rng.integers(0, len(days), len(days)) for _ in range(2000)]
        A = np.array([[[D[d]["h21"].get(f, {}).get(k, 0.0) for k in ("size", "cost") + HZ] for f in FP] for d in days])      # day x footprint x (size, cost, m1, m10, m60)
        share = lambda idx: A[idx, :, 3].sum(0) / A[idx, :, 3].sum() - A[idx, :, 0].sum(0) / A[idx, :, 0].sum()
        st = share(np.arange(len(days))); bs = np.array([share(i) for i in K]); tot = A.sum(0)
        R.setdefault(name, {})["H21"] = dict(stat=float(st[1]), p=float(np.mean(bs[:, 1] <= 0)), ci=np.percentile(bs[:, 1], [2.5, 97.5]).tolist(),
                                            size_share={f: float(tot[c, 0] / tot[:, 0].sum()) for c, f in enumerate(FP)}, adverse_share={f: float(tot[c, 3] / tot[:, 3].sum()) for c, f in enumerate(FP)},
                                            per_btc={f: dict(cost=float(tot[c, 1] / tot[c, 0]), **{h: float(tot[c, 2 + k] / tot[c, 0]) for k, h in enumerate(HZ)}) for c, f in enumerate(FP)},
                                            maker={f: {h: float((tot[c, 1] - tot[c, 2 + k]) / tot[c, 0]) for k, h in enumerate(HZ)} for c, f in enumerate(FP)},
                                            ci_share={f: np.percentile(bs[:, c], [2.5, 97.5]).tolist() for c, f in enumerate(FP)})
        o = {}
        for j in ("2", "5"):
            n = np.array([D[d]["h22"][j]["n"] for d in days]); re = {l: np.array([D[d]["h22"][j]["real"][str(l)] for d in days]) for l in LAT}; ra = {l: np.array([D[d]["h22"][j]["rand"][str(l)] for d in days]) for l in LAT}
            f = lambda idx, l: re[l][idx].sum() / n[idx].sum() - ra[l][idx].sum() / n[idx].sum()
            o[j] = dict(n=int(n.sum()), real={l: float(re[l].sum() / n.sum()) for l in LAT}, rand={l: float(ra[l].sum() / n.sum()) for l in LAT},
                        hist=np.sum([D[d]["h22"][j]["hist"] for d in days], 0).tolist(), hist_rand=np.sum([D[d]["h22"][j]["hist_rand"] for d in days], 0).tolist())
            bs = np.array([f(i, 50) for i in K]); o[j].update(stat=f(np.arange(len(days)), 50), p=float(np.mean(bs <= 0)), ci=np.percentile(bs, [2.5, 97.5]).tolist())
        R[name]["H22"] = o
    (L.RESULTS / "s5_tests.json").write_text(json.dumps(R, indent=1), encoding="utf-8"); return R


if __name__ == "__main__" and "--tests" in sys.argv:
    R = tests()
    for k in ("in", "out"): print(k, json.dumps({"H21": {x: R[k]["H21"][x] for x in ("stat", "p", "ci", "size_share", "adverse_share", "maker")}, "H22": {j: {x: v[x] for x in ("n", "real", "rand", "stat", "p", "ci")} for j, v in R[k]["H22"].items()}}, indent=0))
elif __name__ == "__main__":
    import time
    rng = np.random.default_rng(1)
    for d in [a for a in sys.argv[1:] if not a.startswith("--")] or S3.day_list():
        f = DAYS / f"{d}.json"
        if f.exists(): continue
        t0 = time.time(); bt, bp = S3.binance(d); r = dict(day=d, h21=h21(d, bt, bp), h22=h22(d, bt, bp, rng)); del bt, bp
        f.write_text(json.dumps(r), encoding="utf-8"); print(d, f"{time.time() - t0:.0f} s", r["h22"]["2"]["n"], flush=True)
