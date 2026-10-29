"""Lecture 18 §5.1-§5.4: the per-second record of one or more days (best bid and ask, depth within 5 bp of the mid, imbalance of the best 5 levels,
cost of 1 and 5 BTC market orders by walking the book), built with the viewer of §4.1 (tools/orderbook_viewer) and stored in its cache,
BYBIT_ROOT/viewer_cache. With --rebuild, days already in the cache are built again. Usage: python l18_seconds.py [--rebuild] YYYY-MM-DD [...] (default: every day with a book)."""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L
os.environ["BYBIT_ROOT"] = str(L.ROOT); sys.path.insert(0, str(L.REPO / "tools" / "orderbook_viewer"))
import server

REBUILD = "--rebuild" in sys.argv; DAYS = [a for a in sys.argv[1:] if not a.startswith("--")]
for day in DAYS or L.days():
    t0 = time.time(); server.build_cache(day) if REBUILD else server.cached(day, "seconds"); print(day, f"{time.time() - t0:.0f} s", flush=True)
