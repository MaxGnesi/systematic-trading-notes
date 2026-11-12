"""Lecture 24 §4, what drove the differences: for the baseline and the tested designs on the 24 out-of-sample days, each fill's move after 1 s (bp,
signed for our side, from the fill price), by kind of fill (entry, resting close, stop at market) and by whether it came within 1 s of the previous fill
on the same side (a follow-up fill of the same sweep). Output: results/drivers.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_tests import TESTS
DESIGNS = {"baseline": "fills", TESTS["H1"]: "fills", TESTS["H2"]: "fills_corr", TESTS["H3"]: "fills", TESTS["H4"]: "fills_ledger"}

if __name__ == "__main__":
    days = sorted(p.stem for p in (L.RESULTS / "days").glob("*.json")); rows = []
    for d in days:
        S = pl.read_parquet(E.L21.STATE / f"{d}.parquet", columns=["ts", "bid", "ask"]).sort("ts"); ts = S["ts"].to_numpy(); mid = ((S["bid"] + S["ask"]) / 2).to_numpy(); del S
        bp = mid[len(mid) // 2] / 1e4
        for des, src in DESIGNS.items():
            F = pl.read_parquet(L.OUT / src / f"{d}.parquet").filter(pl.col("design") == des).sort("t")
            t, s, p = F["t"].to_numpy(), F["s"].to_numpy(), F["p"].to_numpy(); prev = np.full(len(t), np.inf)
            for side in (1, -1):
                j = np.nonzero(s == side)[0]; prev[j[1:]] = np.diff(t[j])
            rows.append(pl.DataFrame(dict(design=des, role=F["role"], m1=s * (mid[np.searchsorted(ts, t + 1_000, side="right") - 1] - p) / bp, follow=prev < 1_000)))
        del ts, mid; print(d, flush=True)
    T = pl.concat(rows); out = {}
    for (des,), g in T.group_by("design"):
        o = out.setdefault(des, {"fills": g.height, "m1_bp": float(g["m1"].mean())})
        o["by_role"] = {r: dict(share=x.height / g.height, m1_bp=float(x["m1"].mean())) for (r,), x in g.group_by("role")}
        o["follow_share"] = float(g["follow"].mean())
        for f, x in g.filter(pl.col("role") != "stop").group_by("follow"): o["resting_follow" if f[0] else "resting_first"] = float(x["m1"].mean())
    (L.RESULTS / "drivers.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items(): print(k, json.dumps(v))
