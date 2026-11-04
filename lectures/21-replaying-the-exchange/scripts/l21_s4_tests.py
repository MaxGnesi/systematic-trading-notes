"""Lecture 21 §4: H1, H2, H3 and H5 from the chains of l21_mm.py (L21_OUT/mm). The test resting order is the instant quoter, 0.001 BTC, L = 50 ms, out of
sample. Markout: the mid h seconds after the fill minus the fill price, signed for our side, bp. Uncertainty: 2,000 resamples of days; one-sided p-values.
H1: 1-s markout under Q0 > Q2 (a = 1) (primary), Q2 > Q1. H2: non-adverse > adverse, under Q2. H3 (no test): the grid computed, a in {1, infinity}, L in
{10, 50, 100}, eight days; fill rate and 10-s markout after the 2 bp fee. H5: fills under Q2 in the first 10 s of minutes :00 and :30 have a lower 1-s markout.
Output: L21_OUT/s4/h1235.parquet (one row per contrast or grid point). Usage: python l21_s4_tests.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
OUT = L21.OUT / "s4"; OUT.mkdir(exist_ok=True); rng = np.random.default_rng(0); FEE = 2.0
files = sorted((L21.OUT / "mm").glob("*.parquet"))
BASE = (pl.scan_parquet(files).filter(pl.col("filled") & (pl.col("quoter") == "instant"))
        .with_columns(((pl.col("mid1") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m1"), ((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10")))
T = BASE.filter(pl.col("L") == 50).select("day", "rule", "side", "end", "adverse", "m1", "m10").collect()
days = sorted(T["day"].unique().to_list()); idx = rng.integers(0, len(days), (2000, len(days)))


def daily(G, col="m1"):
    d = G.group_by("day").agg(pl.len().alias("n"), pl.col(col).sum().alias("s")); g = dict(zip(d["day"], zip(d["n"], d["s"])))
    return np.array([g.get(x, (0, 0.0)) for x in days], dtype=float)


def contrast(A, B, name, q):
    """Mean(A) - mean(B) over fills, with resampling of days; p: share of resamples at or below zero."""
    a, b = daily(A), daily(B); f = lambda v: v[..., 1].sum(-1) / v[..., 0].sum(-1)
    bs = f(a[idx]) - f(b[idx]); on = lambda v: float(f(v))
    return dict(test=name, question=q, a=on(a), b=on(b), diff=on(a) - on(b), lo=float(np.quantile(bs, 0.025)), hi=float(np.quantile(bs, 0.975)), p=float((bs <= 0).mean()), days=len(days), fills_a=int(a[:, 0].sum()), fills_b=int(b[:, 0].sum()))


Q0, Q1, Q2 = (T.filter(pl.col("rule") == r) for r in ("Q0", "Q1", "Q2 a=1"))
rows = [contrast(Q0, Q2, "H1", "touch above queue"), contrast(Q2, Q1, "H1b", "queue above trade-through"),
        contrast(Q2.filter(~pl.col("adverse")), Q2.filter(pl.col("adverse")), "H2", "non-adverse above adverse")]
Q2c = Q2.with_columns(pl.from_epoch("end", time_unit="ms").alias("tm")).with_columns(((pl.col("tm").dt.minute().is_in([0, 30])) & (pl.col("tm").dt.second() < 10)).alias("clock"))
rows.append(contrast(Q2c.filter(~pl.col("clock")), Q2c.filter(pl.col("clock")), "H5", "other times above the clock moments"))
pl.DataFrame(rows).write_parquet(OUT / "h1235.parquet")
G8 = (pl.scan_parquet(files).filter((pl.col("quoter") == "instant") & pl.col("rule").str.starts_with("Q2") & pl.col("day").is_in(list(L21_D := __import__("l21_mm").DAYS)))
      .with_columns(((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10"))
      .group_by("rule", "L").agg(pl.col("filled").mean().alias("fill_rate"), pl.col("filled").sum().alias("fills"), pl.col("m10").filter(pl.col("filled")).mean().alias("m10"))
      .with_columns((pl.col("m10") - FEE).alias("m10_fee")).sort("rule", "L").collect())
G8.write_parquet(OUT / "h3.parquet")
with pl.Config(tbl_rows=30, tbl_cols=20, tbl_width_chars=220, float_precision=3):
    print(pl.DataFrame(rows).drop("question")); print(G8); print("clock share of fills", Q2c["clock"].mean())
