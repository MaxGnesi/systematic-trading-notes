"""Lecture 24, what speed is worth (described, not tested): as l24_lean_check.py, with the last moment to move a quote 100, 50, 30, 10 or 0 ms before
the fill. For each, the correlation of the Binance gap with the fill's result after 1 s, and the result per fill of the fills kept when those with the gap
more than x bp against us are skipped, against all fills. 0 ms is an ideal bound: no one can act on a price at the instant it prints.
Output: results/speed_check.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_after_fees import FIRST_OOS
from l24_lean_check import DAYS
LAGS = (100, 50, 30, 10, 0)


if __name__ == "__main__":
    rows = []
    for d in DAYS:
        A = E.Arrays(d); F = pl.read_parquet(L.OUT / "sample_fills" / f"{d}.parquet").filter(pl.col("design") == "baseline")
        t, s, p = F["t"].to_numpy(), F["s"].to_numpy(), F["p"].to_numpy()
        r = dict(oos=np.full(len(t), d >= FIRST_OOS), m1=s * (A.mid[np.searchsorted(A.ts, t + 1_000, side="right") - 1] - p) / A.bp)
        for lag in LAGS: r[f"g{lag}"] = -s * A.gap[np.maximum(np.searchsorted(A.ts, t - lag, side="right") - 1, 0)]
        rows.append(pl.DataFrame(r)); del A; print(d, flush=True)
    T = pl.concat(rows); out = {}
    for oos, G in T.group_by("oos"):
        m = G["m1"].to_numpy(); o = out.setdefault("oos" if oos[0] else "in", {"all_m1_bp": float(m.mean())})
        for lag in LAGS:
            g = G[f"g{lag}"].to_numpy()
            o[str(lag)] = dict(corr=float(np.corrcoef(g, m)[0, 1]),
                               **{f"skip{x}": dict(skipped=float((g > x).mean()), kept_m1_bp=float(m[g <= x].mean()), gain_bp=float(m[g <= x].mean() - m.mean()))
                                  for x in (0.5, 1, 2)})
    (L.RESULTS / "speed_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for w, o in out.items():
        print(w, "all fills", round(o["all_m1_bp"], 3))
        for lag in LAGS:
            v = o[str(lag)]; print(f"  {lag:3d} ms corr {v['corr']:+.3f} | " + " | ".join(f"skip >{x}: {v[f'skip{x}']['skipped']:5.1%} gain {v[f'skip{x}']['gain_bp']:+.3f}" for x in (0.5, 1, 2)))
