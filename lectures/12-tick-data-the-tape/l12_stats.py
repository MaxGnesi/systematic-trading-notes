"""Lecture 12: data-quality tables for any symbol and period (§5, §8.1), and the small archive files they need (funding, candles).

Each function returns a table (Polars DataFrame) from the derived layer written by tape.py. The code behind the lecture's
figures is in l12_figures.py."""
import io, json, zipfile
from datetime import datetime, timezone
from urllib.request import urlopen

import numpy as np
import polars as pl

import tape


# ---------------------------------------------------------------- loading
def _dir(symbol): return tape.ROOT / "interim" / "tape" / symbol


def load(symbol, months, name, columns=None):
    """One derived table for all months: days, hours, sizes, m1, rv_days, flag_counts, flag_examples."""
    parts = [pl.read_parquet(_dir(symbol) / ym / f"{name}.parquet", columns=columns) for ym in months]
    parts = [p for p in parts if p.height]
    return pl.concat(parts, how="diagonal_relaxed") if parts else pl.DataFrame()


def sequence_info(symbol, months):
    return [json.loads((_dir(symbol) / ym / "sequence.json").read_text()) for ym in months]


def _archive_monthly(symbol, months, kind, sub=""):
    """Small monthly files from the archive (funding, klines): downloaded once, checked against their checksum, kept as Parquet."""
    d = tape.ROOT / "raw" / "binance" / "um" / kind / symbol / sub; d.mkdir(parents=True, exist_ok=True); out = []
    for ym in months:
        name = f"{symbol}-{sub + '-' if sub else ''}{kind}-{ym}" if kind != "klines" else f"{symbol}-{sub}-{ym}"
        pq = d / f"{name}.parquet"
        if not pq.exists():
            url = f"https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{sub + '/' if sub else ''}{name}.zip"
            raw = urlopen(url).read()
            import hashlib
            if hashlib.sha256(raw).hexdigest() != urlopen(url + ".CHECKSUM").read().decode().split()[0]:
                raise ValueError(f"{name}: checksum mismatch")
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                txt = z.read(z.namelist()[0])
            header = not txt[:1].isdigit()
            pl.read_csv(io.BytesIO(txt), has_header=header, new_columns=None if header else KLINE_COLS).write_parquet(pq)
        out.append(pl.read_parquet(pq))
    return pl.concat(out, how="diagonal_relaxed")


KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def funding(symbol, months):
    f = _archive_monthly(symbol, months, "fundingRate")
    return f.select(pl.from_epoch(pl.col("calc_time") // 60_000 * 60_000, time_unit="ms").alias("ft"), pl.col("last_funding_rate").cast(pl.Float64).alias("rate")).sort("ft")


def klines(symbol, months):
    k = _archive_monthly(symbol, months, "klines", "1m")
    k = k.rename({c: KLINE_COLS[i] for i, c in enumerate(k.columns) if i < len(KLINE_COLS)})
    return k.with_columns(pl.from_epoch("open_time", time_unit="ms").alias("time")).drop("ignore", strict=False)


# ---------------------------------------------------------------- §5 data quality
def quality_report(symbol, start, end, holes, patches):
    D_ = _dir(symbol); ms_ = tape.months(start, end)
    days_ = pl.concat([pl.read_parquet(D_ / ym / "days.parquet") for ym in ms_])
    fl = pl.concat([pl.read_parquet(D_ / ym / "flag_counts.parquet") for ym in ms_])
    ex_ = pl.concat([pl.read_parquet(D_ / ym / "flag_examples.parquet") for ym in ms_ if pl.read_parquet(D_ / ym / "flag_examples.parquet").height])
    n = int(days_["trades"].sum()); f = lambda rule: int(fl.filter(pl.col("rule") == rule)["n"].sum())
    miss = int(holes.filter(pl.col("kind") == "missing")["n"].sum()); rep = int(holes.filter(pl.col("kind") == "repeated")["n"].sum())
    filled = int(patches.filter(pl.col("status") == "filled")["n"].sum()) if patches.height else 0
    unfilled = miss - filled; total = n + unfilled                                   # what Binance recorded: the trades we have, plus those missing everywhere
    bad_days = set()
    for h in (patches.filter(pl.col("status") != "filled").iter_rows(named=True) if patches.height else []):
        bad_days.update(tape.hole_days(h["from_ms"], h["to_ms"], 1))
    silent_s = float(ex_.filter(pl.col("rule") == "silence over 60 seconds")["value"].sum()) if ex_.height else 0.0
    unusual = f("spike and revert") + f("jump that persists")
    pct = lambda x, base: f"{100 * x / base:.4f}%"
    rows = [("Trades in the period, after patching", f"{n:,}", "100%"),
            ("Missing from the monthly files", f"{miss:,}", pct(miss, total)),
            ("  filled exactly from the daily files", f"{filled:,}", pct(filled, total)),
            ("  missing from the whole archive, recorded", f"{unfilled:,}", pct(unfilled, total)),
            ("Duplicated rows, kept once", f"{rep:,}", pct(rep, n)),
            ("Days complete", f"{days_.height - len(bad_days)} of {days_.height}", f"{100 * (days_.height - len(bad_days)) / days_.height:.1f}%"),
            ("Time with no trade for over a minute", f"{silent_s / 60:,.1f} minutes", f"{100 * silent_s / (days_.height * 86_400):.4f}% of the time"),
            ("Unusual prints, flagged and kept", f"{unusual:,}", pct(unusual, n)),
            ("Prices off the tick grid, kept", f"{int(days_['off_grid'].sum()):,}", pct(int(days_["off_grid"].sum()), n)),
            ("Quantities off the lot size", f"{int(days_['off_lot'].sum()):,}", pct(int(days_["off_lot"].sum()), n))]
    print(f"{symbol}, {start} to {end}: {100 * n / total:.4f}% of the trades Binance recorded are in the data; nothing was deleted.")
    return pl.DataFrame(rows, schema=["measure", "count", "share"], orient="row")


def quality_by_month(symbol, months, holes, patches):
    """Per month: trades, missing and filled shares, duplicates, time without trades, unusual prints, prices off the grid."""
    rows = []
    days = load(symbol, months, "days"); fl = load(symbol, months, "flag_counts"); ex = load(symbol, months, "flag_examples")
    for ym in months:
        d = days.filter(pl.col("day").dt.strftime("%Y-%m") == ym); n = int(d["trades"].sum())
        h = holes.filter(pl.col("month") == ym)
        miss = int(h.filter(pl.col("kind") == "missing")["n"].sum()); rep = int(h.filter(pl.col("kind") == "repeated")["n"].sum())
        p = patches.filter(pl.col("month") == ym) if patches.height else patches
        unfilled = int(p.filter(pl.col("status") != "filled")["n"].sum()) if p.height else 0
        f = fl.filter(pl.col("day").str.slice(0, 7) == ym)
        silence = float(ex.filter((pl.col("rule") == "silence over 60 seconds") & (pl.from_epoch("ms", time_unit="ms").dt.strftime("%Y-%m") == ym))["value"].sum()) if ex.height else 0.0
        rows.append(dict(month=ym, trades=n, missing_pct=100 * miss / (n + unfilled), unfilled_pct=100 * unfilled / (n + unfilled),
                         duplicated_pct=100 * rep / n, no_trade_minutes=round(silence / 60, 1),
                         unusual_prints=int(f.filter(pl.col("rule").is_in(["spike and revert", "jump that persists"]))["n"].sum()),
                         off_grid_pct=100 * int(d["off_grid"].sum()) / n, complete_pct=100 * n / (n + unfilled)))
    return pl.DataFrame(rows).with_columns(pl.col(pl.Float64).round(4))


def flag_register(symbol, months):
    """The flag register of §5.3: every rule, how often it fired, on how many days, as a share of trades."""
    fl = load(symbol, months, "flag_counts"); days = load(symbol, months, "days"); n = int(days["trades"].sum())
    t = fl.group_by("rule", "kind").agg(pl.col("n").sum().alias("count"), pl.col("day").n_unique().alias("days"))
    extra = pl.DataFrame([dict(rule="price off the tick grid", kind="event", count=int(days["off_grid"].sum()), days=int((days["off_grid"] > 0).sum())),
                          dict(rule="quantity off the lot step", kind="error", count=int(days["off_lot"].sum()), days=int((days["off_lot"] > 0).sum())),
                          dict(rule="very large trade (over $5 million)", kind="event", count=int(days["over_5m"].sum()), days=int((days["over_5m"] > 0).sum()))],
                         schema={"rule": pl.Utf8, "kind": pl.Utf8, "count": pl.Int64, "days": pl.Int64})
    t = pl.concat([t.with_columns(pl.col("count").cast(pl.Int64), pl.col("days").cast(pl.Int64)), extra])
    return t.with_columns((100 * pl.col("count") / n).round(5).alias("share_of_trades_pct")).sort("kind", "count", descending=[False, True])


def candles_vs_binance(symbol, months):
    """§8.1: candles rebuilt from the tape against Binance's one-minute candles, part by part."""
    K = klines(symbol, months).with_columns(pl.col("time").cast(pl.Datetime("ms")))
    M = load(symbol, months, "m1").with_columns(pl.col("time").cast(pl.Datetime("ms"))).sort("time").with_columns(pl.col("close").shift(1).alias("prev_close"))
    B = K.join(M, on="time", suffix="_tape")
    eq = lambda a, b: (pl.col(a) - pl.col(b)).abs() < 1e-9
    zero = K.filter(pl.col("count") == 0).join(M, on="time")
    t = pl.DataFrame([
        dict(part="minutes compared", value=f"{B.height:,}", note=""),
        dict(part="close identical", value=f"{100 * B.select(eq('close', 'close_tape').mean()).item():.2f}%", note=""),
        dict(part="high and low identical", value=f"{100 * B.select((eq('high', 'high_tape') & eq('low', 'low_tape')).mean()).item():.2f}%", note="the rest: rows straddling a minute's start"),
        dict(part="open identical", value=f"{100 * B.select(eq('open', 'open_tape').mean()).item():.2f}%",
             note=f"where not, Binance's open is the previous close in {100 * B.filter(~eq('open', 'open_tape')).select(eq('open', 'prev_close').mean()).item():.1f}% of cases"),
        dict(part="volume identical", value=f"{100 * B.select(((pl.col('volume') / pl.col('qty') - 1).abs() < 1e-9).mean()).item():.1f}%", note="the rest typically differ by one part in a million"),
        dict(part="Binance trades per aggregated trade", value=f"{B.select((pl.col('count') / pl.col('trades')).median()).item():.2f}", note="Binance counts single fills"),
        dict(part="minutes Binance shows without trades, the tape has trades", value=f"{zero.height:,}", note=f"{int(zero['trades'].sum()):,} trades on the tape"),
        dict(part="minutes Binance has, the tape does not", value=f"{K.join(M, on='time', how='anti').filter(pl.col('count') > 0).height:,}", note="trades missing from the archive's tape")])
    return t
