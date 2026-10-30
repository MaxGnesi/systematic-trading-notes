"""Lecture 19 figure 19_11, right panel, the data: for each day of L19_OUT/s3/b2_cand_*, the spoof candidates (at least 5 BTC added 1-9 ticks behind
the best, removed within 2 s without a trade at their price), by distance: the sums of the absolute change of the plain and the distance-weighted
imbalance they caused, and their number. Output: L19_OUT/l19_cand_offsets.json; with days given, L19_OUT/check_l19_cand_offsets.json. Usage: python l19_cand_summary.py [DAY ...]."""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19

DAYS = sys.argv[1:]                                                                   # given days: a check, written to check_*.json
R = {}
for f in ([L19.S3 / f"b2_cand_{d}.parquet" for d in DAYS] if DAYS else sorted(L19.S3.glob("b2_cand_*.parquet"))):
    C = pl.read_parquet(f).filter((pl.col("add") >= 5) & pl.col("removed") & ~pl.col("traded") & (pl.col("life") <= 2000) & pl.col("d_plain").is_not_nan())
    O = C.group_by("off").agg(pl.col("d_plain").abs().sum().alias("plain"), pl.col("d_dist").abs().sum().alias("dist"), pl.len().alias("n"))
    R[f.stem.replace("b2_cand_", "")] = {str(int(r["off"])): [r["plain"], r["dist"], int(r["n"])] for r in O.iter_rows(named=True)}
(L19.OUT / (("check_" if DAYS else "") + "l19_cand_offsets.json")).write_text(json.dumps(R))
print("days:", len(R), "candidates:", sum(v[2] for d in R.values() for v in d.values()))
