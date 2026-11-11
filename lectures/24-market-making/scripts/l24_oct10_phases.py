"""Lecture 24, 10 October as a case study (results/hypotheses.md, 2026-11-11): the phases of the crash from the mid alone, and each design's result split
into what its fills kept after 10 s, what its positions made or lost beyond that, and fees, per phase. From the saved fills of l24_oct10.py and l24_case.py.
Output: L24_RESULTS/oct10_phases.json, L24_OUT/oct10_paths.parquet (per second: mid, each design's result so far and position)."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_oct10 import DAY, WINDOWS
MAKER, TAKER = 2.0, 5.5                                                                            # bp, as in l24_tests.py
USDT = 0.1 * L.SIZE                                                                                # ticks x lots -> USDT


def phases(A, t0, t1):
    """Before, fall, bottom, rebound, after: from the mid alone (hypotheses.md)."""
    m = (A.ts >= t0) & (A.ts < t1); ts, mid = A.ts[m], A.mid[m]
    j = np.maximum(np.searchsorted(ts, ts - 1_000, side="right") - 1, 0)
    first = int(ts[np.nonzero(np.abs(mid - mid[j]) >= 10 * A.bp)[0][0]])
    k = int(np.argmin(mid)); tlow = int(ts[k]); b0, b1 = tlow - 150_000, tlow + 150_000
    after = ts >= b1; mx = np.maximum.accumulate(np.where(after, mid, -np.inf)); new = after & (mid >= mx) & np.r_[True, mid[1:] > mx[:-1]]
    th = ts[new]; gap = np.nonzero(np.diff(th) > 300_000)[0]; r1 = int(th[gap[0]]) if len(gap) else int(th[-1])
    return [("before", t0, first), ("fall", first, b0), ("bottom", b0, b1), ("rebound", b1, r1), ("after", r1, t1)], float(mid[0]), float(mid[k])


if __name__ == "__main__":
    F = pl.concat([pl.read_parquet(L.OUT / "oct10_fills.parquet").filter(~pl.col("design").str.starts_with("pp_"))]       # its ping-pong ran before the ledger fix: void
                  + [pl.read_parquet(L.OUT / f) for f in ("oct10_pp_fills.parquet", "oct10_case_quoters_fills.parquet", "oct10_case_pingpong_fills.parquet")])
    A = E.Arrays(DAY); (t0, t1), = E.blocks(DAY, WINDOWS); P, open_, low = phases(A, t0, t1)
    grid = np.arange(t0, t1, 1_000); gm = A.mid[np.searchsorted(A.ts, grid, side="right") - 1]
    paths = {"t": grid, "mid": gm * 0.1}                                                           # ticks -> USDT
    out = {"phases": [(n, a, b) for n, a, b in P], "open_mid": open_, "low_mid": low, "fall_bp": float((low - open_) / A.bp), "designs": {}}
    for d in F["design"].unique().sort().to_list():
        D = F.filter(pl.col("design") == d).sort("t"); t, s, p, tk = D["t"].to_numpy(), D["s"].to_numpy(), D["p"].to_numpy(), D["taker"].to_numpy()
        mk = s * (A.mid[np.searchsorted(A.ts, t + 10_000, side="right") - 1] - p)                 # what each fill kept after 10 s, ticks
        fee = p * np.where(tk, TAKER, MAKER) / 1e4
        def mtm(x):                                                                                # result before the fee up to time x, ticks
            n = np.searchsorted(t, x, side="right"); pos = s[:n].sum(); return -np.sum(s[:n] * p[:n]) + pos * A.mid[np.searchsorted(A.ts, x, side="right") - 1]
        n = np.searchsorted(t, grid, side="right"); cpos = np.r_[0, np.cumsum(s)][n]; ccash = np.r_[0, np.cumsum(-s * p)][n]
        paths[d] = (ccash + cpos * gm) * USDT; paths[d + "|pos"] = cpos
        R = {}
        for name, a, b in P:
            m = (t >= a) & (t < b); res = mtm(b - 1) - mtm(a - 1)
            R[name] = {"fills": int(m.sum()), "result": float(res * USDT), "kept_10s": float(mk[m].sum() * USDT), "positions": float((res - mk[m].sum()) * USDT),
                       "fees": float(-fee[m].sum() * USDT), "value": float(p[m].sum() * USDT), "max_pos": int(np.abs(np.cumsum(s)[m]).max()) if m.any() else 0}
        tot = {k: sum(R[x][k] for x in R) for k in ("fills", "result", "kept_10s", "positions", "fees", "value")}
        tot["after_fee"] = tot["result"] + tot["fees"]; tot["result_bp"] = 1e4 * tot["result"] / tot["value"] if tot["value"] else 0.0
        out["designs"][d] = {"phases": R, "total": tot}
    (L.RESULTS / "oct10_phases.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    pl.DataFrame(paths).write_parquet(L.OUT / "oct10_paths.parquet")
    hm = lambda x: __import__("datetime").datetime.utcfromtimestamp(x / 1000).strftime("%H:%M:%S")
    print("fall", round(out["fall_bp"], 1), "bp;", " | ".join(f"{n} {hm(a)}-{hm(b)}" for n, a, b in P))
    for d, v in sorted(out["designs"].items(), key=lambda kv: -kv[1]["total"]["after_fee"]):
        T = v["total"]; print(f"{d:24s} after fee {T['after_fee']:+8.1f}  before {T['result']:+8.1f} = kept10s {T['kept_10s']:+8.1f} + positions {T['positions']:+8.1f}; fees {T['fees']:+7.1f}; fills {T['fills']}")
