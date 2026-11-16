"""Buy and sell lambdas as Brennan, Chordia, Subrahmanyam and Tong (2010 conference version; JFE 2012), equation (4), a modified Glosten-Harris
model: dp_t = a + lam_buy * q_t 1{q_t > 0} + lam_sell * q_t 1{q_t < 0} + psi (D_t - D_{t-1}) + y_t, OLS, trade by trade. Here a trade is a Bybit
taker order (trades with the same ms and side), p_t its size-weighted fill price in ticks, q_t its signed size in BTC, D_t its recorded side
(Bybit records the aggressor, so no Lee-Ready classification). Both lambdas positive = buys lift and sells lower the price. Fitted per day (their
per stock-month analogue), per 15-minute block and per 2-hour window aligned so that one ends at 20:50 on 10 Oct."""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l20 as L20
L20.log("kyle_bcst")

DAYS = L20.days()
POST = int(np.datetime64("2025-10-10T20:50:00", "ms").astype(np.int64))


def fit(dp, q, dD):
    X = np.column_stack([np.ones(len(dp)), np.where(q > 0, q, 0.0), np.where(q < 0, q, 0.0), dD])
    if (q > 0).sum() < 30 or (q < 0).sum() < 30: return np.nan, np.nan, np.nan
    b = np.linalg.lstsq(X, dp, rcond=None)[0]; return b[1], b[2], b[3]


rows = {15: [], 120: []}; daily = []
for d in DAYS:
    O = pl.read_parquet(L20.ORD / f"bybit_{d}.parquet", columns=["ts", "side", "size", "tick"]).sort("ts")
    t = O["ts"].to_numpy(); p = O["tick"].to_numpy().astype(float); D = O["side"].to_numpy().astype(float); q = D * O["size"].to_numpy()
    dp, dD, q1, t1 = np.diff(p), np.diff(D), q[1:], t[1:]
    lb, ls, ps = fit(dp, q1, dD); daily.append(dict(day=d, lb=lb, ls=ls, psi=ps, n=len(dp)))
    for L in (15, 120):
        b = (t1 - POST) // (L * 60_000)
        for k in np.unique(b):
            m = b == k; lb_, ls_, ps_ = fit(dp[m], q1[m], dD[m])
            rows[L].append(dict(day=d, b=int(k), lb=lb_, ls=ls_, psi=ps_, n=int(m.sum()), vol=float(np.abs(q1[m]).sum())))
    print(d, f"lam_buy {lb:.1f} lam_sell {ls:.1f} psi {ps:.1f} ticks", flush=True)
Dd = pl.DataFrame(daily); Dd.write_parquet(L20.S4 / "bcst_daily.parquet")
I = Dd.filter(pl.col("day") < "2025-10-10"); O_ = Dd.filter(pl.col("day") > "2025-10-10")
for nm, g in (("calm days", I), ("after 10 Oct", O_)):
    r = g["ls"] / g["lb"]
    print(f"{nm}: median buy {g['lb'].median():.2f}, sell {g['ls'].median():.2f} ticks per BTC, sell/buy median {r.median():.3f}, sell > buy on {int((r > 1).sum())} of {g.height} days")
print("10 Oct:", Dd.filter(pl.col("day") == "2025-10-10").row(0, named=True))
sp = lambda a, b: float(np.corrcoef(a.rank().to_numpy(), b.rank().to_numpy())[0, 1])
for L in (15, 120):
    G = pl.DataFrame(rows[L]).drop_nulls().filter(pl.col("lb").is_finite() & pl.col("ls").is_finite()).with_columns((pl.col("ls") - pl.col("lb")).alias("diff"))
    G.write_parquet(L20.S4 / f"bcst_{L}.parquet")
    Ic = G.filter(pl.col("day") < "2025-10-10"); pc = lambda v, c: float((Ic[c] < v).mean())
    print(f"{L} min blocks, calm days: rho(vol) buy {sp(Ic['lb'], Ic['vol']):+.2f} sell {sp(Ic['ls'], Ic['vol']):+.2f} diff {sp(Ic['diff'], Ic['vol']):+.2f}; sell>buy in {float((Ic['diff'] > 0).mean()):.0%}")
    C = G.filter(pl.col("day") == "2025-10-10").filter((pl.col("b") >= -(240 // L)) & (pl.col("b") < 120 // L)).sort("b")
    for r in C.iter_rows(named=True):
        m = 20 * 60 + 50 + L * r["b"]
        print(f"   {m // 60:02d}:{m % 60:02d}  buy {r['lb']:6.2f} ({pc(r['lb'], 'lb'):.3f})  sell {r['ls']:6.2f} ({pc(r['ls'], 'ls'):.3f})  sell-buy {r['diff']:+6.2f} ({pc(r['diff'], 'diff'):.3f})  orders {r['n']}")
    if L == 120:
        ref = G.filter(pl.col("day") != "2025-10-10"); x = G.filter((pl.col("day") == "2025-10-10") & (pl.col("b") == -1)).row(0, named=True)
        for c in ("lb", "ls", "diff"):
            v = ref[c].to_numpy(); print(f"   2 h before the post, {c}: {x[c]:.2f}, above {np.mean(v < x[c]):.3f} of {len(v)}, p = {(1 + (v >= x[c]).sum()) / (1 + len(v)):.3f}")
