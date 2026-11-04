"""Lecture 21 §3.4: what the fills of §3.3 earn, from the orders of l21_s33_queue.py (L21_OUT/s33). Markout of a fill: the mid h seconds after it minus
the fill price, signed for our side, in bp, before the maker fee; h in {1, 10}.
rules.parquet: by fill rule: fills, share adverse, mean markout at each horizon, 95% bands from 2,000 resamples of days.
split.parquet: the queue rule at a = 1 and a = infinity: the same for adverse and non-adverse fills apart.
halfhours.parquet: the queue rule at a = 1, per sampled half-hour: fills, share adverse, mean 10-s markout.
Output: L21_OUT/s34/. Usage: python l21_s34_sum.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
OUT = L21.OUT / "s34"; OUT.mkdir(exist_ok=True); rng = np.random.default_rng(0)
F = (pl.concat([pl.read_parquet(f) for f in sorted((L21.OUT / "s33").glob("*.parquet"))]).filter(pl.col("fill").is_not_null())
     .with_columns(((pl.col("mid1") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m1"), ((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10")))
days = F["day"].unique().sort().to_list(); idx = rng.integers(0, len(days), (2000, len(days)))


def summary(G):
    """Fills, share adverse and mean markouts of a set of fills, with bands from resampling days."""
    d = G.group_by("day").agg(pl.len().alias("n"), pl.col("adverse").sum().alias("adv"), pl.col("m1").sum(), pl.col("m10").sum())
    g = {r[0]: r[1:] for r in d.select("day", "n", "adv", "m1", "m10").iter_rows()}; v = np.array([g.get(x, (0, 0, 0.0, 0.0)) for x in days], dtype=float)
    out = dict(fills=int(v[:, 0].sum()), adverse=v[:, 1].sum() / v[:, 0].sum())
    for j, k in ((2, "m1"), (3, "m10")):
        bs = v[idx, j].sum(1) / v[idx, 0].sum(1); out |= {k: v[:, j].sum() / v[:, 0].sum(), k + "_lo": np.quantile(bs, 0.025), k + "_hi": np.quantile(bs, 0.975)}
    return out


pl.DataFrame([dict(rule=r[0], **summary(G)) for r, G in F.group_by("rule")]).sort("rule").write_parquet(OUT / "rules.parquet")
S = [dict(rule=r, adverse_fill=bool(a), **summary(F.filter((pl.col("rule") == r) & (pl.col("adverse") == a)))) for r in ("Q2 a=1", "Q2 a=inf") for a in (True, False)]
pl.DataFrame(S).write_parquet(OUT / "split.parquet")
H = (F.filter(pl.col("rule") == "Q2 a=1").with_columns(((pl.col("sent") - pl.col("day").str.to_datetime("%Y-%m-%d", time_unit="ms").dt.epoch("ms")) // 1_800_000).alias("hh"))
     .group_by("day", "hh").agg(pl.len().alias("fills"), pl.col("adverse").mean(), pl.col("m10").mean()).sort("day", "hh"))
H.write_parquet(OUT / "halfhours.parquet")
with pl.Config(tbl_rows=40, tbl_cols=20, tbl_width_chars=220, float_precision=3):
    print(pl.read_parquet(OUT / "rules.parquet")); print(pl.read_parquet(OUT / "split.parquet"))
    print(H.select(pl.corr("adverse", "m10").alias("corr"), pl.col("m10").median(), pl.col("adverse").median()))
