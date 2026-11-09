"""Lecture 22: a few numbers of one day from the order table and the book pass (l22_orders.py, l22_book.py), to compare a rerun with the lecture's values.
Output: RESULTS/check_DAY.json. Usage: python l22_check_day.py YYYY-MM-DD"""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L

DAY = sys.argv[1]
X = pl.read_parquet(L.OUT / "orders" / f"{DAY}.parquet"); B = pl.read_parquet(L.OUT / "book" / f"{DAY}.parquet")
F = pl.read_parquet(L.OUT / "refill" / f"{DAY}.parquet").filter((pl.col("met") > 0) & (pl.col("probe") == 1000)); big = X.filter(pl.col("S") >= 1)
out = {"orders": X.height, "orders of 1 BTC or more": big.height, "share of book messages that were quote pulls": float(B["pull"].mean()),
       "share of orders of 1 BTC or more with 90% of the depth back near the new best within 1 s": float((F["near"] >= 0.9 * F["met"]).mean()),
       "mean move at 10 s after orders of 1 BTC or more, in their direction, bp (not net)": float((big["side"] * big["m10000"]).mean())}
(L.RESULTS / f"check_{DAY}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
for k, v in out.items(): print(k, round(v, 4) if isinstance(v, float) else v)
