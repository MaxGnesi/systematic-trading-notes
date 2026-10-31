"""Lecture 20: taker orders per day. Bybit: trades with the same ms and side summed into one order (size, number of trades, size-weighted price
in ticks, worst price), with the book state just before (bid + ask in ticks, from Lecture 19's book state, last update strictly before the order).
Binance: aggregate trades from the raw daily zip (transaction time, price, quantity, aggressor side), summed the same way.
Also the last traded price in each ms on each venue, for lead and lag.
Outputs: L20_OUT/orders/{bybit,binance}_DAY.parquet and {bybit,binance}_px_DAY.parquet. Usage: python l20_orders.py DAY [...]"""
import sys, time, zipfile
from pathlib import Path
import polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20

OUT = L20.ORD
BY = L20.TRADES; BN = L20.BN_RAW

for day in sys.argv[1:]:
    t0 = time.time()
    if not (OUT / f"bybit_{day}.parquet").exists():
        T = pl.read_parquet(BY / f"{day}.parquet", columns=["ts", "side", "tick", "size"])
        O = T.group_by("ts", "side").agg(pl.col("size").sum(), pl.len().alias("n"), ((pl.col("tick") * pl.col("size")).sum() / pl.col("size").sum()).alias("tick"),
                                          pl.when(pl.col("side").first() == 1).then(pl.col("tick").max()).otherwise(pl.col("tick").min()).alias("worst")).sort("ts", "side")
        S = pl.read_parquet(L20.STATE / f"{day}.parquet", columns=["ts", "bid", "ask", "q_bid", "q_ask"]).sort("ts")
        S = S.with_columns((pl.col("bid") + pl.col("ask")).alias("mid2"), ((pl.col("q_bid") - pl.col("q_ask")) / (pl.col("q_bid") + pl.col("q_ask"))).alias("I"),
                           (pl.col("ts") + 1).alias("ts_join")).select("ts_join", "mid2", "I")
        O = O.join_asof(S, left_on="ts", right_on="ts_join", strategy="backward").drop("ts_join")    # state with ts < order ts
        O.write_parquet(OUT / f"bybit_{day}.parquet")
        T.group_by("ts", maintain_order=True).agg((pl.col("tick").last() / 10).alias("px")).write_parquet(OUT / f"bybit_px_{day}.parquet")
    if not (OUT / f"binance_{day}.parquet").exists():
        with zipfile.ZipFile(BN / f"BTCUSDT-aggTrades-{day}.zip") as z:
            B = pl.read_csv(z.open(z.namelist()[0]).read(), columns=["price", "quantity", "transact_time", "is_buyer_maker"])
        B = B.select(pl.col("transact_time").alias("ts"), pl.when(pl.col("is_buyer_maker")).then(-1).otherwise(1).cast(pl.Int8).alias("side"),
                     pl.col("price"), pl.col("quantity").alias("size"))
        O = B.group_by("ts", "side").agg(pl.col("size").sum(), pl.len().alias("n"), ((pl.col("price") * pl.col("size")).sum() / pl.col("size").sum()).alias("price")).sort("ts", "side")
        O.write_parquet(OUT / f"binance_{day}.parquet")
        B.group_by("ts", maintain_order=True).agg(pl.col("price").last().alias("px")).write_parquet(OUT / f"binance_px_{day}.parquet")
    print(day, f"{time.time() - t0:.0f} s", flush=True)
