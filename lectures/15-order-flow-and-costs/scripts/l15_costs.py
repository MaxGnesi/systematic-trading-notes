"""Lecture 15 §5: what a market order costs, from Binance's best bid and ask (bookTicker, 16 May 2023 to 30 March 2024; every 4th day).
Each aggressive order (trades in the same millisecond on the same side, as in §3) is matched to the best bid and ask just before it. Per order:
quoted half-spread, effective half-spread (side x (average fill - mid) / mid), and its split at 1 s, 10 s and 60 s into impact (side x the move of the mid)
and realised spread (side x (average fill - later mid) / mid: what the resting side keeps). Results are summed per hour and size bucket into
data/interim/l15_costs/{day}.parquet; a 2% random sample of orders is kept for distributions. Zips are kept in data/raw/binance/bookTicker/BTCUSDT."""
import io, sys, time, urllib.request, zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

SYM = "BTCUSDT"; RAW = tape.ROOT / "raw" / "binance" / "bookTicker" / SYM; OUT = tape.ROOT / "interim" / "l15_costs"
URL = "https://data.binance.vision/data/futures/um/daily/bookTicker/BTCUSDT/BTCUSDT-bookTicker-{}.zip"
DAYS = [date(2023, 5, 16) + timedelta(days=4 * k) for k in range(80) if date(2023, 5, 16) + timedelta(days=4 * k) <= date(2024, 3, 30)]
BUCKETS = [0, 1e3, 1e4, 1e5, 1e6, np.inf]; BLAB = ["< $1k", "$1k-10k", "$10k-100k", "$100k-1m", "> $1m"]
HZ = {"1s": 1_000, "10s": 10_000, "60s": 60_000}


def book(d):
    f = RAW / f"{d}.zip"
    if not f.exists():
        for k in range(3):
            try: f.write_bytes(urllib.request.urlopen(URL.format(d), timeout=120).read()); break
            except Exception as e:
                if k == 2: raise
                time.sleep(5)
    z = zipfile.ZipFile(f)
    with z.open(z.namelist()[0]) as fh:
        b = pl.read_csv(fh, columns=["best_bid_price", "best_bid_qty", "best_ask_price", "best_ask_qty", "transaction_time"],
                        schema_overrides={"best_bid_price": pl.Float64, "best_bid_qty": pl.Float64, "best_ask_price": pl.Float64, "best_ask_qty": pl.Float64, "transaction_time": pl.Int64})
    return b.rename({"transaction_time": "t", "best_bid_price": "bid", "best_ask_price": "ask", "best_bid_qty": "bq", "best_ask_qty": "aq"}).sort("t")


def orders(d):
    a = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
    t = (pl.scan_parquet(tape.source(SYM, d.strftime("%Y-%m"))).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
         .select("transact_time", "price", "quantity", "is_buyer_maker").collect().sort("transact_time"))
    t = t.with_columns(pl.when(pl.col("is_buyer_maker")).then(-1).otherwise(1).cast(pl.Int8).alias("side"))
    new = (pl.col("transact_time") != pl.col("transact_time").shift(1)) | (pl.col("side") != pl.col("side").shift(1))
    t = t.with_columns(new.fill_null(True).cum_sum().alias("oid"))
    return (t.group_by("oid", maintain_order=True).agg(pl.col("transact_time").first().alias("t"), pl.col("side").first(),
                                                       (pl.col("price") * pl.col("quantity")).sum().alias("usd"), pl.col("quantity").sum().alias("qty"))
            .with_columns((pl.col("usd") / pl.col("qty")).alias("px")).drop("oid"))


def one_day(d):
    B = book(d); O = orders(d)
    B = B.with_columns(((pl.col("bid") + pl.col("ask")) / 2).alias("mid"))
    # the book just before the order (strictly earlier update), and the mid 1 s, 10 s and 60 s later (last update at or before)
    X = O.join_asof(B.select("t", "bid", "ask", "bq", "aq", "mid"), on="t", strategy="backward", allow_exact_matches=False, tolerance=1000)   # no stale book: an update within 1 s
    for lab, h in HZ.items():
        X = X.with_columns((pl.col("t") + h).alias("th")).join_asof(B.select(pl.col("t").alias("th"), pl.col("mid").alias(f"mid_{lab}")), on="th", strategy="backward", tolerance=1000).drop("th")
    X = X.drop_nulls(["mid", "mid_1s", "mid_10s", "mid_60s"]).with_columns(
        ((pl.col("ask") - pl.col("bid")) / 2 / pl.col("mid") * 1e4).alias("quoted"),
        (pl.col("side") * (pl.col("px") - pl.col("mid")) / pl.col("mid") * 1e4).alias("eff"),
        ((pl.col("t") // 3_600_000) * 3_600_000).alias("hour"),
        pl.col("usd").cut(BUCKETS[1:-1], labels=BLAB).cast(pl.Utf8).alias("bucket"),
        pl.when(pl.col("side") == 1).then(pl.col("aq") * pl.col("ask")).otherwise(pl.col("bq") * pl.col("bid")).alias("depth_usd"))
    for lab in HZ:
        X = X.with_columns((pl.col("side") * (pl.col(f"mid_{lab}") - pl.col("mid")) / pl.col("mid") * 1e4).alias(f"imp_{lab}"),
                           (pl.col("side") * (pl.col("px") - pl.col(f"mid_{lab}")) / pl.col("mid") * 1e4).alias(f"real_{lab}"))
    cols = ["quoted", "eff"] + [f"{k}_{lab}" for k in ("imp", "real") for lab in HZ]
    agg = X.group_by("hour", "bucket").agg(pl.len().alias("n"), pl.col("usd").sum(), pl.col("depth_usd").median().alias("depth_med"),
                                            (pl.col("quoted") > 0.05).mean().alias("wider_than_tick_share"),
                                            *[pl.col(c).sum().alias(f"s_{c}") for c in cols], *[(pl.col(c) * pl.col("usd")).sum().alias(f"w_{c}") for c in cols])
    # the quoted spread over time (not per order): share of time at one tick, time-weighted mean
    dt = B["t"].diff().shift(-1).fill_null(0).to_numpy(); q = ((B["ask"] - B["bid"]) / 2 / B["mid"] * 1e4).to_numpy(); tick1 = ((B["ask"] - B["bid"]) < 0.1 + 1e-6).to_numpy()
    gaps = dt > 1000
    spread = dict(day=str(d), covered_hours=float(dt[~gaps].sum() / 3.6e6), orders_matched=int(X.height), orders_total=int(O.height), time_mean_quoted=float((q * dt)[~gaps].sum() / dt[~gaps].sum()), time_share_one_tick=float((tick1 * dt)[~gaps].sum() / dt[~gaps].sum()), updates=B.height)
    smp = X.sample(fraction=0.02, seed=7).select("t", "side", "usd", "bucket", "quoted", "eff", *[f"{k}_{lab}" for k in ("imp", "real") for lab in HZ], "depth_usd")
    return agg, smp, spread


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    days = DAYS if len(sys.argv) < 2 else [date.fromisoformat(x) for x in sys.argv[1:]]
    for d in days:
        f = OUT / f"{d}.parquet"
        if f.exists(): continue
        tape.wait_for_memory(2.0)
        agg, smp, spread = one_day(d)
        agg.write_parquet(f); smp.write_parquet(OUT / f"{d}_sample.parquet"); pl.DataFrame([spread]).write_parquet(OUT / f"{d}_spread.parquet")
        print(d, agg["n"].sum(), "of", spread["orders_total"], "orders,", round(spread["covered_hours"], 1), "h covered,", f"one tick {spread['time_share_one_tick']:.3f}", f"{time.time() - t0:.0f}s", tape.peak_private_gb(), "GB", flush=True)
