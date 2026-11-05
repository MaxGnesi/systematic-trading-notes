"""Lecture 21 §4 and §5: H6, H7 and H9 from the jobs of l21_s4_h679.py, and the verdicts on all tests: Benjamini-Hochberg at 5% over the primary p-values.
H6: in the cascade window, 20:50-22:50 UTC, the test resting order's share of adverse fills and loss per fill (10-s markout) on 10 October against the same window on the other 44
days; p: rank of 10 October among the 45. H7: mean gap of real taker orders of 5 BTC or more minus below 0.01 BTC; orders the 200 levels could not price are counted and left out.
H9: 10 bp from the mid, the share filled under Q2 (a = 1) minus Q1; the 10-s markout of the fills Q1 misses minus that of Q1's fills. Resamples of days: 2,000; one-sided.
Output: L21_OUT/s4/ h6.parquet, h7.parquet, h9.parquet, verdicts.parquet. Usage: python l21_s4_verdicts.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
S4 = L21.OUT / "s4"; rng = np.random.default_rng(0); Q = lambda a: (float(np.quantile(a, 0.025)), float(np.quantile(a, 0.975)))
# H6
D6 = (pl.concat([pl.read_parquet(f) for f in sorted((S4 / "h6").glob("*.parquet"))]).filter(pl.col("filled"))
      .with_columns(((pl.col("mid1") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m1"), ((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10")))
A6 = D6.group_by("quoter", "day").agg(pl.len().alias("fills"), pl.col("adverse").mean(), pl.col("m1").mean(), pl.col("m10").mean()).sort("quoter", "day"); A6.write_parquet(S4 / "h6.parquet")
T = A6.filter(pl.col("quoter") == "instant"); t, o = T.filter(pl.col("day") == "2025-10-10"), T.filter(pl.col("day") != "2025-10-10")
p6a = float((T["adverse"] >= t["adverse"][0]).sum() / T.height); p6b = float((T["m10"] <= t["m10"][0]).sum() / T.height)
print("H6 10 Oct", t.rows(named=True)[0], "others: adverse max", o["adverse"].max(), "median", o["adverse"].median(), "m10 min", o["m10"].min(), "median", o["m10"].median(), "ranks p", p6a, p6b)
print(A6.filter(pl.col("day") == "2025-10-10"))
# H7
D7 = pl.concat([pl.read_parquet(f) for f in sorted((S4 / "h7").glob("*.parquet"))]); days = sorted(D7["day"].unique().to_list()); idx = rng.integers(0, len(days), (2000, len(days)))
G7 = D7.filter(pl.col("gap_bp").is_not_nan()).group_by("day", "cls").agg(pl.len().alias("n"), pl.col("gap_bp").sum().alias("s"))
LAB = ["< 0.01", "0.01-0.1", "0.1-1", "1-5", ">= 5"]; V = {c: np.array([next(iter(G7.filter((pl.col("day") == d) & (pl.col("cls") == c)).select("n", "s").rows()), (0, 0.0)) for d in days], dtype=float) for c in LAB}
f = lambda v: v[..., 1].sum(-1) / v[..., 0].sum(-1)
R7 = [dict(cls=c, orders=int(V[c][:, 0].sum()), gap=float(f(V[c])), lo=Q(f(V[c][idx]))[0], hi=Q(f(V[c][idx]))[1], median=float(D7.filter((pl.col("cls") == c) & pl.col("gap_bp").is_not_nan())["gap_bp"].median()),
           share_nonzero=float((D7.filter((pl.col("cls") == c) & pl.col("gap_bp").is_not_nan())["gap_bp"].abs() > 1e-6).mean()), unpriced=int(D7.filter((pl.col("cls") == c) & pl.col("gap_bp").is_nan()).height)) for c in LAB]
pl.DataFrame(R7).write_parquet(S4 / "h7.parquet"); print(pl.DataFrame(R7))
bs7 = f(V[">= 5"][idx]) - f(V["< 0.01"][idx]); d7 = float(f(V[">= 5"]) - f(V["< 0.01"])); p7 = float((bs7 <= 0).mean()); print("H7 diff", d7, Q(bs7), "p", p7)
# H9
D9 = pl.concat([pl.read_parquet(f) for f in sorted((S4 / "h9").glob("*.parquet"))]).with_columns(((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10"))
W = D9.filter(pl.col("rule") == "Q2").join(D9.filter(pl.col("rule") == "Q1").select("day", "side", "sent", pl.col("fill").alias("f1"), pl.col("m10").alias("m1q")), on=["day", "side", "sent"])
days9 = sorted(W["day"].unique().to_list()); idx9 = rng.integers(0, len(days9), (2000, len(days9)))
P = W.group_by("day").agg(pl.len().alias("n"), pl.col("fill").is_not_null().sum().alias("q2"), pl.col("f1").is_not_null().sum().alias("q1"),
                          (pl.col("fill").is_not_null() & pl.col("f1").is_null()).sum().alias("miss"), pl.col("m10").filter(pl.col("fill").is_not_null() & pl.col("f1").is_null()).sum().alias("miss_m"),
                          pl.col("m1q").filter(pl.col("f1").is_not_null()).sum().alias("q1_m"), (pl.col("fill") < pl.col("f1")).sum().alias("earlier")).sort("day")
v = P.select("n", "q2", "q1", "miss", "miss_m", "q1_m").to_numpy().astype(float); fr = lambda w: (w[..., 1].sum(-1) - w[..., 2].sum(-1)) / w[..., 0].sum(-1); bs = fr(v[idx9]); p9a = float((bs <= 0).mean())
tot = v.sum(0); mm = tot[4] / max(tot[3], 1); mq = tot[5] / tot[2]; w = v[idx9]; bm = w[..., 4].sum(-1) / np.maximum(w[..., 3].sum(-1), 1) - w[..., 5].sum(-1) / w[..., 2].sum(-1); p9b = float((bm < 0).mean())
pl.DataFrame([dict(orders=int(tot[0]), q2=tot[1] / tot[0], q1=tot[2] / tot[0], missed_fills=int(tot[3]), miss_m10=mm, q1_m10=mq, earlier=int(P["earlier"].sum()), p_fill=p9a, p_markout=p9b, diff_lo=Q(bs)[0], diff_hi=Q(bs)[1], m_lo=Q(bm)[0], m_hi=Q(bm)[1])]).write_parquet(S4 / "h9.parquet"); print(pl.read_parquet(S4 / "h9.parquet").rows(named=True)[0])
# verdicts
h = pl.read_parquet(S4 / "h1235.parquet"); pv = {r["test"]: r["p"] for r in h.iter_rows(named=True)}; h4 = pl.read_parquet(S4 / "h4_test.parquet")["p"][0]; h8 = pl.read_parquet(S4 / "h8_test.parquet").filter((pl.col("x") == "x >= 100%") & (pl.col("h") == "1s"))["p"][0]
tests = [("H1", pv["H1"]), ("H2", pv["H2"]), ("H4", h4), ("H5", pv["H5"]), ("H6a adverse", p6a), ("H6b loss", p6b), ("H7", p7), ("H8", h8), ("H9a fills", p9a), ("H9b markout", p9b)]
o = sorted(tests, key=lambda x: x[1]); m = len(o); k = max([i + 1 for i, (_, p) in enumerate(o) if p <= (i + 1) * 0.05 / m], default=0)
Vd = pl.DataFrame([dict(test=t, p=p, limit=(i + 1) * 0.05 / m, holds=i < k) for i, (t, p) in enumerate(o)]); Vd.write_parquet(S4 / "verdicts.parquet"); print(Vd)
