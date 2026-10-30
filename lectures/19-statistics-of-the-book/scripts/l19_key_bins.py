"""Lecture 19 figure 19_02, the data: for each day of L19_OUT/state, the updates with a one-tick spread, in 20 bands of the imbalance at the best
just before; per band the sum of the imbalance, the number of next mid moves that were up, and the number of updates.
Output: L19_OUT/l19_key_bins.json; with days given, L19_OUT/check_l19_key_bins.json. Usage: python l19_key_bins.py [DAY ...]"""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l19 as L19

DAYS = sys.argv[1:]                                                                   # given days: a check, written to check_*.json
R = {}
for f in ([L19.STATE / f"{d}.parquet" for d in DAYS] if DAYS else sorted(L19.STATE.glob("*.parquet"))):
    X = pl.read_parquet(f).with_columns(((pl.col("bid") + pl.col("ask")) / 2).alias("mid"))
    X = X.with_columns(pl.when(pl.col("mid") != pl.col("mid").shift(-1)).then(pl.col("mid").shift(-1)).otherwise(None).backward_fill().alias("next_mid"))
    X = X.filter((pl.col("ask") - pl.col("bid")) == 1).drop_nulls("next_mid")
    X = X.with_columns(((pl.col("q_bid") - pl.col("q_ask")) / (pl.col("q_bid") + pl.col("q_ask"))).alias("I"), (pl.col("next_mid") > pl.col("mid")).alias("up"))
    G = X.with_columns(((pl.col("I") + 1) / 2 * 20).floor().clip(0, 19).alias("b")).group_by("b").agg(pl.col("I").sum().alias("si"), pl.col("up").sum().alias("su"), pl.len().alias("n"))
    R[f.stem] = {str(int(r["b"])): [r["si"], int(r["su"]), int(r["n"])] for r in G.iter_rows(named=True)}
(L19.OUT / (("check_" if DAYS else "") + "l19_key_bins.json")).write_text(json.dumps(R))
print("days:", len(R))
