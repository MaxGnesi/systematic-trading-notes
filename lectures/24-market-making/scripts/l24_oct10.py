"""Lecture 24, 10 October (results/hypotheses.md): the five tested designs with and without the kill switch, 20:30 - 23:00 UTC (the half-hour windows
holding 20:50 - 22:50), starting flat at 20:30. Output: L24_RESULTS/oct10.json, L24_OUT/oct10_fills.parquet."""
import json, sys, time
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E, l24_designs as G
DAY = "2025-10-10"; WINDOWS = tuple(range(41, 46))

if __name__ == "__main__":
    pp_only = "--pp" in sys.argv                                                                   # H4 again after the ledger fix (hypotheses.md, 2026-11-11)
    base = [G.PingPong(0, ("c", 110, 110, 60_000), ("n", 2))] if pp_only else [G.Quoter(), G.Quoter(theta=2), G.Quoter(k=1), G.AS(5, 2), G.PingPong(0, ("c", 110, 110, 60_000), ("n", 1))]
    D = base + [G.Kill(d) for d in base]; t0 = time.time()
    R, A = E.run_days(DAY, D, windows=WINDOWS); B = E.blocks(DAY, WINDOWS)
    pl.concat([f.with_columns(pl.lit(k).alias("design")) for k, f in R.items()]).write_parquet(L.OUT / ("oct10_pp_fills.parquet" if pp_only else "oct10_fills.parquet"))
    S = {k: E.score(f, A, B=B) for k, f in R.items()}
    (L.RESULTS / ("oct10_pp.json" if pp_only else "oct10.json")).write_text(json.dumps(S, indent=1), encoding="utf-8"); print(f"{time.time() - t0:.0f} s")
    for k, s in S.items(): print(f"{k:22s} fills {s.get('fills', 0):6d} result {s.get('result_bp', 0):+7.2f} bp  {s.get('result_usdt', 0):+8.1f} USDT  mk10 {s.get('mk10', 0):+6.2f}  max pos {s.get('max_pos', 0)}")
