"""Lecture 18 §5 / Lecture 20, first look: are cancellation bursts ("pulls") driven by the clock or by events? One day of Bybit BTCUSDT (L2, 200 levels,
100 ms), streamed from Parquet. For every update: among the best 20 levels of each side before it, how many lost size by more than the trades at that
price in the same interval (cancellations net of new orders, without trades explaining them). A pull: 5 or more such levels on one side in one update.
Then the pull rate (a) by second of the minute and minute of the hour (clock), (b) by the absolute move of the mid and the traded volume in the
previous second (events). Output: L18_OUT/pulls/DAY.parquet. Usage: python l18_pulls.py YYYY-MM-DD"""
import sys
from pathlib import Path
import numpy as np, polars as pl, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18

DAY = sys.argv[1]; ROOT = L18.PARQUET; HERE = L18.OUT / "pulls"; HERE.mkdir(exist_ok=True)
TOP, PULL = 20, 5
tr = pl.read_parquet(ROOT / "trades" / "BTCUSDT" / f"{DAY}.parquet", columns=["ts", "tick", "size"]).sort("ts")
t_ts, t_tick, t_size = tr["ts"].to_numpy(), tr["tick"].to_numpy(), tr["size"].to_numpy(); ti = 0
bids, asks = {}, {}; out = []; prev_ts = None
pf = pq.ParquetFile(ROOT / "orderbook" / "BTCUSDT" / f"{DAY}.parquet")
cur_u, msg = None, []


def apply(ts, rows):
    """One message: count unexplained decreases among the best TOP levels of each side, then apply the changes."""
    global ti, prev_ts
    traded = {}
    if prev_ts is not None:
        while ti < len(t_ts) and t_ts[ti] <= ts:
            if t_ts[ti] > prev_ts: traded[t_tick[ti]] = traded.get(t_tick[ti], 0.0) + t_size[ti]
            ti += 1
    snap = rows[0][0] == 1
    if snap: bids.clear(); asks.clear()
    nb = na = 0
    if not snap and bids and asks:
        topb = set(sorted(bids, reverse=True)[:TOP]); topa = set(sorted(asks)[:TOP])
        for _, s, p, q in rows:
            book, top = (bids, topb) if s == 1 else (asks, topa)
            if p in top and q < book[p] - traded.get(p, 0.0) - 1e-9:
                if s == 1: nb += 1
                else: na += 1
    for _, s, p, q in rows:
        book = bids if s == 1 else asks
        if q == 0: book.pop(p, None)
        else: book[p] = q
    mid = (max(bids) + min(asks)) / 20 if bids and asks else np.nan
    out.append((ts, nb, na, mid)); prev_ts = ts


for batch in pf.iter_batches(batch_size=2_000_000, columns=["ts", "u", "snap", "side", "tick", "size"]):
    ts, u, sn, sd, tk, sz = (batch.column(i).to_numpy() for i in range(6))
    for k in range(len(u)):
        if u[k] != cur_u:
            if msg: apply(msg_ts, msg)
            cur_u, msg_ts, msg = u[k], ts[k], []
        msg.append((sn[k], sd[k], tk[k], sz[k]))
if msg: apply(msg_ts, msg)
M = pl.DataFrame(out, schema=["ts", "nb", "na", "mid"], orient="row")
M = M.with_columns(((pl.col("nb") >= PULL) | (pl.col("na") >= PULL)).alias("pull"), ((pl.col("ts") // 1000) % 60).alias("sec"), ((pl.col("ts") // 60000) % 60).alias("minute"))
# events in the previous second: absolute mid move (bp) and traded volume (BTC)
M = M.sort("ts").with_columns(pl.col("mid").shift(10).alias("mid_1s"))
M = M.with_columns(((pl.col("mid") / pl.col("mid_1s") - 1).abs() * 1e4).alias("move_bp"))
vol = tr.with_columns((pl.col("ts") // 1000).alias("s")).group_by("s").agg(pl.col("size").sum().alias("vol"))
M = M.with_columns((pl.col("ts") // 1000 - 1).alias("s")).join(vol, on="s", how="left").with_columns(pl.col("vol").fill_null(0.0))
M.write_parquet(HERE / f"{DAY}.parquet")
rate = M["pull"].mean()
print(f"{DAY}: updates {len(M):,}, pulls {int(M['pull'].sum()):,} ({rate:.2%} of updates)")
S = M.group_by("sec").agg(pl.col("pull").mean().alias("rate")).sort("sec"); s0 = S.filter(pl.col("sec") == 0)["rate"][0]
print(f"clock: rate at second 0 of the minute {s0:.2%}, other seconds mean {S.filter(pl.col('sec') != 0)['rate'].mean():.2%}, max {S['rate'].max():.2%} at second {S.sort('rate')['sec'][-1]}")
Mi = M.group_by("minute").agg(pl.col("pull").mean().alias("rate")); print(f"clock: rate at minute 0 of the hour {Mi.filter(pl.col('minute') == 0)['rate'][0]:.2%}, others {Mi.filter(pl.col('minute') != 0)['rate'].mean():.2%}")
M = M.with_columns(pl.col("move_bp").cut([0.5, 2, 5], labels=["<0.5 bp", "0.5-2", "2-5", ">5 bp"]).alias("move_bin"),
                   pl.col("vol").cut([0.1, 1, 5], labels=["<0.1 BTC", "0.1-1", "1-5", ">5 BTC"]).alias("vol_bin"))
pl.Config.set_tbl_rows(20); pl.Config.set_float_precision(4)
print("events: pull rate by the mid's move in the previous second"); print(M.drop_nulls("move_bp").group_by("move_bin").agg(pl.col("pull").mean().alias("rate"), pl.len().alias("updates")).sort("move_bin"))
print("events: pull rate by traded volume in the previous second"); print(M.group_by("vol_bin").agg(pl.col("pull").mean().alias("rate"), pl.len().alias("updates")).sort("vol_bin"))
