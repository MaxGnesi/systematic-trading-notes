"""Order-book viewer for Part IV: a small local web app to scan through the Bybit BTCUSDT book and trades of Lecture 18.

Reads the Parquet tables written by bybit_to_parquet.py (Lecture 18, §3). The book can only be reconstructed from a day's midnight snapshot, so the
first time a day is opened the server replays it once and caches (next to the data) a checkpoint of the book every minute and a summary of every
second (best bid and ask, depth within 5 bp); later requests start from the nearest checkpoint.
Run:  python server.py   then open http://127.0.0.1:8077
Settings (environment variables): BYBIT_ROOT, the folder holding parquet/orderbook/SYMBOL and parquet/trades/SYMBOL (default D:/trading-data/bybit);
VIEWER_PORT (default 8077)."""
import base64, os, time
from pathlib import Path
import numpy as np, polars as pl
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(os.environ.get("BYBIT_ROOT", "D:/trading-data/bybit")); SYM = "BTCUSDT"
BOOK, TRADES = ROOT / "parquet" / "orderbook" / SYM, ROOT / "parquet" / "trades" / SYM
CACHE = ROOT / "viewer_cache" / SYM; CACHE.mkdir(parents=True, exist_ok=True)
HERE = Path(__file__).parent
DAY_MS, BAND = 86_400_000, 5e-4                                                    # depth is measured within 5 bp of the mid
EVENTS = {"2025-10-10": [(14 * 3600_000 + 57 * 60_000 + 52_308, "Truth Social post: 'a massive increase of Tariffs' on China"),
                         (20 * 3600_000 + 50 * 60_000 + 1_702, "Truth Social post: an additional 100% tariff on China")]}   # times from the post IDs (Lecture 20)
app = FastAPI(title="Order-book viewer")


def day_start_ms(day):
    return int(np.datetime64(day, "ms").astype(np.int64))


def depth(bids, asks, mid):
    lo, hi = mid * (1 - BAND), mid * (1 + BAND)
    return sum(q for p, q in bids.items() if p >= lo), sum(q for p, q in asks.items() if p <= hi)


def walk_bp(levels, size, mid, sign):
    """What a market order of `size` BTC pays by walking the given levels, in bp beyond the mid (None if the book is too thin)."""
    left, cost = size, 0.0
    for p, q in levels:
        x = min(left, q); cost += x * p; left -= x
        if left <= 1e-12: return sign * (cost / size / mid - 1) * 1e4
    return None


def build_cache(day):
    """Replay the day once: the book before every full minute (checkpoints) and, at the end of every second, best bid and ask and depth within 5 bp."""
    t0 = time.time(); d0 = day_start_ms(day)
    b = pl.read_parquet(BOOK / f"{day}.parquet", columns=["cts", "snap", "side", "tick", "size"])
    ts, sn, sd, tk, sz = (b[c].to_numpy() for c in ("cts", "snap", "side", "tick", "size"))
    starts = np.flatnonzero(np.r_[True, np.diff(ts) != 0])
    bids, asks, cps, secs = {}, {}, [], []; nxt_min, nxt_sec = d0, d0 + 1000
    for k, a in enumerate(starts):
        while ts[a] >= nxt_min and nxt_min < d0 + DAY_MS:
            for book, s in ((bids, 1), (asks, -1)): cps += [(nxt_min, s, p, q) for p, q in book.items()]
            nxt_min += 60_000
        while ts[a] >= nxt_sec and nxt_sec <= d0 + DAY_MS:
            if bids and asks:
                bb, ba = max(bids), min(asks); mid = (bb + ba) / 2; db, da = depth(bids, asks, mid)
                A = sorted(asks.items()); B = sorted(bids.items(), reverse=True)
                b5, a5 = sum(q for _, q in B[:5]), sum(q for _, q in A[:5])
                secs.append((nxt_sec, bb, ba, db, da, (b5 - a5) / (b5 + a5), walk_bp(A, 1, mid, 1), walk_bp(A, 5, mid, 1), walk_bp(B, 1, mid, -1), walk_bp(B, 5, mid, -1)))
            nxt_sec += 1000
        e = starts[k + 1] if k + 1 < len(starts) else len(b)
        if sn[a] == 1: bids.clear(); asks.clear()
        for s, p, q in zip(sd[a:e].tolist(), tk[a:e].tolist(), sz[a:e].tolist()):
            book = bids if s == 1 else asks
            if q == 0: book.pop(p, None)
            else: book[p] = q
    pl.DataFrame(cps, schema=["at", "side", "tick", "size"], orient="row").write_parquet(CACHE / f"{day}_checkpoints.parquet")
    pl.DataFrame(secs, schema=["at", "bid", "ask", "depth_bid", "depth_ask", "imbalance", "buy_1", "buy_5", "sell_1", "sell_5"], orient="row").write_parquet(CACHE / f"{day}_seconds.parquet")
    print(f"cache for {day}: {time.time() - t0:.0f} s")


def cached(day, kind):
    f = CACHE / f"{day}_{kind}.parquet"
    s = CACHE / f"{day}_seconds.parquet"
    if not f.exists() or not s.exists() or "buy_5" not in pl.read_parquet_schema(s): build_cache(day)   # rebuild caches from before the cost columns
    return pl.read_parquet(f)


def book_at(day, ms):
    """The exact book just after the last update at or before `ms` (milliseconds since 1970)."""
    d0 = day_start_ms(day); at = d0 + (ms - d0) // 60_000 * 60_000
    base = cached(day, "checkpoints").filter(pl.col("at") == at)
    bids = {p: q for s, p, q in base.select("side", "tick", "size").iter_rows() if s == 1}
    asks = {p: q for s, p, q in base.select("side", "tick", "size").iter_rows() if s == -1}
    b = pl.scan_parquet(BOOK / f"{day}.parquet").filter((pl.col("cts") >= at) & (pl.col("cts") <= ms)).select("cts", "snap", "side", "tick", "size").collect()
    prev = None
    for cts, snap, s, p, q in b.iter_rows():
        if snap == 1 and prev != (cts, 1): bids.clear(); asks.clear()           # a snapshot replaces the book
        prev = (cts, snap)
        book = bids if s == 1 else asks
        if q == 0: book.pop(p, None)
        else: book[p] = q
    return bids, asks


def encode(m):
    """Resting size per cell as one byte: 0 empty, 1-255 log10(size) from 0.001 to 30 BTC; base64 for the browser."""
    v = np.zeros(m.shape, np.uint8); ok = m > 0
    v[ok] = np.clip((np.log10(m[ok]) + 3) / np.log10(30_000) * 254 + 1, 1, 255).astype(np.uint8)
    return base64.b64encode(v.tobytes()).decode()


@app.get("/api/days")
def days():
    return sorted(p.stem for p in BOOK.glob("*.parquet"))


@app.get("/api/gaps")
def gaps():
    f = ROOT / "parquet" / f"{SYM}_book_gaps.csv"
    return pl.read_csv(f).to_dicts() if f.exists() else []


@app.get("/api/overview")
def overview(day: str):
    """The whole day per minute: mid (last), its low and high, depth within 5 bp, traded volume; plus the day's events."""
    if not (BOOK / f"{day}.parquet").exists(): raise HTTPException(404, "no such day")
    d0 = day_start_ms(day)
    s = cached(day, "seconds").with_columns(((pl.col("at") - d0 - 1) // 60_000).alias("m"), ((pl.col("bid") + pl.col("ask")) / 20).alias("mid"))
    s = s.with_columns(((pl.col("ask") - pl.col("bid")) / 10).alias("spread"))
    m = s.group_by("m").agg(pl.col("mid").last(), pl.col("mid").min().alias("lo"), pl.col("mid").max().alias("hi"),
                            pl.col("depth_bid").mean(), pl.col("depth_ask").mean(), pl.col("spread").mean(), pl.col("imbalance").mean(),
                            pl.col("buy_1").mean(), pl.col("buy_5").mean(), pl.col("sell_1").mean(), pl.col("sell_5").mean()).sort("m")
    v = (pl.scan_parquet(TRADES / f"{day}.parquet").select(((pl.col("ts") - d0) // 60_000).alias("m"), "size").group_by("m")
           .agg(pl.col("size").sum().alias("vol")).collect())
    m = m.join(v, on="m", how="left").with_columns(pl.col("vol").fill_null(0.0))
    return dict(day=day, d0=d0, minutes=m.to_dict(as_series=False), events=[dict(ms=d0 + t, text=x) for t, x in EVENTS.get(day, [])])


@app.get("/api/at")
def at_cursor(day: str, ms: int, levels: int = 15):
    """At one moment: the ladder (best `levels` each side), spread, depth within 5 bp, book imbalance over the best 5 levels, the cost of market
    orders of 1 and 5 BTC by walking the book, and the trades of the 20 seconds up to that moment."""
    bids, asks = book_at(day, ms)
    if not bids or not asks: raise HTTPException(404, "no book at this moment")
    bb, ba = max(bids), min(asks); mid = (bb + ba) / 2
    B = sorted(bids.items(), reverse=True); A = sorted(asks.items())
    db, da = depth(bids, asks, mid)
    b5, a5 = sum(q for _, q in B[:5]), sum(q for _, q in A[:5])

    def walk(levels_, size, sign):
        left, cost = size, 0.0
        for p, q in levels_:
            t = min(left, q); cost += t * p; left -= t
            if left <= 1e-12: avg = cost / size; return dict(avg=avg / 10, bp=round(sign * (avg / mid - 1) * 1e4, 2))
        return None
    tr = (pl.scan_parquet(TRADES / f"{day}.parquet").filter(pl.col("ts").is_between(ms - 20_000, ms)).select("ts", "side", "tick", "size")
            .collect().sort("ts", descending=True).head(60))
    return dict(ms=ms, bids=B[:levels], asks=A[:levels], spread=(ba - bb) / 10, mid=mid / 10, depth_bid=db, depth_ask=da,
                imbalance=(b5 - a5) / (b5 + a5), buy_1=walk(A, 1, 1), buy_5=walk(A, 5, 1), sell_1=walk(B, 1, -1), sell_5=walk(B, 5, -1), trades=tr.rows())


@app.get("/api/window")
def window(day: str, start: float, seconds: float = 60, max_cols: int = 900, max_rows: int = 400):
    """The book and the trades from `start` (seconds after midnight UTC) for `seconds`: a heatmap of resting size (price x time, bids and asks),
    the best bid and ask at every update, and every trade (or, if very many, the trades summed per 100 ms and side)."""
    if not (BOOK / f"{day}.parquet").exists(): raise HTTPException(404, "no such day")
    seconds = float(np.clip(seconds, 1, 1800)); d0 = day_start_ms(day); w0 = int(d0 + start * 1000); w1 = int(w0 + seconds * 1000)
    cp = cached(day, "checkpoints"); at = d0 + int(start // 60) * 60_000
    base = cp.filter(pl.col("at") == at)
    bids = {p: q for s, p, q in base.select("side", "tick", "size").iter_rows() if s == 1}
    asks = {p: q for s, p, q in base.select("side", "tick", "size").iter_rows() if s == -1}
    b = (pl.scan_parquet(BOOK / f"{day}.parquet").filter((pl.col("cts") >= at) & (pl.col("cts") <= w1))
           .select("cts", "snap", "side", "tick", "size").collect())
    ts, sn, sd, tk, sz = (b[c].to_numpy() for c in ("cts", "snap", "side", "tick", "size"))
    starts = np.flatnonzero(np.r_[True, np.diff(ts) != 0]) if len(ts) else np.array([], int)
    states, best = [], []
    for k, a in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else len(b)
        if sn[a] == 1: bids.clear(); asks.clear()
        for s, p, q in zip(sd[a:e].tolist(), tk[a:e].tolist(), sz[a:e].tolist()):
            book = bids if s == 1 else asks
            if q == 0: book.pop(p, None)
            else: book[p] = q
        if ts[a] >= w0 and bids and asks:
            states.append((int(ts[a]), dict(bids), dict(asks))); best.append((int(ts[a]), max(bids), min(asks)))
    if not states: raise HTTPException(404, "no book updates in this window")
    tr = (pl.scan_parquet(TRADES / f"{day}.parquet").filter(pl.col("ts").is_between(w0, w1)).select("ts", "side", "tick", "size").collect())
    lo = min(min(x[1] for x in best), int(tr["tick"].min()) if len(tr) else 10**12) - 150
    hi = max(max(x[2] for x in best), int(tr["tick"].max()) if len(tr) else 0) + 150
    tick_per_row = max(1, int(np.ceil((hi - lo + 1) / max_rows))); nrows = (hi - lo) // tick_per_row + 1
    ncols = min(max_cols, len(states)); idx = np.linspace(0, len(states) - 1, ncols).round().astype(int)
    MB = np.zeros((nrows, ncols), np.float32); MA = np.zeros((nrows, ncols), np.float32)
    for j, i in enumerate(idx):
        _, bb, aa = states[i]
        for book, M in ((bb, MB), (aa, MA)):
            for p, q in book.items():
                r = (p - lo) // tick_per_row
                if 0 <= r < nrows: M[r, j] += q
    if len(tr) > 30_000:                                                            # very busy windows: trades summed per 100 ms and side
        tr = (tr.with_columns((pl.col("ts") // 100 * 100).alias("ts"))
                .group_by("ts", "side").agg((pl.col("tick") * pl.col("size")).sum().alias("v"), pl.col("size").sum())
                .with_columns((pl.col("v") / pl.col("size")).round(0).cast(pl.Int64).alias("tick")).drop("v").sort("ts"))
    return dict(day=day, t0=w0, t1=w1, times=[states[i][0] for i in idx], lo=lo, tick_per_row=tick_per_row, nrows=nrows, ncols=ncols,
                bids=encode(MB), asks=encode(MA), best=best, trades=tr.select("ts", "side", "tick", "size").rows(), tick_size=0.1)


app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(HERE / "static" / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("VIEWER_PORT", 8077)))
