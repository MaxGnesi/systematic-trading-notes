"""Lecture 24, a pause after each fill (results/hypotheses.md, 2026-11-12; described, not tested): before and after fees, fills an hour, in and out of
sample, against the designs without a pause; and the share of the baseline's loss after 1 s in fills within P of its previous fill on the same side.
Output: results/pause.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
from l24_tests import MAKER
from l24_after_fees import FIRST_OOS
from l24_lean_check import DAYS

if __name__ == "__main__":
    acc = {}
    for d in DAYS:
        S = json.loads((L.RESULTS / "sample_days_pause" / f"{d}.json").read_text(encoding="utf-8"))
        B = json.loads((L.RESULTS / "sample_days" / f"{d}.json").read_text(encoding="utf-8")); S["baseline"], S["as_5_2"] = B["baseline"], B["as_5_2"]
        for k, x in S.items():
            a = acc.setdefault((k, d >= FIRST_OOS), [0.0, 0.0, 0, 0]); a[0] += x["result_usdt"]; a[1] += x["value_usdt"]; a[2] += x["fills"]; a[3] += 4
    out = {"designs": {}}
    for (k, oos), (r, v, f, h) in acc.items():
        out["designs"].setdefault(k, {})["oos" if oos else "in"] = dict(before_bp=1e4 * r / v, after_bp=1e4 * r / v - MAKER, fills_hour=f / h)
    rows = []                                                                                      # the follow-up fills of the baseline (no pause)
    for d in DAYS:
        F = pl.read_parquet(L.OUT / "sample_fills" / f"{d}.parquet").filter(pl.col("design") == "baseline").sort("t")
        t, s = F["t"].to_numpy(), F["s"].to_numpy(); gap = np.full(len(t), np.inf)
        for side in (1, -1):
            j = np.nonzero(s == side)[0]; gap[j[1:]] = np.diff(t[j])
        rows.append(pl.DataFrame(dict(oos=[d >= FIRST_OOS] * len(t), gap=gap)))
    G = pl.concat(rows)
    out["followups"] = {("oos" if o[0] else "in"): {str(P): float((g["gap"] < P).mean()) for P in (200, 500, 1_000, 2_000, 5_000)} for o, g in G.group_by("oos")}
    (L.RESULTS / "pause.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k in sorted(out["designs"]):
        i, o = out["designs"][k]["in"], out["designs"][k]["oos"]
        print(f"{k:20s} in {i['before_bp']:+.3f} ({i['fills_hour']:5.0f}/h)  oos {o['before_bp']:+.3f} ({o['fills_hour']:5.0f}/h)")
    print("share of baseline fills within P of the previous same-side fill:", out["followups"])
