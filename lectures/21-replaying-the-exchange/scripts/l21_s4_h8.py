"""Lecture 21 §4, H8 and the reaction curve: does the market react to size added at the best? Out of sample, from Lecture 19's book state and the trades.
An addition: between two book updates with the same best price, added = change of the displayed size + size traded at that price in between (§3.1); its size
x = added / size displayed before. For each addition with x >= 5%: the move of the mid over the next 1 s and 10 s in bp, positive away from the addition (up after an
addition to the bid), less the mean move at the control moments of its cell: updates of the same side, day and hour, in the same decile of the imbalance at the best
before the update, with no addition of 5% or more (control A, as fixed). Control B, stricter: the same cells, updates where the queue changed by less than 5% either way, since
a queue that is falling is itself a signal. Removed: within 1 s, with the price still the best, the displayed size plus the size traded since has fallen back by all that was
added. That split depends on what happens after the addition, so it is reported apart and the test uses all additions. Primary: x >= 100%, 1-s horizon, all additions, control
A; p: share of 2,000 resamples of days at or below zero.
Output: L21_OUT/s4/h8_days.parquet (per day, class, kind, horizon), h8_curve.parquet, h8_test.parquet. Usage: python l21_s4_h8.py"""
import sys, time
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
OUT = L21.OUT / "s4"; OUT.mkdir(exist_ok=True); rng = np.random.default_rng(0)
EDGES = np.array([0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, np.inf]); LAB = ["5-10%", "10-25%", "25-50%", "50-100%", "100-200%", "200-400%", "400-800%", "> 800%"]; W = 10


def one_side(ts, px, q, other, tt, tp, tz, mid, hour, sg, day):
    same = np.nonzero(px[1:] == px[:-1])[0] + 1                                  # update i: same best price as update i-1
    o = np.lexsort((tt, tp)); tt, tp, tz = tt[o], tp[o], tz[o]; cz = np.r_[0.0, np.cumsum(tz)]
    key = lambda p, t: np.searchsorted(tp * 10**13 + tt, p * 10**13 + t, side="right")
    tr = cz[key(px[same], ts[same])] - cz[key(px[same], ts[same - 1])]
    added = q[same] - q[same - 1] + tr; x = added / np.maximum(q[same - 1], 1e-9)
    imb = q[same - 1] / np.maximum(q[same - 1] + other[same - 1], 1e-9); dec = np.minimum((np.searchsorted(np.quantile(imb, np.arange(0.1, 1, 0.1)), imb)), 9)
    cell = hour[same] * 10 + dec
    rows = []
    for h, nm in ((1000, "1s"), (10_000, "10s")):
        j = np.searchsorted(ts, ts[same] + h, side="right") - 1; move = sg * (mid[j] - mid[same]) / mid[same] * 1e4
        def base_of(ctrl):
            s = np.bincount(cell[ctrl], move[ctrl], 240); n = np.bincount(cell[ctrl], minlength=240); return np.where(n > 0, s / np.maximum(n, 1), np.nan)
        net = move - base_of(x < 0.05)[cell]; netb = move - base_of(np.abs(x) < 0.05)[cell]; ok = (x >= 0.05) & ~np.isnan(net) & ~np.isnan(netb); idx = np.nonzero(ok)[0]
        if nm == "1s":                                                            # removed within 1 s?
            removed = np.zeros(len(same), bool); nxt = same[idx]; a = added[idx]; qa = q[nxt]; p0 = px[nxt]; alive = np.ones(len(idx), bool); sumr = np.zeros(len(idx), bool); cum = np.zeros(len(idx))
            for k in range(1, W + 2):
                u = np.minimum(nxt + k, len(ts) - 1); alive &= (px[u] == p0) & (ts[u] <= ts[nxt] + 1000)
                t2 = cz[key(p0, ts[u])] - cz[key(p0, ts[nxt])]; sumr |= alive & (q[u] + t2 <= qa - a + 1e-9)
            removed[idx] = sumr
        cls = np.searchsorted(EDGES, x[idx], side="right") - 1
        for c in range(len(LAB)):
            for kind, flag in (("stayed", False), ("removed", True)):
                m = (cls == c) & (removed[idx] == flag)
                rows.append(dict(day=day, cls=LAB[c], kind=kind, h=nm, n=int(m.sum()), net_sum=float(net[idx][m].sum()), netb_sum=float(netb[idx][m].sum()), raw_sum=float(move[idx][m].sum())))
    return rows


rows = []; days = [p.stem for p in sorted(L21.STATE.glob("*.parquet")) if p.stem >= "2025-10-11"]
for day in days:
    t0 = time.time(); S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask", "q_bid", "q_ask"]).sort("ts"); T = pl.read_parquet(L21.TRADES / f"{day}.parquet", columns=["ts", "side", "tick", "size"])
    ts = S["ts"].to_numpy(); mid = (S["bid"].to_numpy() + S["ask"].to_numpy()) / 2; hour = ((ts - L21.ms(day)) // 3_600_000).astype(np.int64).clip(0, 23)
    for px, q, other, sd, sg in ((S["bid"].to_numpy(), S["q_bid"].to_numpy(), S["q_ask"].to_numpy(), -1, 1), (S["ask"].to_numpy(), S["q_ask"].to_numpy(), S["q_bid"].to_numpy(), 1, -1)):
        X = T.filter(pl.col("side") == sd); rows += one_side(ts, px, q, other, X["ts"].to_numpy(), X["tick"].to_numpy(), X["size"].to_numpy(), mid, hour, sg, day)
    print(day, f"{time.time() - t0:.0f} s", flush=True)
D = pl.DataFrame(rows).group_by("day", "cls", "kind", "h").agg(pl.col("n", "net_sum", "netb_sum", "raw_sum").sum()); D.write_parquet(OUT / "h8_days.parquet")
idx = rng.integers(0, len(days), (2000, len(days)))


def stat(G):
    d = G.group_by("day").agg(pl.col("n", "net_sum", "netb_sum", "raw_sum").sum()); g = {r[0]: r[1:] for r in d.select("day", "n", "net_sum", "netb_sum", "raw_sum").iter_rows()}; v = np.array([g.get(x, (0, 0.0, 0.0, 0.0)) for x in days], dtype=float)
    bs = v[idx, 1].sum(1) / np.maximum(v[idx, 0].sum(1), 1); bb = v[idx, 2].sum(1) / np.maximum(v[idx, 0].sum(1), 1); N = max(v[:, 0].sum(), 1)
    return dict(n=int(v[:, 0].sum()), net=v[:, 1].sum() / N, lo=float(np.quantile(bs, .025)), hi=float(np.quantile(bs, .975)), p=float((bs <= 0).mean()), netb=v[:, 2].sum() / N, lob=float(np.quantile(bb, .025)), hib=float(np.quantile(bb, .975)), pb=float((bb <= 0).mean()), raw=v[:, 3].sum() / N)


C = [dict(cls=c, kind=k, h=h, **stat(D.filter((pl.col("cls") == c) & (pl.col("kind").is_in(("stayed", "removed") if k == "all" else (k,))) & (pl.col("h") == h)))) for c in LAB for k in ("all", "stayed", "removed") for h in ("1s", "10s")]
pl.DataFrame(C).write_parquet(OUT / "h8_curve.parquet")
TH = {"x >= 25%": LAB[2:], "x >= 100%": LAB[4:], "x >= 400%": LAB[6:]}
Y = [dict(x=k, h=h, kind="all", **stat(D.filter(pl.col("cls").is_in(v) & (pl.col("h") == h)))) for k, v in TH.items() for h in ("1s", "10s")]
pl.DataFrame(Y).write_parquet(OUT / "h8_test.parquet")
with pl.Config(tbl_rows=40, tbl_cols=20, tbl_width_chars=200, float_precision=3):
    print(pl.DataFrame(C).filter(pl.col("kind") == "all")); print(pl.DataFrame(C).filter((pl.col("kind") == "removed") & (pl.col("h") == "10s")).select("cls", "n", "net", "netb", "raw")); print(pl.DataFrame(Y))
