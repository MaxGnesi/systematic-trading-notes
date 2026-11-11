"""Lecture 24, quoting deeper in the book (results/hypotheses.md, 2026-11-11; described, not tested): the baseline and quotes 1 to 10 bp behind the best on
the sampled hours, in and out of sample, before and after fees, with each fill's result split as in l24_key.py. Output: results/depth.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_tests import MAKER
from l24_after_fees import FIRST_OOS
USDT = 0.1 * L.SIZE


if __name__ == "__main__":
    days = sorted(p.stem for p in (L.RESULTS / "sample_days_depth").glob("*.json")); acc = {}
    for day in days:
        S = pl.read_parquet(E.L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).sort("ts")
        ts = S["ts"].to_numpy(); mid = ((S["bid"] + S["ask"]) / 2).to_numpy(); del S
        at = lambda t, side="right": mid[np.maximum(np.searchsorted(ts, t, side=side) - 1, 0)]
        for res_dir, fill_dir, only in (("sample_days_depth", "sample_fills_depth", None), ("sample_days", "sample_fills", "baseline")):
            R = json.loads((L.RESULTS / res_dir / f"{day}.json").read_text(encoding="utf-8")); F = pl.read_parquet(L.OUT / fill_dir / f"{day}.parquet")
            for d in ([only] if only else F["design"].unique().to_list()):
                D = F.filter(pl.col("design") == d); t, s, p = D["t"].to_numpy(), D["s"].to_numpy(), D["p"].to_numpy()
                m0 = at(t, "left"); m1, m10 = at(t + 1_000), at(t + 10_000)
                a = acc.setdefault((d, day >= FIRST_OOS), dict(spread=0.0, move_1s=0.0, move_10s=0.0, positions=0.0, result=0.0, value=0.0, fills=0, hours=0))
                sp, v1, v10 = (s * (m0 - p)).sum() * USDT, (s * (m1 - m0)).sum() * USDT, (s * (m10 - m1)).sum() * USDT
                a["spread"] += sp; a["move_1s"] += v1; a["move_10s"] += v10; a["positions"] += R[d]["result_usdt"] - sp - v1 - v10
                a["result"] += R[d]["result_usdt"]; a["value"] += R[d]["value_usdt"]; a["fills"] += len(t); a["hours"] += 4
        del ts, mid; print(day, flush=True)
    out = {}
    for (d, oos), a in acc.items():
        b = {k + "_bp": 1e4 * a[k] / a["value"] for k in ("spread", "move_1s", "move_10s", "positions", "result")}
        b.update(after_fee_bp=b["result_bp"] - MAKER, fills_hour=a["fills"] / a["hours"], after_fee_usdt_hour=(a["result"] - MAKER * a["value"] / 1e4) / a["hours"])
        out.setdefault(d, {})["oos" if oos else "in"] = b
    (L.RESULTS / "depth.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for d in ["baseline"] + [f"behind_{k}" for k in (110, 220, 330, 550, 1100)]:
        for w in ("in", "oos"):
            b = out[d][w]; print(f"{d:12s} {w:3s} before {b['result_bp']:+.2f} after {b['after_fee_bp']:+.2f} | spread {b['spread_bp']:+.2f} 1s {b['move_1s_bp']:+.2f} "
                                f"10s {b['move_10s_bp']:+.2f} pos {b['positions_bp']:+.2f} | {b['fills_hour']:6.0f} fills/h {b['after_fee_usdt_hour']:+7.1f} USDT/h")
