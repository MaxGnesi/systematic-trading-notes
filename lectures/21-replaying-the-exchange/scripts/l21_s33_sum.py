"""Lecture 21 §3.3: the small tables behind figure 21_12, from the orders of l21_s33_queue.py (L21_OUT/s33).
curve.parquet: share of orders filled within s seconds of joining, s = 0..120, by rule, with 95% bands from 2,000 resamples of days.
ahead.parquet: share filled within 120 s by the size ahead at joining (classes in BTC), by rule; median time to fill of the filled.
through.parquet: for the fills under Q2, the share that came with the first trade through our price (the Q1 fill) rather than at our price.
halfhours.parquet: per sampled half-hour, Q2 with a = 1: median size ahead at joining, median time to fill, share filled, share adverse.
Output: L21_OUT/s33_sum/. Usage: python l21_s33_sum.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
S33 = L21.OUT / "s33"; OUT = L21.OUT / "s33_sum"; OUT.mkdir(exist_ok=True); rng = np.random.default_rng(0)
D = pl.concat([pl.read_parquet(f) for f in sorted(S33.glob("*.parquet"))]).with_columns(((pl.col("fill") - pl.col("arrival")) / 1000).alias("wait"))
days = D["day"].unique().sort().to_list(); idx = rng.integers(0, len(days), (2000, len(days)))
SEC = np.arange(0, 121)
rows = []
for rule, G in D.group_by("rule"):
    n = G.group_by("day").len().sort("day")["len"].to_numpy()
    W = G.filter(pl.col("wait").is_not_null())
    cnt = np.zeros((len(days), len(SEC)))
    for i, d in enumerate(days):
        w = np.sort(W.filter(pl.col("day") == d)["wait"].to_numpy()); cnt[i] = np.searchsorted(w, SEC, side="right")
    share = cnt.sum(0) / n.sum(); bs = cnt[idx].sum(1) / n[idx].sum(1)[:, None]
    lo, hi = np.quantile(bs, [0.025, 0.975], axis=0)
    rows += [dict(rule=rule[0], sec=int(s), share=float(a), lo=float(b), hi=float(c)) for s, a, b, c in zip(SEC, share, lo, hi)]
pl.DataFrame(rows).sort("rule", "sec").write_parquet(OUT / "curve.parquet")
EDGES = [0.01, 0.1, 1, 5]; LAB = ["< 0.01", "0.01-0.1", "0.1-1", "1-5", "> 5"]
A = (D.filter(pl.col("ahead").is_not_nan()).with_columns(pl.col("ahead").cut(EDGES, labels=LAB, left_closed=True).cast(pl.String).alias("cls"))
     .group_by("rule", "cls").agg(pl.len().alias("n"), pl.col("fill").is_not_null().mean().alias("filled"), pl.col("wait").median().alias("median_wait")))
A.sort("rule", "cls").write_parquet(OUT / "ahead.parquet")
Q1 = D.filter(pl.col("rule") == "Q1").select("day", "side", "sent", pl.col("fill").alias("f1"))
X = D.filter(pl.col("rule").str.starts_with("Q2") & pl.col("fill").is_not_null()).join(Q1, on=["day", "side", "sent"])
X.group_by("rule").agg(pl.len().alias("fills"), (pl.col("fill") == pl.col("f1")).mean().alias("through")).sort("rule").write_parquet(OUT / "through.parquet")
H = (D.filter(pl.col("rule") == "Q2 a=1").with_columns(((pl.col("sent") - pl.col("day").str.to_datetime("%Y-%m-%d", time_unit="ms").dt.epoch("ms")) // 1_800_000).alias("hh"))
     .group_by("day", "hh").agg(pl.col("ahead").median().alias("ahead"), pl.col("wait").median().alias("wait"), pl.col("fill").is_not_null().mean().alias("filled"),
                                pl.col("adverse").mean().alias("adverse"), pl.len().alias("n")).sort("day", "hh"))
H.write_parquet(OUT / "halfhours.parquet")
J = D.filter(pl.col("rule") == "Q0")
print("orders", J.height, "days", len(days), "ahead at joining: median", J["ahead"].median(), "share ahead > 1 BTC", (J["ahead"] > 1).mean())
with pl.Config(tbl_rows=60, tbl_width_chars=200, float_precision=3):
    print(pl.read_parquet(OUT / "curve.parquet").filter(pl.col("sec").is_in([1, 5, 10, 30, 60, 120])).pivot("sec", index="rule", values="share"))
    print(A.pivot("cls", index="rule", values="filled")); print(A.filter(pl.col("rule") == "Q0").select("cls", "n"))
    print(pl.read_parquet(OUT / "through.parquet")); print(H.filter(pl.col("day") == "2025-10-10"))
    print("half-hours", H.height, "median ahead", H["ahead"].median(), "median wait", H["wait"].median(),
          "10 Oct 21:30 ranks by ahead (lowest = 1):", int((H["ahead"] <= H.filter((pl.col("day") == "2025-10-10") & (pl.col("hh") == 43))["ahead"][0]).sum()),
          "by wait:", int((H["wait"] <= H.filter((pl.col("day") == "2025-10-10") & (pl.col("hh") == 43))["wait"][0]).sum()))
