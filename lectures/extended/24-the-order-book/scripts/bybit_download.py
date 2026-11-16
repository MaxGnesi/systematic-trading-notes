"""Download Bybit's public history for one perpetual: the order book (daily zip of JSON lines, snapshot + 100 ms updates) and the trades
(daily csv.gz), for a range of days, into ROOT/raw/{orderbook/linear,trades}/SYMBOL. Days already complete are skipped; every file is checked
against the size the server reports; failed downloads are retried. The book's depth changed over time (500 levels until about August 2025,
200 levels after); the script takes whichever exists, in the order given. Usage: python bybit_download.py ROOT SYMBOL FIRST_DAY LAST_DAY"""
import sys, time, urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT, SYM, D0, D1 = Path(sys.argv[1]), sys.argv[2], date.fromisoformat(sys.argv[3]), date.fromisoformat(sys.argv[4])
BOOK = "https://quote-saver.bycsi.com/orderbook/linear/{s}/{d}_{s}_{k}.data.zip"; TRADES = "https://public.bybit.com/trading/{s}/{s}{d}.csv.gz"
DEPTHS = ["ob500", "ob200", "ob1000"]


def size_of(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30) as r: return int(r.headers["Content-Length"])
    except Exception: return None


def fetch(url, dst, n):
    if dst.exists() and dst.stat().st_size == n: return "have"
    for attempt in range(4):
        try:
            tmp = dst.with_suffix(dst.suffix + ".part")
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20): f.write(chunk)
            if tmp.stat().st_size == n: tmp.replace(dst); return "ok"
        except Exception as e: print("   retry", attempt + 1, dst.name, e, flush=True)
        time.sleep(5 * (attempt + 1))
    return "FAILED"


(ROOT / "raw" / "orderbook" / "linear" / SYM).mkdir(parents=True, exist_ok=True); (ROOT / "raw" / "trades" / SYM).mkdir(parents=True, exist_ok=True)
d = D0
while d <= D1:
    out = []
    for k in DEPTHS:
        u = BOOK.format(s=SYM, d=d, k=k); n = size_of(u)
        if n: out.append(f"book {k} {n / 1e6:.0f} MB {fetch(u, ROOT / 'raw' / 'orderbook' / 'linear' / SYM / f'{d}_{SYM}_{k}.data.zip', n)}"); break
    else: out.append("book MISSING")
    u = TRADES.format(s=SYM, d=d); n = size_of(u)
    out.append(f"trades {n / 1e6:.0f} MB {fetch(u, ROOT / 'raw' / 'trades' / SYM / f'{SYM}{d}.csv.gz', n)}" if n else "trades MISSING")
    print(d, " | ".join(out), flush=True); d += timedelta(days=1)
