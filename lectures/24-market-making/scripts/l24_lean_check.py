"""Lecture 24, could a lean on Binance have helped? (described, not tested): for the baseline's fills on the sampled hours, the Binance gap 50 ms before the
fill (the last moment our quote could still be moved), signed so that > 0 means Binance pointed against our fill, against the fill's move in the first
second; and the most that skipping the fills above a gap x could have saved. Output: results/lean_check.json."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E
from l24_after_fees import FIRST_OOS
DAYS = ("2025-09-24", "2025-09-30", "2025-10-06", "2025-10-13", "2025-10-21", "2025-10-29")
EDGES = [-np.inf, -2, -1, -0.5, 0, 0.5, 1, 2, np.inf]


if __name__ == "__main__":
    rows = []
    for d in DAYS:
        A = E.Arrays(d); F = pl.read_parquet(L.OUT / "sample_fills" / f"{d}.parquet").filter(pl.col("design") == "baseline")
        t, s, p = F["t"].to_numpy(), F["s"].to_numpy(), F["p"].to_numpy()
        g = -s * A.gap[np.maximum(np.searchsorted(A.ts, t - L.LAT, side="right") - 1, 0)]          # bp; > 0: Binance below our buy or above our sell
        m1 = s * (A.mid[np.searchsorted(A.ts, t + 1_000, side="right") - 1] - p) / A.bp           # the fill's result after 1 s, bp
        rows.append(pl.DataFrame(dict(day=[d] * len(t), oos=[d >= FIRST_OOS] * len(t), against=g, m1=m1))); del A; print(d, len(t), flush=True)
    T = pl.concat(rows); out = {}
    for oos, G in T.group_by("oos"):
        g, m = G["against"].to_numpy(), G["m1"].to_numpy(); n = len(g); k = np.digitize(g, EDGES[1:-1])
        bins = [dict(lo=EDGES[i], hi=EDGES[i + 1], share=float((k == i).mean()), m1_bp=float(m[k == i].mean()) if (k == i).any() else None) for i in range(len(EDGES) - 1)]
        skip = {str(x): dict(skipped=float((g > x).mean()), saved_bp_per_fill=float(-m[g > x].sum() / n)) for x in (0.5, 1, 2, 3)}
        out["oos" if oos[0] else "in"] = dict(fills=n, m1_bp=float(m.mean()), corr=float(np.corrcoef(g, m)[0, 1]), bins=bins, skip=skip)
    (L.RESULTS / "lean_check.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for w, o in out.items():
        print(w, o["fills"], "fills, mean 1 s", round(o["m1_bp"], 3), "corr", round(o["corr"], 3))
        for b in o["bins"]: print(f"   gap against {b['lo']:>5} to {b['hi']:>5}: {b['share']:6.1%} of fills, 1 s {b['m1_bp'] if b['m1_bp'] is None else round(b['m1_bp'], 2)} bp")
        for x, v in o["skip"].items(): print(f"   skip gap > {x} bp: {v['skipped']:.1%} of fills, saves {v['saved_bp_per_fill']:+.3f} bp per fill")
