"""Lecture 18 §5: what the book shows, from the viewer's per-second records of all 45 days (best bid and ask, depth within 5 bp, imbalance of the
best 5 levels, cost of 1 and 5 BTC market orders by walking the book). Seconds inside the feed gaps are left out. Output: l18_s5_summary.json with
(a) per day, (b) by hour of the day (UTC), (c) the evening of 10 October, minute by minute from 20:30 to 22:30, against the median calm day."""
import json, sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18
CACHE = L18.ROOT / "viewer_cache" / L18.SYM; HERE = L18.OUT
gaps = pl.read_csv(L18.gaps_path())
S = pl.concat([pl.read_parquet(f).with_columns(pl.lit(f.name[:10]).alias("day")) for f in sorted(CACHE.glob("*_seconds.parquet"))])
for g in gaps.iter_rows(named=True): S = S.filter(~pl.col("at").is_between(g["start_ms"], g["end_ms"] + 1000))
S = S.with_columns(((pl.col("ask") - pl.col("bid"))).alias("spread_ticks"), ((pl.col("at") // 3_600_000) % 24).alias("hour"),
                   (pl.col("depth_bid") + pl.col("depth_ask")).alias("depth"))
agg = [pl.len().alias("seconds"), (pl.col("spread_ticks") > 1).mean().alias("share_wider_than_1_tick"), pl.col("spread_ticks").quantile(0.99).alias("spread_p99_ticks"),
       pl.col("depth_bid").median(), pl.col("depth_ask").median(), pl.col("depth").quantile(0.05).alias("depth_p5"),
       pl.col("buy_1").median().alias("buy_1_bp"), pl.col("buy_5").median().alias("buy_5_bp"), pl.col("buy_5").quantile(0.99).alias("buy_5_p99_bp"),
       pl.col("sell_5").median().alias("sell_5_bp"), (pl.col("buy_5").is_null()).mean().alias("share_5btc_beyond_book"), pl.col("imbalance").std().alias("imbalance_sd")]
by_day = S.group_by("day").agg(agg).sort("day")
by_hour = S.filter(pl.col("day") != "2025-10-10").group_by("hour").agg(agg).sort("hour")
ev = S.filter(pl.col("day") == "2025-10-10").with_columns(((pl.col("at") % 86_400_000) // 60_000).alias("minute")).filter(pl.col("minute").is_between(20 * 60 + 30, 22 * 60 + 30))
ev = ev.group_by("minute").agg(pl.col("spread_ticks").mean(), pl.col("depth").median(), pl.col("buy_5").median(), pl.col("sell_5").median(),
                               (pl.col("buy_5").is_null() | pl.col("sell_5").is_null()).mean().alias("beyond_book")).sort("minute")
calm = S.filter(pl.col("day") != "2025-10-10").select(pl.col("depth").median().alias("depth"), pl.col("sell_5").median().alias("sell_5"), pl.col("buy_5").median().alias("buy_5"))
out = dict(by_day=by_day.to_dicts(), by_hour=by_hour.to_dicts(), evening_10_oct=ev.to_dicts(), calm=calm.to_dicts()[0],
           overall=S.filter(pl.col("day") != "2025-10-10").select(agg).to_dicts()[0])
(HERE / "l18_s5_summary.json").write_text(json.dumps(out, indent=1, default=float))
pl.Config.set_tbl_rows(50); pl.Config.set_tbl_width_chars(220); pl.Config.set_float_precision(3)
print("all days except 10 Oct:", {k: round(v, 3) if isinstance(v, float) else v for k, v in out["overall"].items()})
print(by_day.select("day", "share_wider_than_1_tick", "depth_bid", "depth_ask", "depth_p5", "buy_1_bp", "buy_5_bp", "buy_5_p99_bp", "share_5btc_beyond_book"))
print(by_hour.select("hour", "share_wider_than_1_tick", "depth_bid", "depth_ask", "buy_5_bp"))
print(ev.filter(pl.col("minute").is_between(20 * 60 + 45, 21 * 60 + 40)))
