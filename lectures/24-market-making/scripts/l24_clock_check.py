"""Lecture 24, are quotes hit worse around round times? (described, not tested): the baseline's fills on the 24 out-of-sample days by the second within
the minute and the minute within the hour, with each fill's move after 1 s (bp, signed for our side) and its share of fills. Output: results/clock_check.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E

if __name__ == "__main__":
    days = sorted(p.stem for p in (L.RESULTS / "days").glob("*.json")); rows = []
    for d in days:
        S = pl.read_parquet(E.L21.STATE / f"{d}.parquet", columns=["ts", "bid", "ask"]).sort("ts"); ts = S["ts"].to_numpy(); mid = ((S["bid"] + S["ask"]) / 2).to_numpy(); del S
        F = pl.read_parquet(L.OUT / "fills" / f"{d}.parquet").filter(pl.col("design") == "baseline"); t, s, p = F["t"].to_numpy(), F["s"].to_numpy(), F["p"].to_numpy()
        bp = np.median(mid) / 1e4
        m1 = s * (mid[np.searchsorted(ts, t + 1_000, side="right") - 1] - p) / bp
        rows.append(pl.DataFrame(dict(sec=(t // 1000) % 60, minute=(t // 60_000) % 60, hour=(t // 3_600_000) % 24, m1=m1))); del ts, mid; print(d, flush=True)
    T = pl.concat(rows); out = {"all": float(T["m1"].mean()), "fills": T.height}
    for name, cond in (("sec 0-2", pl.col("sec") < 3), ("sec 3-9", pl.col("sec").is_between(3, 9)), ("sec 10-59", pl.col("sec") >= 10),
                       ("minute 59-01", pl.col("minute").is_in([59, 0, 1])), ("minutes 29-31", pl.col("minute").is_in([29, 30, 31])), ("other minutes", ~pl.col("minute").is_in([59, 0, 1, 29, 30, 31])),
                       ("hour 21", pl.col("hour") == 21)):
        g = T.filter(cond); out[name] = dict(share=g.height / T.height, m1_bp=float(g["m1"].mean()), fills_per_sec=g.height)
    (L.RESULTS / "clock_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("all", round(out["all"], 3), out["fills"])
    for k, v in out.items():
        if isinstance(v, dict): print(f"{k:14s} share {v['share']:6.1%}  1 s {v['m1_bp']:+.3f} bp")
