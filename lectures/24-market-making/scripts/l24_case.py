"""Lecture 24, 10 October as a case study (results/hypotheses.md, 2026-11-11): the added designs, same window as l24_oct10.py.
Usage: python l24_case.py quoters|pingpong. Output: L24_RESULTS/oct10_case_JOB.json, L24_OUT/oct10_case_JOB_fills.parquet."""
import json, sys, time
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E, l24_designs as G
from l24_oct10 import DAY, WINDOWS
C = ("c", 110, 110, 60_000)

if __name__ == "__main__":
    job = sys.argv[1]
    if job == "quoters":
        D = [G.Kill(G.Quoter(), x, off=o * 1000) for x in (5, 10, 20) for o in (10, 30, 60) if (x, o) != (10, 30)] + [G.Quoter(theta=1), G.Quoter(theta=5), G.AS(5, 0), G.AS(5, 1)]
    else:
        D = [G.PingPong(0, "a", ("n", 2)), G.PingPong(0, ("b", 110), ("n", 2)), G.PingPong(0, C, ("n", 1))]
    t0 = time.time(); R, A = E.run_days(DAY, D, windows=WINDOWS); B = E.blocks(DAY, WINDOWS)
    pl.concat([f.with_columns(pl.lit(k).alias("design")) for k, f in R.items()]).write_parquet(L.OUT / f"oct10_case_{job}_fills.parquet")
    S = {k: E.score(f, A, B=B) for k, f in R.items()}
    (L.RESULTS / f"oct10_case_{job}.json").write_text(json.dumps(S, indent=1), encoding="utf-8"); print(f"{time.time() - t0:.0f} s")
    for k, s in S.items(): print(f"{k:24s} fills {s.get('fills', 0):6d} result {s.get('result_bp', 0):+7.2f} bp  {s.get('result_usdt', 0):+8.1f} USDT  mk10 {s.get('mk10', 0):+6.2f}  max pos {s.get('max_pos', 0)}")
