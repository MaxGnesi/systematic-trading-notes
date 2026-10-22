"""Lecture 13: bars on six clocks from the tape of Lecture 12, day by day, with thresholds from the past 28 days only.

time      30-minute bars (the benchmark: 48 a day)
tick      a fixed number of trades          threshold = median trades per day over the past 28 days / N
volume    a fixed number of coins            threshold = median coins per day / N
dollar    a fixed number of dollars          threshold = median dollars per day / N
range     high - low reaches a distance      threshold = K_RANGE x typical daily volatility / sqrt(N), in log price
cusum     the cumulative move since the last event exceeds h in either direction (Page, 1954), both sums reset at an event
The two price clocks follow one price per second, the VWAP of that second's trades, not every fill: in a burst, one order can fill at
over a thousand prices within a millisecond (21 September 2022, 18:00:02), and a clock on every fill would count each sweep as many moves.
N = 48 bars a day on average. The last, unfinished bar of each day is carried into the next, so bars do not break at midnight."""
import json, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np, polars as pl
from numba import njit
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

N = 48
K_RANGE, K_CUSUM = 1.431, 1.442                                      # set by calibrate() on the burn-in, October to December 2021: as many bars as the dollar clock there
BURN_IN = ("2021-10", "2021-12")
TYPES = ("time", "tick", "volume", "dollar", "range", "cusum")


def bars_dir(symbol, kind): return tape.ROOT / "interim" / "bars" / symbol / kind
def carry_file(symbol, kind): return tape.ROOT / "interim" / "bars" / symbol / "_carry" / f"{kind}.parquet"


def thresholds(symbol):
    """Per day: each clock's threshold from the previous 28 days (at least 7), so no bar knows the future."""
    D = tape.ROOT / "interim" / "tape" / symbol
    days = pl.concat([pl.read_parquet(f, columns=["day", "trades", "usd"]) for f in sorted(D.glob("*/days.parquet"))]).sort("day")
    qty = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "qty").group_by(pl.col("time").dt.date().alias("day")).agg(pl.col("qty").sum()).collect()
    rv = pl.concat([pl.read_parquet(f, columns=["day", "rv_300"]) for f in sorted(D.glob("*/rv_days.parquet"))])
    d = days.join(qty, on="day").join(rv, on="day").sort("day")
    past = lambda c: pl.col(c).shift(1).rolling_median(28, min_samples=7)
    return d.with_columns((past("trades") / N).alias("tick"), (past("qty") / N).alias("volume"), (past("usd") / N).alias("dollar"),
                          (K_RANGE * past("rv_300").sqrt() / np.sqrt(N)).alias("range"), (K_CUSUM * past("rv_300").sqrt() / np.sqrt(N)).alias("cusum")).drop_nulls("tick")


@njit(cache=True)
def _range_ends(lp, thr):
    """Indices of the trades that close a range bar: high - low of the bar, in log price, reaches thr."""
    out = np.empty(len(lp), np.int64); k = 0; hi = lp[0]; lo = lp[0]
    for i in range(1, len(lp)):
        if lp[i] > hi: hi = lp[i]
        if lp[i] < lo: lo = lp[i]
        if hi - lo >= thr:
            out[k] = i; k += 1
            if i + 1 < len(lp): hi = lp[i + 1]; lo = lp[i + 1]
    return out[:k]


@njit(cache=True)
def _cusum_ends(lp, h):
    """Indices of the trades at which the symmetric CUSUM of log-price changes passes +h or -h; both sums then restart."""
    out = np.empty(len(lp), np.int64); k = 0; sp = 0.0; sn = 0.0
    for i in range(1, len(lp)):
        r = lp[i] - lp[i - 1]
        sp = max(0.0, sp + r); sn = min(0.0, sn + r)
        if sp > h or sn < -h:
            out[k] = i; k += 1; sp = 0.0; sn = 0.0
    return out[:k]


def _aggregate(df, bar_id):
    """One row per bar from the trades and their bar numbers."""
    return (df.with_columns(pl.Series("bar", bar_id)).group_by("bar", maintain_order=True)
              .agg(pl.col("transact_time").first().alias("start_ms"), pl.col("transact_time").last().alias("end_ms"),
                   pl.col("price").first().alias("open"), pl.col("price").max().alias("high"), pl.col("price").min().alias("low"), pl.col("price").last().alias("close"),
                   pl.col("quantity").sum().alias("qty"), pl.col("usd").sum().alias("usd"), pl.col("signed_usd").sum().alias("signed_usd"), pl.len().alias("trades")).drop("bar"))


def build(symbol, start, end, kinds=TYPES, resume=False):
    """Bars from start to end (months); with resume, each clock continues the unfinished bar left on disk by the previous month."""
    th = thresholds(symbol)
    carry = {k: (pl.read_parquet(carry_file(symbol, k)) if resume and carry_file(symbol, k).exists() else None) for k in kinds if k != "time"}   # the trades of each clock's unfinished bar
    out = {k: [] for k in kinds}; t0 = time.time(); month = None
    for row in th.filter(pl.col("day").dt.strftime("%Y-%m").is_between(pl.lit(start), pl.lit(end))).iter_rows(named=True):
        d0 = row["day"]; ym = d0.strftime("%Y-%m")
        if month and ym != month:                                       # write the finished month
            for k in kinds:
                if out[k]:
                    bars_dir(symbol, k).mkdir(parents=True, exist_ok=True); pl.concat(out[k]).write_parquet(bars_dir(symbol, k) / f"{month}.parquet"); out[k] = []
            print(month, f"{time.time() - t0:.0f}s", tape.peak_private_gb(), "GB", flush=True)
        month = ym
        tape.wait_for_memory(2.5)
        a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
        t = (pl.scan_parquet(tape.source(symbol, ym)).filter(pl.col("transact_time").is_between(a, a + 86_400_000, closed="left"))
               .select("transact_time", "price", "quantity", "is_buyer_maker").collect()
               .with_columns((pl.col("price") * pl.col("quantity")).alias("usd")))
        t = t.with_columns(pl.when(pl.col("is_buyer_maker")).then(-pl.col("usd")).otherwise(pl.col("usd")).alias("signed_usd")).drop("is_buyer_maker")
        if t.height == 0: continue
        if "time" in kinds: out["time"].append(_aggregate(t, (t["transact_time"] // 1_800_000).to_numpy()))
        for k, x in [(k, x) for k, x in (("tick", None), ("volume", "quantity"), ("dollar", "usd"), ("range", None), ("cusum", None)) if k in kinds]:
            df = pl.concat([carry[k], t]) if carry[k] is not None else t
            if k in ("tick", "volume", "dollar"):
                v = np.ones(df.height) if x is None else df[x].to_numpy()
                c = np.cumsum(v) - v                                       # the counter before each trade: the trade that crosses closes its bar
                bar = np.floor(c / row[k]).astype(np.int64)
                done = bar < bar[-1]
            else:
                sec = (df["transact_time"] // 1000).to_numpy()              # the clock's price: one per second, that second's VWAP
                first = np.r_[True, sec[1:] != sec[:-1]]; sec_idx = np.cumsum(first) - 1
                usd, qty = df["usd"].to_numpy(), df["quantity"].to_numpy()
                vwap = np.bincount(sec_idx, usd) / np.bincount(sec_idx, qty)
                lp = np.log(vwap)
                ends = _range_ends(lp, row[k]) if k == "range" else _cusum_ends(lp, row[k])   # indices of closing seconds
                bar_s = np.zeros(len(lp), np.int64)                        # a new bar starts with the second after each closing second
                if len(ends): np.add.at(bar_s, ends[ends + 1 < len(lp)] + 1, 1); bar_s = np.cumsum(bar_s)
                bar = bar_s[sec_idx]
                done = sec_idx <= (ends[-1] if len(ends) else -1)
            if done.any():
                out[k].append(_aggregate(df.filter(pl.Series(done)), bar[done]))
            carry[k] = df.filter(pl.Series(~done))
    for k in kinds:
        if out[k]:
            bars_dir(symbol, k).mkdir(parents=True, exist_ok=True); pl.concat(out[k]).write_parquet(bars_dir(symbol, k) / f"{month}.parquet")
    for k, c in carry.items():                                          # the unfinished bars, for the next month
        if c is not None: carry_file(symbol, k).parent.mkdir(parents=True, exist_ok=True); c.write_parquet(carry_file(symbol, k))
    print(month, f"{time.time() - t0:.0f}s", tape.peak_private_gb(), "GB", flush=True)


def build_all(symbol, kinds=TYPES, rebuild=False):
    """Every month in its own process, so that memory is freed between months; the unfinished bars pass through carry files.
    Months whose bars exist for every clock are skipped, unless rebuild=True; a run therefore continues where the last one stopped."""
    import subprocess
    months = sorted({d.strftime("%Y-%m") for d in thresholds(symbol)["day"].to_list()})
    for i, ym in enumerate(months):
        if not rebuild and all((bars_dir(symbol, k) / f"{ym}.parquet").exists() for k in kinds):
            continue                                                    # built already; new months continue from the carry files of the last one
        cmd = [sys.executable, "-I", str(Path(__file__).resolve()), symbol, ym, ym, ",".join(kinds)] + (["--resume"] if i else [])
        subprocess.run(cmd, check=True)


def calibrate(symbol):
    """K_RANGE and K_CUSUM from the burn-in: price clocks at K = 1, then K = sqrt(their bars / dollar bars), since bars per day go as 1 / K^2.
    Built in a separate folder, so the bars in use are not touched."""
    global K_RANGE, K_CUSUM, bars_dir
    keep = bars_dir; tmp = tape.ROOT / "interim" / "bars_calibration" / symbol
    bars_dir = lambda s, k: tmp / k; K_RANGE = K_CUSUM = 1.0
    build(symbol, *BURN_IN, ("dollar", "range", "cusum"))
    n = {k: sum(pl.read_parquet(f).height for f in (tmp / k).glob("*.parquet")) for k in ("dollar", "range", "cusum")}
    bars_dir = keep
    print({k: round(float(np.sqrt(n[k] / n["dollar"])), 3) for k in ("range", "cusum")}, n)


if __name__ == "__main__":
    if sys.argv[1] == "calibrate":
        calibrate(sys.argv[2])
    elif sys.argv[1] == "all":
        build_all(sys.argv[2], tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] != "--rebuild" else TYPES, rebuild="--rebuild" in sys.argv)
    else:
        build(sys.argv[1], sys.argv[2], sys.argv[3], tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 and sys.argv[4] != "--resume" else TYPES, resume="--resume" in sys.argv)
