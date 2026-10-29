"""Convert Bybit's daily history to Parquet, check each day, and delete the raw files of the days that pass.
Book: one row per price level changed, ts (ms, sent), cts (ms, matching engine), u (update id), seq, snap (1 for snapshot rows), side (+1 bid,
-1 ask), tick (price in $0.10 ticks, integer), size (BTC; 0 = level removed). Trades: ts (ms), side (+1 buyer aggressive, -1 seller), tick,
size, id, rpi. Checks: (1) the book rebuilt from the Parquet file segment by segment equals every snapshot that follows continuous data, level by level
(each day file ends with the next midnight's snapshot); pauses of the feed are recorded as gaps in ROOT/parquet/SYMBOL_book_gaps.csv; (2) update ids rise by 1 apart from the reset at the snapshot; (3) trade rows and
total size equal those of the raw file. A day's raw files are deleted only if all checks pass. Usage: python bybit_to_parquet.py ROOT SYMBOL [--keep] [--day=YYYY-MM-DD]"""
import gzip, io, sys, time, zipfile
from pathlib import Path
import numpy as np, orjson, polars as pl, psutil, pyarrow as pa, pyarrow.parquet as pq

SCHEMA = pa.schema([("ts", pa.int64()), ("cts", pa.int64()), ("u", pa.int64()), ("seq", pa.int64()), ("snap", pa.int8()), ("side", pa.int8()),
                    ("tick", pa.int64()), ("size", pa.float64())])
CHUNK = 4_000_000


def wait_for_memory(gb=2.0):
    while psutil.virtual_memory().available / 1e9 < gb: time.sleep(20)


def convert_book(src, dst):
    """Stream the zip, write the Parquet file in chunks; return the second snapshot (for the check) and the message count."""
    cols = {k: [] for k in SCHEMA.names}; n = 0; msgs = 0; snaps = []
    w = pq.ParquetWriter(dst, SCHEMA, compression="zstd")
    z = zipfile.ZipFile(src)
    with z.open(z.infolist()[0]) as f:
        for line in f:
            m = orjson.loads(line); d = m["data"]; snap = 1 if m["type"] == "snapshot" else 0; msgs += 1
            if snap: snaps.append((msgs, {round(float(p) * 10): float(s) for p, s in d["b"]}, {round(float(p) * 10): float(s) for p, s in d["a"]}))
            for side, key in ((1, "b"), (-1, "a")):
                for p, s in d[key]:
                    cols["ts"].append(m["ts"]); cols["cts"].append(m.get("cts", m["ts"])); cols["u"].append(d["u"]); cols["seq"].append(d.get("seq", -1))
                    cols["snap"].append(snap); cols["side"].append(side); cols["tick"].append(round(float(p) * 10)); cols["size"].append(float(s)); n += 1
            if n >= CHUNK:
                w.write_table(pa.table(cols, schema=SCHEMA)); cols = {k: [] for k in SCHEMA.names}; n = 0
    if n: w.write_table(pa.table(cols, schema=SCHEMA))
    w.close()
    return snaps, msgs


def check_book(dst, snaps):
    """Rebuild segment by segment: from each snapshot to the next. A segment that ends at a snapshot following continuous data (update numbers
    rising by 1, no pause over 2 s) must equal that snapshot level by level. A segment that ends after a pause or a break in the numbering is a
    GAP: the feed stopped, and the next snapshot restarts the book; it is recorded, not failed. Every day file ends with the next midnight's snapshot."""
    t = pl.read_parquet(dst, columns=["ts", "u", "snap", "side", "tick", "size"])
    ts, u, sn, side, tick, size = (t[c].to_numpy() for c in ("ts", "u", "snap", "side", "tick", "size"))
    starts = np.flatnonzero((sn == 1) & ((np.r_[0, sn[:-1]] == 0) | (np.r_[0, np.diff(ts)] != 0)))
    bounds = list(starts) + [len(t)]
    bids, asks = {}, {}; checked, mismatched, gaps = 0, 0, []
    for k in range(len(starts)):
        a = starts[k]; e = a
        while e < len(t) and sn[e] == 1 and ts[e] == ts[a]: e += 1
        sb = {int(p): float(q) for s, p, q in zip(side[a:e], tick[a:e], size[a:e]) if s == 1}
        sa = {int(p): float(q) for s, p, q in zip(side[a:e], tick[a:e], size[a:e]) if s == -1}
        if k > 0:
            prev_ts, prev_u = ts[a - 1], u[a - 1]
            broken = (ts[a] - prev_ts > 2000) or not (u[a] in (prev_u, prev_u + 1))
            if broken:
                gaps.append(dict(start_ms=int(prev_ts), end_ms=int(ts[a]), seconds=round((ts[a] - prev_ts) / 1000, 1)))
            else:
                rb = dict(sorted(bids.items(), reverse=True)[:len(sb)]); ra = dict(sorted(asks.items())[:len(sa)])
                checked += 1; mismatched += int(rb != sb or ra != sa)
        bids, asks = dict(sb), dict(sa)
        for s, p, q in zip(side[e:bounds[k + 1]].tolist(), tick[e:bounds[k + 1]].tolist(), size[e:bounds[k + 1]].tolist()):
            book = bids if s == 1 else asks
            if q == 0: book.pop(p, None)
            else: book[p] = q
    du = np.diff(u)
    inner_gaps = int(((du != 0) & (du != 1)).sum()) - len(gaps)                    # breaks in the numbering not at a recorded gap
    return dict(ok=bool(checked > 0 and mismatched == 0 and inner_gaps <= 0), segments_checked=checked, mismatched=mismatched,
                gaps=gaps, rows=len(t))


def convert_trades(src, dst):
    raw = pl.read_csv(src, schema_overrides={"price": pl.Utf8})
    out = raw.select((pl.col("timestamp") * 1000).round(0).cast(pl.Int64).alias("ts"), pl.when(pl.col("side") == "Buy").then(1).otherwise(-1).cast(pl.Int8).alias("side"),
                     (pl.col("price").cast(pl.Float64) * 10).round(0).cast(pl.Int64).alias("tick"), pl.col("size").cast(pl.Float64), pl.col("trdMatchID").alias("id"),
                     (pl.col("RPI") if "RPI" in raw.columns else pl.lit(None)).cast(pl.Int8).alias("rpi"))
    out.write_parquet(dst, compression="zstd")
    back = pl.read_parquet(dst)
    with gzip.open(src, "rt") as g: lines = sum(1 for _ in g) - 1
    ok = len(back) == lines == len(raw) and abs(back["size"].sum() - raw["size"].sum()) < 1e-6
    return dict(ok=bool(ok), rows=len(back), raw_lines=lines)


if __name__ == "__main__":
    ROOT, SYM = Path(sys.argv[1]), sys.argv[2]; KEEP = "--keep" in sys.argv
    ONLY = next((a[6:] for a in sys.argv if a.startswith("--day=")), None)   # one day only, for a test
    RAWB, RAWT = ROOT / "raw" / "orderbook" / "linear" / SYM, ROOT / "raw" / "trades" / SYM
    OUTB, OUTT = ROOT / "parquet" / "orderbook" / SYM, ROOT / "parquet" / "trades" / SYM
    OUTB.mkdir(parents=True, exist_ok=True); OUTT.mkdir(parents=True, exist_ok=True)
    GAPS = []
    for zp in sorted(RAWB.glob("*.data.zip")):
        day = zp.name[:10]
        if day == "2024-03-12" or (ONLY and day != ONLY): continue                                               # the sample day stays raw (Lecture 18 shows its lines)
        tp = RAWT / f"{SYM}{day}.csv.gz"; ob, ot = OUTB / f"{day}.parquet", OUTT / f"{day}.parquet"
        wait_for_memory(); t0 = time.time()
        snaps, msgs = convert_book(zp, ob); cb = check_book(ob, snaps)
        for gp in cb.get("gaps", []): GAPS.append(dict(day=day, **gp))
        ct = convert_trades(tp, ot) if tp.exists() else dict(ok=False, note="trades missing")
        ok = cb["ok"] and ct["ok"]
        if ok and not KEEP: zp.unlink(); tp.unlink()
        print(day, "PASS" if ok else "FAIL", f"{time.time() - t0:.0f} s", "book", cb, "trades", ct, "raw deleted" if ok and not KEEP else "raw kept", flush=True)

    if GAPS:                                                                            # the register of feed gaps, appended to across runs
        reg = ROOT / "parquet" / f"{SYM}_book_gaps.csv"
        new = pl.DataFrame(GAPS)
        old = pl.read_csv(reg) if reg.exists() else None
        (pl.concat([old, new]).unique(subset=["day", "start_ms"]) if old is not None else new).sort("day").write_csv(reg)
