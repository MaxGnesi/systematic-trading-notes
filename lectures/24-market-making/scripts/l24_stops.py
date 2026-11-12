"""Lecture 24, stops with room for noise (results/hypotheses.md, 2026-11-11; described, not tested): each design with and without a stop, after fees, in and
out of sample on the sampled hours run; the share of value stopped; and what the mid does in the minute after a stop (keeps going: a trend; comes back:
noise). Output: results/stops.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_tests import MAKER, TAKER
from l24_after_fees import FIRST_OOS
BASE = {"baseline": "sample_days", "as_5_2": "sample_days", "pp_e0_a_n2": "sample_days_ledger"}


if __name__ == "__main__":
    days = sorted(p.stem for p in (L.RESULTS / "sample_days_stops").glob("*.json")); rows = []; after = []
    for d in days:
        S = json.loads((L.RESULTS / "sample_days_stops" / f"{d}.json").read_text(encoding="utf-8"))
        for k, src in BASE.items(): S[k] = json.loads((L.RESULTS / src / f"{d}.json").read_text(encoding="utf-8"))[k]
        F = pl.read_parquet(L.OUT / "sample_fills_stops" / f"{d}.parquet").with_columns((pl.col("p") * 0.1 * L.SIZE).alias("v"))
        tv = dict(F.filter(pl.col("taker")).group_by("design").agg(pl.col("v").sum()).iter_rows())
        A = E.Arrays(d); X = F.filter(pl.col("role") == "stop")
        t, s, p = X["t"].to_numpy(), X["s"].to_numpy(), X["p"].to_numpy()
        m60 = A.mid[np.searchsorted(A.ts, t + 60_000, side="right") - 1]
        after += [dict(design=k, back_bp=float(b)) for k, b in zip(X["design"].to_list(), s * (m60 - p) / A.bp)]   # > 0: the mid came back after the stop
        for k, x in S.items():
            rows.append(dict(day=d, oos=d >= FIRST_OOS, design=k, res=x["result_usdt"], val=x["value_usdt"], tval=tv.get(k, 0.0), fills=x["fills"],
                             stops=int((X["design"] == k).sum()), max_pos=x["max_pos"]))
        del A; print(d, flush=True)
    T = pl.DataFrame(rows); Q = pl.DataFrame(after); out = {"days": days, "designs": {}}
    for (k, oos), g in T.group_by("design", "oos"):
        r, v, tv = g["res"].sum(), g["val"].sum(), g["tval"].sum(); fee = (MAKER * (v - tv) + TAKER * tv) / 1e4
        out["designs"].setdefault(k, {})["oos" if oos else "in"] = dict(before_bp=1e4 * r / v, after_bp=1e4 * (r - fee) / v, stops=int(g["stops"].sum()),
                                                                         stop_value_share=tv / v, fills=int(g["fills"].sum()), max_pos=int(g["max_pos"].max()))
    for k, g in Q.group_by("design"):
        b = g["back_bp"].to_numpy(); out["designs"][k[0]]["after_stop"] = dict(n=len(b), median_back_bp=float(np.median(b)), share_back=float((b > 0).mean()))
    (L.RESULTS / "stops.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k in sorted(out["designs"]):
        v = out["designs"][k]; a = v.get("after_stop", {})
        print(f"{k:24s} in {v['in']['after_bp']:+.2f} oos {v['oos']['after_bp']:+.2f} bp after fees | before in {v['in']['before_bp']:+.2f} oos {v['oos']['before_bp']:+.2f}"
              f" | stops {v['in']['stops'] + v['oos']['stops']:5d} back {a.get('median_back_bp', float('nan')):+.1f} bp ({a.get('share_back', float('nan')):.0%}) maxpos {max(v['in']['max_pos'], v['oos']['max_pos'])}")
