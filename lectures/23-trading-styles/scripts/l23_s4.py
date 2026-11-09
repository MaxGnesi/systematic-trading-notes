"""Lecture 23 §4: H13 and H14, the style shares hour by hour. Each taker order goes to one footprint, in this order: sliced (H12's runs), sniper-like (H10), large (1 BTC or more), other.
The clock-like share is the extra taker size in the first 3 s after each whole minute over seconds 10 to 49 of the same minute (H11), summed over the hour, as a share of its taker size.
An hour's volatility: the square root of the sum of squared 1-minute changes of the log mid, in bp. Thirds of volatility are fixed in sample, separately for each hour of the day.
Per day to L23_RESULTS/s4_hours/DAY.parquet. Usage: python l23_s4.py [DAY ...] (default: all days); python l23_s4.py --tests."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l23 as L
import l22_styles as St, l23_s3 as S3
HOURS = L.RESULTS / "s4_hours"; HOURS.mkdir(parents=True, exist_ok=True); H = 3_600_000


def day_hours(day):
    O = pl.read_parquet(L.L22.OUT / "orders" / f"{day}.parquet", columns=["ts", "side", "S"]).rename({"ts": "t", "S": "q"}).sort("t").with_columns(pl.col("q").round(3))
    _, run = St.runs(O); bt, bp = S3.binance(day); sn = S3.sniper_like(O["t"].to_numpy(), O["side"].to_numpy(), bt, bp); del bt, bp
    q = O["q"].to_numpy(); sl = run >= 0; sn = sn & ~sl; lg = (q >= 1) & ~sl & ~sn
    X = O.with_columns(pl.Series("sliced", np.where(sl, q, 0.0)), pl.Series("sniper", np.where(sn, q, 0.0)), pl.Series("large", np.where(lg, q, 0.0)), (pl.col("t") // H).alias("hk"))
    G = X.group_by("hk").agg(pl.col("q").sum().alias("taker"), pl.col("sliced", "sniper", "large").sum())
    Q = pl.read_parquet(L.L22.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).rename({"ts": "t"}).sort("t")
    M = St.marks(O, Q).with_columns((pl.col("g0") - pl.col("gc")).alias("clock"), (pl.col("t") // H).alias("hk")).group_by("hk").agg(pl.col("clock").sum())
    qt = Q["t"].to_numpy(); mid = (Q["bid"].to_numpy() + Q["ask"].to_numpy()) / 2.0; grid = np.arange((qt[0] // 60_000 + 1) * 60_000, qt[-1], 60_000)
    m = np.log(mid[np.searchsorted(qt, grid, "right") - 1]); V = pl.DataFrame(dict(hk=grid[1:] // H, r2=np.diff(m) ** 2)).group_by("hk").agg((pl.col("r2").sum().sqrt() * 1e4).alias("vol"))
    return G.join(M, on="hk", how="left").join(V, on="hk", how="left").with_columns(pl.lit(day).alias("day"), (pl.col("hk") % 24).alias("hour")).sort("hk")


def tests():
    """H13: Spearman correlation of the 24-hour profiles in sample and out of sample, for the sliced, sniper-like and clock-like shares; H14: within each hour of the day, the share in the most
    volatile third less the least volatile third, averaged over the hours, out of sample. One-sided p from 2,000 resamples of days."""
    from scipy.stats import spearmanr
    rng = np.random.default_rng(0); STY = ("sliced", "sniper", "clock", "large"); F = ("taker",) + STY
    A = pl.concat([pl.read_parquet(p) for p in sorted(HOURS.glob("*.parquet"))]).with_columns(pl.col("clock").fill_null(0.0))
    days = sorted(A["day"].unique().to_list()); X = np.zeros((len(days), 24, len(F))); V = np.full((len(days), 24), np.nan)
    for r in A.iter_rows(named=True):
        k = days.index(r["day"]); X[k, r["hour"]] = [r[f] for f in F]; V[k, r["hour"]] = r["vol"]
    di = [k for k, d in enumerate(days) if L.L22.IN_SAMPLE[0] <= d <= L.L22.IN_SAMPLE[1]]; do = [k for k, d in enumerate(days) if L.L22.OUT_SAMPLE[0] <= d <= L.L22.OUT_SAMPLE[1]]
    v1, v2 = np.nanquantile(V[di], 1 / 3, axis=0), np.nanquantile(V[di], 2 / 3, axis=0)            # thirds fixed in sample, per hour of the day
    third = np.where(V <= v1, 0, np.where(V > v2, 2, 1))
    profile = lambda idx: X[idx].sum(0)[:, 1:] / X[idx].sum(0)[:, :1]                            # 24 x styles
    def h14(idx):
        hi = (X[idx] * (third[idx] == 2)[..., None]).sum(0); lo = (X[idx] * (third[idx] == 0)[..., None]).sum(0)
        ok = (hi[:, 0] > 0) & (lo[:, 0] > 0); return (hi[ok, 1:] / hi[ok, :1] - lo[ok, 1:] / lo[ok, :1]).mean(0)
    Pi, Po = profile(di), profile(do); st14 = h14(do); sign = dict(sliced=-1, sniper=1, clock=1, large=0)
    b13, b14 = [], []
    for _ in range(2000):
        bi, bo = rng.choice(di, len(di)), rng.choice(do, len(do)); pi, po = profile(bi), profile(bo)
        b13.append([spearmanr(pi[:, c], po[:, c])[0] for c in range(len(STY))]); b14.append(h14(bo))
    b13, b14 = np.array(b13), np.array(b14); R = dict(H13={}, H14={}, profile_in={s: Pi[:, c].tolist() for c, s in enumerate(STY)}, profile_out={s: Po[:, c].tolist() for c, s in enumerate(STY)})
    for c, s in enumerate(STY):
        R["H13"][s] = dict(rho=float(spearmanr(Pi[:, c], Po[:, c])[0]), p=float(np.mean(b13[:, c] <= 0)), ci=np.percentile(b13[:, c], [2.5, 97.5]).tolist())
        R["H14"][s] = dict(diff=float(st14[c]), p=float(np.mean(sign[s] * b14[:, c] <= 0)) if sign[s] else None, ci=np.percentile(b14[:, c], [2.5, 97.5]).tolist(),
                           by_third=[float((X[do] * (third[do] == t)[..., None]).sum((0, 1))[c + 1] / (X[do] * (third[do] == t)[..., None]).sum((0, 1))[0]) for t in range(3)])
    R["shares"] = {k: {s: float(X[idx].sum((0, 1))[c + 1] / X[idx].sum((0, 1))[0]) for c, s in enumerate(STY)} for k, idx in (("in", di), ("out", do))}
    R["daily"] = [dict(day=d, **{s: float(X[k].sum(0)[c + 1] / X[k].sum(0)[0]) for c, s in enumerate(STY)}) for k, d in enumerate(days)]
    R["vol_hour"] = np.nanmedian(V[do], 0).tolist()
    (L.RESULTS / "s4_tests.json").write_text(json.dumps(R, indent=1), encoding="utf-8"); return R


if __name__ == "__main__" and "--tests" in sys.argv:
    R = tests(); print("H13", R["H13"]); print("H14", R["H14"]); print("shares", R["shares"]); print({k: v["by_third"] for k, v in R["H14"].items()})
elif __name__ == "__main__":
    import time
    for d in [a for a in sys.argv[1:] if not a.startswith("--")] or S3.day_list():
        f = HOURS / f"{d}.parquet"
        if f.exists(): continue
        t0 = time.time(); day_hours(d).write_parquet(f); print(d, f"{time.time() - t0:.0f} s", flush=True)
