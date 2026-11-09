"""Lecture 22 §3, step 1: the table of real orders of one day, and of control moments, with what the hybrid replay and H1-H9, H20 need. A real order: the trades with the same
millisecond and side (Lecture 19). For each: size S, average price and cost against the mid before, the book state just before it (Lecture 19's state after every update, engine time),
relative size x = S / size at the best on the side taken, imbalance at the best, the mid's move over the last second, the mid at each horizon after it, other takers' size on its side after it,
how many taker orders came in the last 10 s and how much was bought and sold, quote pulls near the best in the last 5 s (Lecture 18's rule, from l22_book.py if it has run) and the gap to Binance's last price. Controls: one random moment in every 10 s, with the same state and mid path and no sign; they are
signed for a side when matched. Nothing is estimated here. Output: L22_OUT/orders/DAY.parquet and L22_OUT/controls/DAY.parquet. Usage: python l22_orders.py YYYY-MM-DD"""
import io, sys, time, zipfile
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l22 as L

DAY = sys.argv[1]; t_start = time.time()
for d in ("orders", "controls"): (L.OUT / d).mkdir(parents=True, exist_ok=True)
S = pl.read_parquet(L.STATE / f"{DAY}.parquet").sort("ts"); st = S["ts"].to_numpy(); mid = ((S["bid"] + S["ask"]) / 2).to_numpy(); qb, qa = S["q_bid"].to_numpy(), S["q_ask"].to_numpy()
q5 = (S["q_bid5"] + S["q_ask5"]).to_numpy(); spread = (S["ask"] - S["bid"]).to_numpy()
T = pl.read_parquet(L.TRADES / f"{DAY}.parquet", columns=["ts", "side", "tick", "size"])
O = T.group_by("ts", "side").agg(pl.col("size").sum().round(6).alias("S"), (pl.col("tick") * pl.col("size")).sum().alias("pq"), pl.len().alias("prints"),
                                 (pl.col("tick").max() - pl.col("tick").min()).alias("walk")).sort("ts").with_columns((pl.col("pq") / pl.col("S")).alias("avg")).drop("pq")
PF = L.OUT / "book" / f"{DAY}.parquet"                                               # pulls from this lecture's pass over the book (l22_book.py), if it has run
P = pl.read_parquet(PF, columns=["ts", "pull"]).sort("ts") if PF.exists() else None
pt = P["ts"].to_numpy() if P is not None else np.array([0]); pc = np.concatenate(([0], np.cumsum(P["pull"].to_numpy()))) if P is not None else np.array([0, 0])
with zipfile.ZipFile(L.BN_RAW / f"{L.SYM}-aggTrades-{DAY}.zip") as z:
    B = pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), columns=["price", "transact_time"]).sort("transact_time")
bt, bp = B["transact_time"].to_numpy(), B["price"].to_numpy() * 10           # Binance price in Bybit ticks of 0.1 USDT
ot, osd, oS = O["ts"].to_numpy(), O["side"].to_numpy(), O["S"].to_numpy(); fc = {s: np.concatenate(([0.0], np.cumsum(np.where(osd == s, oS, 0.0)))) for s in (1, -1)}


def state_at(t):
    """Index of the last book state strictly before t (the book our order would have met), and of the last state at or before t."""
    return np.searchsorted(st, t, "left") - 1, np.searchsorted(st, t, "right") - 1


def features(t):
    """Everything that does not depend on the side: the book just before t, the mid path after it, pulls in the last 5 s, the gap to Binance."""
    i, _ = state_at(t); ok = i >= 0; i = np.maximum(i, 0); m0 = mid[i]
    f = dict(ok=ok, mid0=m0, qb=qb[i], qa=qa[i], q5=q5[i], spread=spread[i], imb=(qb[i] - qa[i]) / (qb[i] + qa[i]), move1=(m0 - mid[np.maximum(state_at(t - 1000)[0], 0)]) / m0 * 1e4)
    for tau in L.TAUS: f[f"m{tau}"] = (mid[np.maximum(state_at(t + tau)[1], 0)] - m0) / m0 * 1e4
    a, b = np.searchsorted(pt, t - 5000, "right"), np.searchsorted(pt, t, "right"); f["pulls5"] = np.where(b > a, (pc[b] - pc[a]) / np.maximum(b - a, 1), np.nan) if P is not None else np.full(len(t), np.nan); f["updates5"] = b - a
    f["act10"] = np.searchsorted(ot, t, "left") - np.searchsorted(ot, t - 10_000, "left")      # taker orders in the 10 s before: how busy the market is
    a10, b10 = np.searchsorted(ot, t - 10_000, "left"), np.searchsorted(ot, t, "left")       # taker size bought and sold in the 10 s before: a stream already running
    f["prior_buy"], f["prior_sell"] = fc[1][b10] - fc[1][a10], fc[-1][b10] - fc[-1][a10]
    j = np.searchsorted(bt, t, "right") - 1; f["bn_gap"] = np.where(j >= 0, (m0 - bp[np.maximum(j, 0)]) / m0 * 1e4, np.nan); f["bn_age"] = np.where(j >= 0, t - bt[np.maximum(j, 0)], -1)
    return f


f = features(ot); end = st[-1] - L.TAUS[-1]
X = O.with_columns(**{k: pl.Series(v) for k, v in f.items()}).filter(pl.col("ok") & (pl.col("ts") <= end)).drop("ok")
X = X.with_columns(((pl.col("S") / pl.when(pl.col("side") == 1).then("qa").otherwise("qb"))).alias("x"), (pl.col("side") * (pl.col("avg") - pl.col("mid0")) / pl.col("mid0") * 1e4).alias("cost_bp"))
xt, xs = X["ts"].to_numpy(), X["side"].to_numpy()
for w in (1_000, 10_000):                                                            # other takers on the same side after the order, the order itself left out
    a = np.searchsorted(ot, xt, "right"); b = np.searchsorted(ot, xt + w, "right")
    X = X.with_columns(pl.Series(f"flow{w}", np.where(xs == 1, fc[1][b] - fc[1][a], fc[-1][b] - fc[-1][a])))
X.write_parquet(L.OUT / "orders" / f"{DAY}.parquet")
rng = np.random.default_rng(int(DAY.replace("-", ""))); t0 = (st[0] // 10_000 + 1) * 10_000; tc = np.arange(t0, end, 10_000) + rng.integers(0, 10_000, len(np.arange(t0, end, 10_000)))
fcn = features(tc); a = np.searchsorted(ot, tc, "right")
C = pl.DataFrame(dict(ts=tc, **fcn)).filter(pl.col("ok")).drop("ok")
for w in (1_000, 10_000):
    b = np.searchsorted(ot, C["ts"].to_numpy() + w, "right"); a = np.searchsorted(ot, C["ts"].to_numpy(), "right")
    C = C.with_columns(pl.Series(f"flow_buy{w}", fc[1][b] - fc[1][a]), pl.Series(f"flow_sell{w}", fc[-1][b] - fc[-1][a]))
C.write_parquet(L.OUT / "controls" / f"{DAY}.parquet")
print(f"{DAY}: {X.height:,} orders ({(X['S'] >= 1).sum():,} of 1 BTC or more), {C.height:,} control moments, {time.time() - t_start:.0f} s")
