"""Lecture 18 §5.5: the book in motion, over the 45 days. (a) Quote fading: large market orders (>= 1 BTC) against the last recorded book before them,
predicted vs actual cost, by size and by how fast the market moved in the second before; (b) refill after orders >= 2 BTC; (c) pulls: share of updates,
clock (second of the minute) vs events (mid's move in the previous second), per day. Calm = all days except 10 October. Output: l18_s55_summary.json."""
import json, sys
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
HERE = L18.OUT
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_width_chars(220); pl.Config.set_float_precision(3)
S = pl.concat([pl.read_parquet(f) for f in sorted((HERE / "sweeps").glob("*.parquet"))]).drop_nulls("predicted_bp")
S = S.with_columns(pl.col("btc").cut([2, 5, 10], labels=["1-2 BTC", "2-5", "5-10", ">10 BTC"]).alias("size_bin"),
                   pl.col("move_1s_bp").cut([0.5, 2, 5], labels=["<0.5 bp", "0.5-2", "2-5", ">5 bp"]).alias("move_bin"),
                   pl.when(pl.col("day") < "2025-10-10").then(pl.lit("before")).when(pl.col("day") == "2025-10-10").then(pl.lit("10 Oct")).otherwise(pl.lit("after")).alias("period"))
fade = [pl.len().alias("orders"), pl.col("predicted_bp").median().alias("predicted"), pl.col("actual_bp").median().alias("actual"),
        pl.col("fade_bp").median().alias("fade_med"), pl.col("fade_bp").mean().alias("fade_mean"), pl.col("fade_bp").quantile(0.9).alias("fade_p90"),
        (pl.col("fade_bp") > 0.05).mean().alias("worse"), (pl.col("fade_bp") < -0.05).mean().alias("better"),
        pl.col("refill_s").median().alias("refill_med"), (pl.col("refill_s") >= 60).mean().alias("refill_60")]
calm = S.filter(pl.col("day") != "2025-10-10")
out = dict(overall=calm.select(fade).to_dicts()[0], by_size=calm.group_by("size_bin").agg(fade).sort("size_bin").to_dicts(),
           by_move=calm.group_by("move_bin").agg(fade).sort("move_bin").to_dicts(), by_period=S.group_by("period").agg(fade).to_dicts(),
           by_day=S.group_by("day").agg(fade).sort("day").to_dicts())
for k in ("overall",): print(k, out[k])
for k in ("by_size", "by_move", "by_period"): print(k); print(pl.DataFrame(out[k]))
# pulls
P = []
for f in sorted((HERE / "pulls").glob("*.parquet")):
    M = pl.read_parquet(f, columns=["ts", "pull", "sec", "move_bp"]); d = f.stem[-10:]
    M = M.with_columns(pl.col("move_bp").cut([0.5, 2, 5], labels=["<0.5 bp", "0.5-2", "2-5", ">5 bp"]).alias("move_bin"))
    row = dict(day=d, updates=len(M), rate=M["pull"].mean(), sec0=M.filter(pl.col("sec") == 0)["pull"].mean(), other=M.filter(pl.col("sec") != 0)["pull"].mean())
    for r in M.drop_nulls("move_bp").group_by("move_bin").agg(pl.col("pull").mean(), pl.len()).iter_rows(): row[f"move {r[0]}"] = r[1]; row[f"n {r[0]}"] = r[2]
    sec = M.group_by("sec").agg(pl.col("pull").mean()).sort("sec"); row["by_sec"] = sec["pull"].to_list()
    P.append(row)
out["pulls"] = P
D = pl.DataFrame([{k: v for k, v in r.items() if k != "by_sec"} for r in P])
print(D.select("day", "rate", "sec0", "other", "move <0.5 bp", "move 0.5-2", "move 2-5", "move >5 bp"))
print("median over days:", D.select(pl.exclude("day").median()).to_dicts()[0])
(HERE / "l18_s55_summary.json").write_text(json.dumps(out, indent=1, default=str))
