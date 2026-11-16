"""Re-score saved fills with l24_engine.score (no new replay). Usage: python l24_rescore.py sample|days [DAY ...]."""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l24 as L
import l24_engine as E, l24_run as R

if __name__ == "__main__":
    sample = sys.argv[1] == "sample"; out, fills = (L.RESULTS / "sample_days", L.OUT / "sample_fills") if sample else (R.DAYS, R.FILLS)
    days = sys.argv[2:] or sorted(p.stem for p in out.glob("*.json"))
    for d in days:
        F = pl.read_parquet(fills / f"{d}.parquet"); A = E.Arrays(d); B = E.blocks(d, R.WINDOWS if sample else None)
        S = {k: E.score(F.filter(pl.col("design") == k).drop("design").sort("t", maintain_order=True), A, B=B) for k in F["design"].unique(maintain_order=True)}
        (out / f"{d}.json").write_text(json.dumps(S), encoding="utf-8"); print(d, len(S), flush=True); del A
