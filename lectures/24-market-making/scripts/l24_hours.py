"""Lecture 24, the hour of the day (results/hypotheses.md, 2026-11-11; described, not tested): per design, day and hour, the result before the fee and the
value traded from the saved fills of the 24 out-of-sample days, and the hour's volatility. No new replay; the mid is read once a second, streamed.
Output: results/hours.parquet (design, day, hour, result_usdt, value_usdt, fills, vol_bp)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_tests import TESTS
USDT = 0.1 * L.SIZE                                                                                # ticks x lots -> USDT
DESIGNS = ["baseline"] + list(TESTS.values())
SRC = {"days": L.OUT / "fills", "days_corr": L.OUT / "fills_corr", "days_ledger": L.OUT / "fills_ledger"}


def mid_seconds(day):
    """The mid at the end of every second of the day, in ticks (the last update at or before it)."""
    d0 = E.L21.ms(day)
    S = (pl.scan_parquet(E.L21.STATE / f"{day}.parquet").select("ts", ((pl.col("bid") + pl.col("ask")) / 2).alias("mid"))
         .group_by((pl.col("ts") - d0) // 1_000).agg(pl.col("mid").sort_by("ts").last()).collect(engine="streaming").sort("ts"))
    m = np.full(86_400, np.nan); k = S["ts"].to_numpy(); ok = (k >= 0) & (k < 86_400); m[k[ok]] = S["mid"].to_numpy()[ok]
    return pl.Series(m).fill_nan(None).forward_fill().backward_fill().to_numpy()


if __name__ == "__main__":
    days = sorted(p.stem for p in (L.RESULTS / "days").glob("*.json")); rows = []
    for day in days:
        d0 = E.L21.ms(day); m = mid_seconds(day); ends = m[np.arange(3_599, 86_400, 3_600)]; starts = np.r_[m[0], ends[:-1]]
        lm = np.log(m[59::60]); vol = np.sqrt(np.add.reduceat(np.r_[0, np.diff(lm)] ** 2, np.arange(0, 1_440, 60))) * 1e4
        for src, fdir in SRC.items():
            F = pl.read_parquet(fdir / f"{day}.parquet")
            for d in F["design"].unique().to_list():
                if d not in DESIGNS or (d.startswith("pp_") and src != "days_ledger"): continue          # ping-pong before the ledger fix: void
                D = F.filter(pl.col("design") == d).sort("t", maintain_order=True)
                t, s, p = D["t"].to_numpy(), D["s"].to_numpy(), D["p"].to_numpy(); h = (t - d0) // 3_600_000
                pos_end = np.array([s[h <= k].sum() for k in range(24)]); pos_start = np.r_[0, pos_end[:-1]]
                cash = np.bincount(h, -s * p, 24); val = np.bincount(h, p, 24); n = np.bincount(h, minlength=24)
                res = cash + pos_end * ends - pos_start * starts
                rows += [dict(design=d, day=day, hour=k, result_usdt=float(res[k] * USDT), value_usdt=float(val[k] * USDT), fills=int(n[k]), vol_bp=float(vol[k])) for k in range(24)]
        print(day, flush=True); del m
    pl.DataFrame(rows).write_parquet(L.RESULTS / "hours.parquet")
