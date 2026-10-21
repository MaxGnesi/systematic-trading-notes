"""The tape pipeline (Lecture 12): Binance USD-M futures aggTrades, from the public archive to daily summaries.

Stages, each reading only the stage before it, each run one month (or one day) at a time with bounded memory:
  1. get          monthly zip -> checksum -> Parquet (raw layer, never changed) -> checks -> log
  2. find_holes   missing trade IDs and duplicated rows, from the IDs alone
  3. patch        fill missing days from Binance's daily files; check that each patch fills its hole exactly
  4. clean        for months with holes or duplicates only: raw + patches - duplicates, rebuilt day by day
  5. aggregate    order-free statistics with Polars' streaming engine (counts, volumes, histograms, simple flags)
  6. sequence     order-dependent statistics day by day, carrying the edges across midnight
                  (1-second and 1-minute bars, realised variance, durations, autocorrelations, rolling flags)
Every stage takes the market (symbol) and the month as parameters, so the same code serves any symbol.
run_pipeline() runs all stages for a period, each stage and month in a fresh process, and returns a log of time and peak memory.

Data are written under the folder in the environment variable TAPE_ROOT, or else under data/ at the top of the repository
(ignored by git: data are never committed)."""
import hashlib, json, os, shutil, subprocess, sys, time, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen, urlretrieve

os.environ.setdefault("POLARS_MAX_THREADS", "4")
import numpy as np
import polars as pl
import psutil
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as papq

ROOT = Path(os.environ.get("TAPE_ROOT", Path(__file__).resolve().parents[2] / "data"))
ARCHIVE = "https://data.binance.vision/data/futures/um/{freq}/aggTrades/{symbol}/{name}.zip"
COLS = ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]
TYPES = {"agg_trade_id": pa.int64(), "price": pa.float64(), "quantity": pa.float64(), "first_trade_id": pa.int64(),
         "last_trade_id": pa.int64(), "transact_time": pa.int64(), "is_buyer_maker": pa.bool_()}
SCHEMA = pa.schema([(c, TYPES[c]) for c in COLS])
TICK_CHANGES = {"BTCUSDT": (datetime(2022, 2, 16, tzinfo=timezone.utc), 0.01, 0.10)}   # before, after; 15 Feb 2022 is checked on the old grid
SIG_DT = [1, 2, 5, 10, 30, 60, 120, 300, 600, 900, 1800, 3600]
SIGN_LAGS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]               # lags for the autocorrelation of trade signs
SIZE_BINS = np.arange(0, 9.001, 0.05)
DUR_BINS = np.arange(0, 7.001, 0.1)
MIN_FREE_GB = 2.5
JUMP_BP = 50                                                   # unusual print: at least 0.5% from its neighbours


# ---------------------------------------------------------------- folders and small helpers
def raw_dir(symbol): return ROOT / "raw" / "binance" / "um" / "aggTrades" / symbol
def clean_dir(symbol): return ROOT / "interim" / "tape" / symbol / "clean"
def out_dir(symbol, ym): return ROOT / "interim" / "tape" / symbol / ym


def wait_for_memory(gb=MIN_FREE_GB):
    """Wait until gb of memory are free; return the seconds waited."""
    t0 = time.time()
    while psutil.virtual_memory().available / 1e9 < gb:
        time.sleep(15)
    return round(time.time() - t0, 1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def peak_private_gb():
    m = psutil.Process().memory_info()
    return round(getattr(m, "peak_pagefile", m.rss) / 1e9, 2)


def months(start, end):
    y, m = map(int, start.split("-")); out = []
    while f"{y}-{m:02d}" <= end:
        out.append(f"{y}-{m:02d}"); m += 1
        if m == 13: y, m = y + 1, 1
    return out


def tick(symbol, day):
    """The tick in force on a day: from TICK_CHANGES where the history is known, otherwise inferred from the month's prices."""
    change = TICK_CHANGES.get(symbol)
    if change is None: return infer_tick(symbol, f"{day.year}-{day.month:02d}")
    return change[1] if day < change[0] else change[2]


_TICKS = {}
def infer_tick(symbol, ym):
    """The smallest step between distinct prices in the month's first million trades, rounded to a power of ten."""
    if (symbol, ym) not in _TICKS:
        px = np.unique(np.round(papq.ParquetFile(source(symbol, ym)).read_row_group(0, columns=["price"]).column(0).to_numpy(), 8))
        step = np.diff(px).min() if len(px) > 1 else 0.01
        _TICKS[(symbol, ym)] = float(10 ** np.round(np.log10(step)))
    return _TICKS[(symbol, ym)]


# ---------------------------------------------------------------- 1. get
def _convert(zip_path, parquet_path, tmp_dir):
    """CSV inside the zip -> Parquet, 32 MB at a time; returns the number of rows."""
    with zipfile.ZipFile(zip_path) as z:
        member = z.namelist()[0]; csv = tmp_dir / member
        with z.open(member) as src, open(csv, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 22)
    with open(csv, "rb") as f:
        first = f.readline().decode()
    header = first.startswith("agg_trade_id")                   # older files have no header row
    names = [c.strip() for c in first.strip().split(",")] if header else COLS
    reader = pacsv.open_csv(csv, read_options=pacsv.ReadOptions(block_size=32 << 20, use_threads=False, column_names=names, skip_rows=1 if header else 0),
                            convert_options=pacsv.ConvertOptions(column_types=TYPES, include_columns=COLS))
    n = 0
    with papq.ParquetWriter(parquet_path, SCHEMA, compression="zstd") as w:
        for batch in reader:
            t = pa.Table.from_batches([batch]).select(COLS).cast(SCHEMA)
            w.write_table(t, row_group_size=1_000_000); n += t.num_rows
            del t, batch; pa.default_memory_pool().release_unused()
    reader.close(); del reader
    csv.unlink()
    return n, header


def _check(parquet_path):
    """Row count, ID continuity and time order, one row group at a time (two columns only)."""
    f = papq.ParquetFile(parquet_path); rows = gaps = dup = back = 0; prev = None; first = None
    for g in range(f.num_row_groups):
        t = f.read_row_group(g, columns=["agg_trade_id", "transact_time"])
        ids, ts = t.column(0).to_numpy(), t.column(1).to_numpy()
        if prev is not None:
            ids = np.concatenate([[prev[0]], ids]); ts = np.concatenate([[prev[1]], ts])
        else:
            first = (int(ids[0]), int(ts[0]))
        d = np.diff(ids); gaps += int((d > 1).sum()); dup += int((d < 1).sum()); back += int((np.diff(ts) < 0).sum())
        rows += len(ids) - (1 if prev is not None else 0); prev = (int(ids[-1]), int(ts[-1]))
    return dict(rows=rows, first_id=first[0], last_id=prev[0], first_time=first[1], last_time=prev[1], id_jumps=gaps, id_repeats=dup, time_backwards=back)


def get(symbol, period, freq="monthly", log_name="manifest.jsonl"):
    """Stage 1: download one month (or one day, freq='daily'), verify, convert, check, log, delete the zip."""
    d = raw_dir(symbol); zdir, tmp = d / "zip", d / "tmp"
    pdir = d / "parquet" if freq == "monthly" else d / "parquet" / "patch"
    for x in (zdir, tmp, pdir): x.mkdir(parents=True, exist_ok=True)
    name = f"{symbol}-aggTrades-{period}"; pq = pdir / f"{name}.parquet"
    if pq.exists(): return None
    waited = wait_for_memory(); t0 = time.time()
    url = ARCHIVE.format(freq=freq, symbol=symbol, name=name); zp = zdir / f"{name}.zip"
    expected = urlopen(url + ".CHECKSUM").read().decode().split()[0]
    if not (zp.exists() and sha256(zp) == expected):
        urlretrieve(url, zp)
        if sha256(zp) != expected:
            raise ValueError(f"{name}: checksum mismatch, zip kept for inspection")
    n, header = _convert(zp, pq, tmp)
    chk = _check(pq)
    if chk["rows"] != n:
        pq.unlink(); raise ValueError(f"{name}: Parquet rows {chk['rows']} != CSV rows {n}")
    info = dict(file=name, rows_csv=n, header=header, **chk, zip_mb=round(zp.stat().st_size / 1e6, 1), parquet_mb=round(pq.stat().st_size / 1e6, 1),
                seconds=round(time.time() - t0, 1), waited_seconds=waited, sha256=expected, peak_private_gb=peak_private_gb())
    zp.unlink()
    with open(d / log_name, "a") as f:
        f.write(json.dumps(info) + "\n")
    return info


# ---------------------------------------------------------------- 2. find holes
def find_holes(symbol, start, end):
    """Stage 2: every jump (missing IDs) and every repeat (duplicated IDs) in the raw monthly files, in order, across file boundaries."""
    rows, prev = [], None
    for ym in months(start, end):
        f = papq.ParquetFile(raw_dir(symbol) / "parquet" / f"{symbol}-aggTrades-{ym}.parquet")
        for g in range(f.num_row_groups):
            t = f.read_row_group(g, columns=["agg_trade_id", "transact_time"])
            ids, ts = t.column(0).to_numpy(), t.column(1).to_numpy()
            if prev is not None:
                ids = np.concatenate([[prev[0]], ids]); ts = np.concatenate([[prev[1]], ts])
            d = np.diff(ids)
            for i in np.where(d > 1)[0]:
                rows.append(dict(kind="missing", month=ym, from_id=int(ids[i]), to_id=int(ids[i + 1]), n=int(d[i] - 1), from_ms=int(ts[i]), to_ms=int(ts[i + 1])))
            rep = np.where(d < 1)[0]
            if len(rep):
                days = pd_days(ts[rep + 1])
                for day, cnt in zip(*np.unique(days, return_counts=True)):
                    rows.append(dict(kind="repeated", month=ym, from_id=-1, to_id=-1, n=int(cnt), from_ms=int(day), to_ms=int(day) + 86_400_000))
            prev = (int(ids[-1]), int(ts[-1]))
    holes = pl.DataFrame(rows, schema={"kind": pl.Utf8, "month": pl.Utf8, "from_id": pl.Int64, "to_id": pl.Int64, "n": pl.Int64, "from_ms": pl.Int64, "to_ms": pl.Int64})
    # repeated rows are reported per day; merge rows of the same day that came from different row groups
    holes = pl.concat([holes.filter(pl.col("kind") == "missing"),
                       holes.filter(pl.col("kind") == "repeated").group_by(["kind", "month", "from_id", "to_id", "from_ms", "to_ms"]).agg(pl.col("n").sum()).select(holes.columns)]).sort("from_ms")
    return holes


def pd_days(ms):
    return (np.asarray(ms) // 86_400_000) * 86_400_000


def hole_days(from_ms, to_ms, min_overlap_ms=60_000):
    """The days a hole really covers: those overlapping the open interval (last trade before, first trade after) by at least a minute."""
    day = from_ms // 86_400_000 * 86_400_000; out = []
    while day < to_ms:
        overlap = min(to_ms, day + 86_400_000) - max(from_ms, day)
        if overlap >= min_overlap_ms:
            out.append(datetime.fromtimestamp(day / 1000, timezone.utc).date())
        day += 86_400_000
    return out


# ---------------------------------------------------------------- 3. patch
def patch(symbol, holes):
    """Stage 3: for each missing range, fetch the daily files of the days it spans; record whether they fill it exactly."""
    out = []
    for h in holes.filter(pl.col("kind") == "missing").iter_rows(named=True):
        days = hole_days(h["from_ms"], h["to_ms"])
        found = 0
        for day in days:
            get(symbol, day.isoformat(), freq="daily", log_name="manifest_patch.jsonl")
            p = raw_dir(symbol) / "parquet" / "patch" / f"{symbol}-aggTrades-{day.isoformat()}.parquet"
            found += pl.scan_parquet(p).filter(pl.col("agg_trade_id").is_between(h["from_id"] + 1, h["to_id"] - 1)).select(pl.len()).collect().item()
        out.append(dict(**h, patched=found, status="filled" if found == h["n"] else ("not in the archive" if found == 0 else "partly filled")))
    return pl.DataFrame(out)


# ---------------------------------------------------------------- 4. clean
def clean(symbol, ym, holes):
    """Stage 4: for a month with holes or repeats, write raw + patches - duplicates, one day at a time. Other months need nothing."""
    if holes.filter(pl.col("month") == ym).height == 0: return None
    cdir = clean_dir(symbol); cdir.mkdir(parents=True, exist_ok=True)
    target = cdir / f"{symbol}-aggTrades-{ym}.parquet"
    if target.exists(): return target
    files = [raw_dir(symbol) / "parquet" / f"{symbol}-aggTrades-{ym}.parquet"] + sorted((raw_dir(symbol) / "parquet" / "patch").glob(f"{symbol}-aggTrades-{ym}-*.parquet"))
    lf = pl.scan_parquet(files); y, m = map(int, ym.split("-")); day = datetime(y, m, 1, tzinfo=timezone.utc)
    with papq.ParquetWriter(target, SCHEMA, compression="zstd") as w:
        while day.month == m:
            a, b = int(day.timestamp() * 1000), int((day + timedelta(days=1)).timestamp() * 1000)
            df = lf.filter(pl.col("transact_time").is_between(a, b, closed="left")).collect().unique("agg_trade_id").sort("agg_trade_id")
            if df.height: w.write_table(df.to_arrow().cast(SCHEMA), row_group_size=1_000_000)
            day += timedelta(days=1)
    return target


def source(symbol, ym):
    """The file every later stage reads: the clean month if one exists, otherwise the raw month."""
    c = clean_dir(symbol) / f"{symbol}-aggTrades-{ym}.parquet"
    return c if c.exists() else raw_dir(symbol) / "parquet" / f"{symbol}-aggTrades-{ym}.parquet"


# ---------------------------------------------------------------- 5. aggregate (Polars streaming: order-free statistics)
def aggregate(symbol, ym):
    out = out_dir(symbol, ym); out.mkdir(parents=True, exist_ok=True)
    waited = wait_for_memory()
    lf = pl.scan_parquet(source(symbol, ym)).with_columns(
        pl.from_epoch("transact_time", time_unit="ms").alias("time"), (pl.col("price") * pl.col("quantity")).alias("usd"))
    change = TICK_CHANGES.get(symbol)
    if change:                                                    # the tick in force at each trade, from its timestamp
        grid = pl.when(pl.col("transact_time") < int(change[0].timestamp() * 1000)).then(change[1]).otherwise(change[2])
    else:
        grid = pl.lit(infer_tick(symbol, ym))
    lf = lf.with_columns(grid.alias("tick"))
    lf = lf.with_columns(
        ((pl.col("price") / pl.col("tick")).round(6) - (pl.col("price") / pl.col("tick")).round(0)).abs().gt(1e-6).alias("off_grid"),
        ((pl.col("quantity") * 1000).round(6) - (pl.col("quantity") * 1000).round(0)).abs().gt(1e-6).alias("off_lot"),
        pl.col("usd").log10().clip(0, 8.999).truediv(0.05).floor().cast(pl.Int32).alias("size_bin"))
    days = (lf.group_by(pl.col("time").dt.date().alias("day")).agg(
        pl.len().alias("trades"), pl.col("usd").sum().alias("usd"), pl.col("usd").filter(~pl.col("is_buyer_maker")).sum().alias("buy_usd"),
        (pl.col("last_trade_id") - pl.col("first_trade_id") + 1).sum().alias("fills"), pl.col("usd").max().alias("max_usd"),
        pl.col("off_grid").sum().alias("off_grid"), pl.col("off_lot").sum().alias("off_lot"), (pl.col("usd") > 5e6).sum().alias("over_5m"))
        .sort("day").collect(engine="streaming"))
    hours = (lf.group_by(pl.col("time").dt.truncate("1h").alias("hour")).agg(
        pl.len().alias("trades"), pl.col("usd").sum().alias("usd"), pl.col("usd").filter(~pl.col("is_buyer_maker")).sum().alias("buy_usd"))
        .sort("hour").collect(engine="streaming"))
    sizes = lf.group_by("size_bin").agg(pl.len().alias("n"), pl.col("usd").sum().alias("usd")).sort("size_bin").collect(engine="streaming")
    q = lf.select([pl.col("usd").quantile(x, "nearest").alias(f"q{int(1000 * x)}") for x in (0.5, 0.9, 0.99, 0.999)]).collect(engine="streaming")
    days.write_parquet(out / "days.parquet"); hours.write_parquet(out / "hours.parquet"); sizes.write_parquet(out / "sizes.parquet"); q.write_parquet(out / "quantiles.parquet")
    return dict(month=ym, days=days.height, quantiles=q.row(0, named=True), waited_seconds=waited, peak_private_gb=peak_private_gb())


# ---------------------------------------------------------------- 6. sequence (day by day: order-dependent statistics)
class LagCorr:
    """Running sums for the correlation of consecutive values, so that days can be added one at a time."""
    def __init__(self): self.n = 0; self.s = np.zeros(5)
    def add(self, v):
        v = np.asarray(v, float)
        if len(v) < 2: return
        x, y = v[:-1], v[1:]; self.n += len(x); self.s += [x.sum(), y.sum(), (x * x).sum(), (y * y).sum(), (x * y).sum()]
    def add_pairs(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float); self.n += len(x); self.s += [x.sum(), y.sum(), (x * x).sum(), (y * y).sum(), (x * y).sum()]
    def value(self):
        n = self.n; sx, sy, sxx, syy, sxy = self.s / n
        return float((sxy - sx * sy) / np.sqrt((sxx - sx * sx) * (syy - sy * sy)))


class SignACF:
    """Autocorrelation of +1/-1 trade signs at several lags, from running sums, so that days can be added one at a time."""
    def __init__(self, lags): self.lags = lags; self.xy = dict.fromkeys(lags, 0.0); self.n = dict.fromkeys(lags, 0); self.s = 0.0; self.m = 0
    def add(self, sg, k0):                                       # sg: signs with yesterday's last ones in front; k0: first of today's
        self.s += sg[k0:].sum(); self.m += len(sg) - k0
        for L in self.lags:
            a = max(k0 - L, 0)                                   # pairs whose later trade is today's
            if len(sg) - L > a: self.xy[L] += float((sg[a:len(sg) - L] * sg[a + L:]).sum()); self.n[L] += len(sg) - L - a
    def value(self):
        mu = self.s / self.m
        return {str(L): float((self.xy[L] / self.n[L] - mu * mu) / (1 - mu * mu)) for L in self.lags if self.n[L]}


def sequence(symbol, ym, carry_trades=1000):
    out = out_dir(symbol, ym); out.mkdir(parents=True, exist_ok=True)
    waited = wait_for_memory(); t0 = time.time()
    lf = pl.scan_parquet(source(symbol, ym)).select("agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker")
    y, m = map(int, ym.split("-")); day = datetime(y, m, 1, tzinfo=timezone.utc)
    carry = None                                                  # the last trades of the previous day
    m1s, rvs, flags, examples = [], [], [], []
    dur_h = np.zeros(len(DUR_BINS) - 1); tot = dict(dur_n=0, dur_sum=0.0, dur_sq=0.0, dur_zero=0)
    c_trade, c_1s, c_dur = LagCorr(), LagCorr(), LagCorr()
    flow_lags = [1, 2, 5, 10, 30, 60]; c_flow = {L: LagCorr() for L in flow_lags}   # net signed dollars per second, at lags in seconds
    acf_trade, acf_order = SignACF(SIGN_LAGS), SignACF(SIGN_LAGS)  # per trade; per order (same millisecond and side merged)
    prev_last = prev_mid = None                                   # yesterday's last price and last mid, so each day includes the return across midnight
    while day.month == m:
        a, b = int(day.timestamp() * 1000), int((day + timedelta(days=1)).timestamp() * 1000)
        today = lf.filter(pl.col("transact_time").is_between(a, b, closed="left")).collect()
        d0 = day.date(); tk = tick(symbol, day); day += timedelta(days=1)
        if today.height == 0: continue
        n_today = today.height
        df = pl.concat([carry, today]) if carry is not None else today               # the edge: yesterday's last trades in front
        k0 = df.height - n_today                                                     # rows before k0 belong to yesterday
        ts = df["transact_time"].to_numpy(); px = df["price"].to_numpy()
        # durations between trades (today's, including the one across midnight)
        d = np.diff(ts)[max(k0 - 1, 0):].astype(float)
        c_dur.add(d); tot["dur_n"] += len(d); tot["dur_sum"] += d.sum(); tot["dur_sq"] += (d * d).sum(); tot["dur_zero"] += int((d == 0).sum())
        dur_h += np.histogram(np.log10(d.clip(1)), bins=DUR_BINS)[0]
        # trade-to-trade returns, including the pair across midnight
        c_trade.add(np.diff(np.log(px))[max(k0 - 1, 0):])
        # trade signs: +1 if the buyer was the aggressor; an "order" merges consecutive trades in the same millisecond on the same side (a sweep)
        sg = np.where(df["is_buyer_maker"].to_numpy(), -1.0, 1.0)
        acf_trade.add(sg, k0)
        new = np.concatenate([[True], (np.diff(ts) != 0) | (np.diff(sg) != 0)])
        acf_order.add(sg[new], int(new[:k0].sum()))

        def flag(rule, kind, mask, value):
            idx = np.where(mask)[0]; idx = idx[idx >= k0]
            if len(idx):
                flags.append(dict(day=str(d0), rule=rule, kind=kind, n=len(idx)))
                examples.append(pl.DataFrame({"ms": ts[idx[:20]], "rule": rule, "kind": kind, "value": np.asarray(value, float)[idx[:20]],
                                              "id": df["agg_trade_id"].to_numpy()[idx[:20]], "price": px[idx[:20]]}))
        ids = df["agg_trade_id"].to_numpy()
        jump = np.concatenate([[1], np.diff(ids)]) ; flag("missing trades", "error", jump > 1, jump - 1)
        fill_gap = np.concatenate([[1], df["first_trade_id"].to_numpy()[1:] - df["last_trade_id"].to_numpy()[:-1]])
        flag("fills not in the aggregated tape", "check", fill_gap > 1, fill_gap - 1)
        gap = np.concatenate([[0], np.diff(ts)]); flag("silence over 60 seconds", "check", gap > 60_000, gap / 1000)
        # spike and revert vs fast move: distance from the median of the previous 50 trades, in their standard deviations
        med_b = pl.Series(px).shift(1).rolling_median(50).to_numpy(); sd_b = pl.Series(px).shift(1).rolling_std(50).to_numpy()
        med_a = pl.Series(px).shift(-10).rolling_median(10).to_numpy()
        # a trade is unusual only if it is both far in price (at least JUMP_BP from the median of the 50 trades before it)
        # and far in local standard deviations (Brownlees-Gallo: deviation beyond k standard deviations plus a granularity term)
        dev_bp = np.abs(px / med_b - 1) * 1e4
        sd_bp = np.nan_to_num(sd_b / med_b * 1e4, nan=0.0)
        far = np.nan_to_num(dev_bp) >= np.maximum(JUMP_BP, 10 * sd_bp)
        back_bp = np.abs(med_a / med_b - 1) * 1e4
        rev = far & (np.nan_to_num(back_bp, nan=1e9) < 0.2 * np.nan_to_num(dev_bp))       # the next trades return within a fifth of the jump
        flag("spike and revert", "check", rev, dev_bp); flag("jump that persists", "event", far & ~rev, dev_bp)
        del med_b, sd_b, med_a, dev_bp, sd_bp, back_bp
        # bars: 1 second (realised variance) and 1 minute (candles with order flow), today's trades only
        t = today.with_columns(pl.from_epoch("transact_time", time_unit="ms").alias("time"), (pl.col("price") * pl.col("quantity")).alias("usd"))
        t = t.with_columns(pl.when(pl.col("is_buyer_maker")).then(-pl.col("usd")).otherwise(pl.col("usd")).alias("signed_usd"))
        # each second: the last price, and a mid estimated from the aggressor flag: buyer-initiated trades happen at the ask,
        # seller-initiated at the bid, so the last buy and the last sell of the second estimate the ask and the bid
        sec = t.group_by_dynamic("time", every="1s").agg(pl.col("price").last().alias("last"),
                                                         pl.col("price").filter(~pl.col("is_buyer_maker")).last().alias("ask"),
                                                         pl.col("price").filter(pl.col("is_buyer_maker")).last().alias("bid"),
                                                         pl.col("signed_usd").sum().alias("flow"))
        quoted = pl.col("ask").is_not_null() & pl.col("bid").is_not_null() & (pl.col("ask") >= pl.col("bid"))
        sec = sec.with_columns(pl.when(quoted).then((pl.col("ask") + pl.col("bid")) / 2).otherwise(pl.col("last")).alias("mid"),
                               pl.when(quoted).then((pl.col("ask") - pl.col("bid")) / ((pl.col("ask") + pl.col("bid")) / 2) * 1e4).alias("spread_bp"))
        c_1s.add(np.diff(np.log(sec["last"].to_numpy())))
        fl = sec.upsample("time", every="1s").fill_null(0)["flow"].to_numpy() if sec.height else np.array([])   # seconds without trades: zero flow
        for L in flow_lags:
            if len(fl) > L: c_flow[L].add_pairs(fl[:-L], fl[L:])
        sp = sec["spread_bp"].drop_nulls()
        rv = {"day": d0, "spread_p50_bp": float(sp.median()) if len(sp) else None, "spread_p99_bp": float(sp.quantile(0.99)) if len(sp) else None,
              "spread_one_tick": float((sp <= tk / sec["mid"].mean() * 1e4 * 1.01).mean()) if len(sp) else None}
        for s in SIG_DT:
            b_ = sec.group_by_dynamic("time", every=f"{s}s").agg(pl.col("last").last(), pl.col("mid").last())
            for col, prev, key in (("last", prev_last, "rv"), ("mid", prev_mid, "rvm")):
                x = b_[col].to_numpy(); x = np.concatenate([[prev], x]) if prev is not None else x
                rv[f"{key}_{s}"] = float((np.diff(np.log(x)) ** 2).sum())
        prev_last, prev_mid = float(sec["last"][-1]), float(sec["mid"][-1])
        rvs.append(rv)
        m1 = t.group_by_dynamic("time", every="1m").agg(
            pl.col("price").first().alias("open"), pl.col("price").max().alias("high"), pl.col("price").min().alias("low"), pl.col("price").last().alias("close"),
            pl.col("quantity").sum().alias("qty"), pl.col("usd").sum().alias("usd"), pl.col("signed_usd").sum().alias("signed_usd"), pl.len().alias("trades"),
            ((pl.col("price") * pl.col("quantity")).sum() / pl.col("quantity").sum()).alias("vwap"))
        burst = m1.filter(pl.col("trades") > 20 * m1["trades"].median())
        if burst.height:
            flags.append(dict(day=str(d0), rule="activity burst (20 times the day's median minute)", kind="event", n=burst.height))
        m1s.append(m1)
        carry = today.tail(carry_trades)
        del df, today, t, sec
    pl.concat(m1s).write_parquet(out / "m1.parquet")
    pl.DataFrame(rvs).write_parquet(out / "rv_days.parquet")
    pl.DataFrame(flags, schema={"day": pl.Utf8, "rule": pl.Utf8, "kind": pl.Utf8, "n": pl.Int64}).write_parquet(out / "flag_counts.parquet")
    (pl.concat(examples) if examples else pl.DataFrame()).write_parquet(out / "flag_examples.parquet")
    np.save(out / "dur_hist.npy", dur_h)
    n = tot["dur_n"]; mean = tot["dur_sum"] / n
    info = dict(month=ym, ac1_trade_returns=c_trade.value(), ac1_1s_returns=c_1s.value(), dur_mean_ms=mean,
                dur_cv=float(np.sqrt(tot["dur_sq"] / n - mean ** 2) / mean), dur_ac1=c_dur.value(), dur_share_zero_ms=tot["dur_zero"] / n,
                sign_acf_trade=acf_trade.value(), sign_acf_order=acf_order.value(), flow_acf_1s={str(L): c_flow[L].value() for L in flow_lags},
                seconds=round(time.time() - t0, 1), waited_seconds=waited, peak_private_gb=peak_private_gb())
    (out / "sequence.json").write_text(json.dumps(info, indent=1))
    return info


# ---------------------------------------------------------------- the whole pipeline
def _stage(code, log):
    """Run one stage in a fresh Python process, so that its memory is freed and its peak measured alone; append its result to the log."""
    t0 = time.time()
    r = subprocess.run([sys.executable, "-c", f"import json, tape; print(json.dumps({code}, default=str))"], cwd=Path(__file__).parent,
                       capture_output=True, text=True, env={**os.environ, "TAPE_ROOT": str(ROOT)})
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    out = json.loads(r.stdout.strip().splitlines()[-1]) or {}
    out = {"stage": code.split("(")[0].split(".")[-1], **out, "wall_seconds": round(time.time() - t0, 1)}
    with open(log, "a") as f:
        f.write(json.dumps(out, default=str) + "\n")
    return out


def run_pipeline(symbol, start, end, rebuild=False, verbose=True):
    """All six stages for the months start..end (YYYY-MM). Months already converted are not downloaded again.
    Months whose derived tables are newer than their tape are not rebuilt, unless rebuild=True.
    Returns (holes, patches, log): the missing and repeated trade IDs, the patches and their status, and one row per stage and month."""
    base = ROOT / "interim" / "tape" / symbol; base.mkdir(parents=True, exist_ok=True)
    log = base / "run_log.jsonl"; rows = []
    for ym in months(start, end):
        rows.append({"month": ym, **_stage(f"tape.get('{symbol}', '{ym}')", log)})
        if verbose: print(f"get {ym}: done", flush=True)
    holes = find_holes(symbol, start, end); holes.write_parquet(base / f"holes_{start}_{end}.parquet")
    patches = patch(symbol, holes)
    if patches.height: patches.write_parquet(base / f"patches_{start}_{end}.parquet")
    for ym in sorted(set(holes["month"])):
        clean(symbol, ym, holes)
    if verbose:
        print(f"holes: {holes.filter(pl.col('kind') == 'missing').height} ranges of missing IDs, "
              f"{holes.filter(pl.col('kind') == 'repeated').height} days with repeated IDs", flush=True)
    for ym in months(start, end):
        done = {"aggregate": out_dir(symbol, ym) / "days.parquet", "sequence": out_dir(symbol, ym) / "sequence.json"}
        for st in ("aggregate", "sequence"):
            if not rebuild and done[st].exists() and done[st].stat().st_mtime > source(symbol, ym).stat().st_mtime:
                rows.append({"month": ym, "stage": st, "wall_seconds": 0.0}); continue          # up to date: nothing to do
            rows.append({"month": ym, **_stage(f"tape.{st}('{symbol}', '{ym}')", log)})
        if verbose: print(f"aggregate and sequence {ym}: done", flush=True)
    table = [dict(month=r["month"], stage=r["stage"], done="already there" if r.get("peak_private_gb") is None else "run",
                  waited_s=r.get("waited_seconds") or 0.0, run_s=round(r["wall_seconds"] - (r.get("waited_seconds") or 0.0), 1), peak_gb=r.get("peak_private_gb")) for r in rows]
    return holes, patches, pl.DataFrame(table, schema={"month": pl.Utf8, "stage": pl.Utf8, "done": pl.Utf8, "waited_s": pl.Float64, "run_s": pl.Float64, "peak_gb": pl.Float64})
