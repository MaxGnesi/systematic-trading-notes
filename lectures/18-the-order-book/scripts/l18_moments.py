"""Lecture 18 §1-§2: from the sample day (Bybit BTCUSDT, 12 March 2024, 500-level book, streamed): (a) the book at 12:20:30.000 UTC, best 10
levels each side; (b) 100 ms windows between 12:00 and 13:00 in which the size at the best bid fell while sellers traded there, split into the part
filled by trades and the part cancelled (worked examples for what L2 shows and why trades are needed). Output: l18_moments.json."""
import gzip, csv, io, json, sys, zipfile
from pathlib import Path
import orjson
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l18 as L18

HERE = L18.OUT
BOOK, TRD = L18.SAMPLE_BOOK, L18.SAMPLE_TRADES
T_SNAP = 1710246030000; W0, W1 = 1710244800000, 1710248400000                     # 12:20:30; 12:00-13:00 UTC
trades = []
with gzip.open(TRD, "rt") as g:
    for r in csv.DictReader(g):
        t = round(float(r["timestamp"]) * 1000)
        if W0 <= t <= W1: trades.append((t, r["side"], round(float(r["price"]) * 10), float(r["size"])))
bids, asks = {}, {}; snap = None; prev = None; cands = []; ti = 0
z = zipfile.ZipFile(BOOK)
with z.open(z.infolist()[0]) as f:
    for line in f:
        m = orjson.loads(line); ts = m["ts"]
        if ts > W1: break
        d = m["data"]
        if m["type"] == "snapshot": bids.clear(); asks.clear()
        before_bid = max(bids) if bids else None; before_size = bids.get(before_bid) if bids else None
        for side, book in (("b", bids), ("a", asks)):
            for p, s in d[side]:
                p, s = round(float(p) * 10), float(s)
                if s == 0: book.pop(p, None)
                else: book[p] = s
        if snap is None and ts >= T_SNAP:
            snap = dict(ts=ts, bids=sorted(bids.items(), reverse=True)[:50], asks=sorted(asks.items())[:50])
        if W0 <= ts and prev is not None and before_bid is not None:
            sold = [x for x in trades if prev < x[0] <= ts and x[1] == "Sell" and x[2] == before_bid]
            traded = sum(x[3] for x in sold); after = bids.get(before_bid, 0.0); drop = before_size - after
            if traded > 0 and drop > traded + 0.05 and after > 0:
                cands.append(dict(t0=prev, t1=ts, price=before_bid / 10, before=before_size, traded=round(traded, 4), after=after,
                                  cancelled=round(drop - traded, 4), n_trades=len(sold)))
        prev = ts
out = dict(snapshot=snap, candidates=cands[:40], n_candidates=len(cands))
(HERE / "l18_moments.json").write_text(json.dumps(out, indent=1))
print("book at", snap["ts"], "best bid/ask", snap["bids"][0], snap["asks"][0])
print("windows with fill + cancel at the best bid:", len(cands))
for c in cands[:12]: print(c)
