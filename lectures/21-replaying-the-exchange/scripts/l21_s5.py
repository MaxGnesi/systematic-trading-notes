"""Lecture 21 §5: the replay in the cascade, 20:50-22:50 UTC, on 10 October against the same window on the other 44 days. Description only: the one test is H6 (§4). No new replay:
everything is read from the runs of §3.2, §3.3 and H6.
days.parquet: per day and quoter (the test order and the once-a-second quoter, Q2, a = 1, L = 50 ms, 0.001 BTC a side, no limit on the position): fills, adverse share, markouts,
  the sum of the 10-s markouts over all fills (fill-bp), the largest position in BTC, and the result in USDT at the mid at 22:50 before the fee, in all and split into the spread
  and move after each fill (fill to 10 s later) and the rest, which is the position carried.
taker.parquet: per day, S and L, the orders of §3.2 sent in the window: share paying more than seen, share of IOC orders filled short, mean slippage, spread, orders without a price.
path.parquet, path_taker.parquet: 10 October in steps of 10 minutes: the mid, fills, adverse share and 10-s markout of each quoter, its position; the taker measures at L = 50 ms.
minutes.parquet: 10 October minute by minute: the mid in USDT and each quoter's position.
rules.parquet: the held orders of §3.3 in the two half-hours inside the cascade (21:30, 22:00) against all other half-hours, by fill rule: share filled, 10-s markout.
Output: L21_OUT/s5/. Usage: python l21_s5.py"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21
OUT = L21.OUT / "s5"; OUT.mkdir(parents=True, exist_ok=True); CRASH = "2025-10-10"; STEP = 600_000
days = sorted(f.stem for f in (L21.OUT / "s4" / "h6").glob("*.parquet")); Q = []; T = []; PQ = []; PT = []; M1 = []


def mids(day, a, b):
    S = pl.scan_parquet(L21.STATE / f"{day}.parquet").select("ts", "bid", "ask").filter((pl.col("ts") >= a) & (pl.col("ts") <= b)).sort("ts").collect()
    return S["ts"].to_numpy(), ((S["bid"] + S["ask"]) / 2).to_numpy()


def taker(X):
    return [pl.len().alias("n"), (pl.col("paid_bp") - pl.col("exp_bp")).is_nan().sum().alias("empty"), (pl.col("paid_bp") - pl.col("exp_bp")).filter((pl.col("paid_bp") - pl.col("exp_bp")).is_not_nan()).mean().alias("slip"),
            ((pl.col("paid_bp") - pl.col("exp_bp")) > 1e-9).mean().alias("worse"), (pl.col("ioc_fill") < 1 - 1e-9).mean().alias("short"), pl.col("spread_bp").mean().alias("spread"), pl.col("ret10_bp").abs().mean().alias("move10"), pl.col("ret10_bp").abs().median().alias("move10_med")]


for day in days:
    a, b = L21.ms(day, "20:50:00"), L21.ms(day, "22:50:00"); ts, mid = mids(day, a, b); end = mid[-1]
    D = pl.read_parquet(L21.OUT / "s4" / "h6" / f"{day}.parquet").filter(pl.col("filled")).with_columns(pl.col("price").abs().alias("p")).sort("end")
    for q in ("instant", "1s"):
        F = D.filter(pl.col("quoter") == q); sd, p, t, m10 = F["side"].to_numpy(), F["p"].to_numpy().astype(float), F["end"].to_numpy(), F["mid10"].to_numpy() * F["side"].to_numpy()
        pos = np.cumsum(sd) * 0.001                                               # a bid filled is a buy; mid10 is stored with the ask side negated
        tot = float((sd * (end - p)).sum() * 0.001 * L21.TICK); fast = float((sd * (m10 - p)).sum() * 0.001 * L21.TICK); mk = sd * (m10 - p) / p * 1e4
        Q.append(dict(day=day, quoter=q, fills=len(F), adverse=float(F["adverse"].mean()), m10=float(mk.mean()), m10_sd=float(mk.std()), fill_bp=float(mk.sum()), max_pos=float(np.abs(pos).max()), last_pos=float(pos[-1]), usdt=tot, usdt_10s=fast, usdt_held=tot - fast, volume_usdt=float(p.sum() * 0.001 * L21.TICK)))
        if day == CRASH:
            mm = np.searchsorted(ts, a + 60_000 * np.arange(121), side="right") - 1; pp = np.searchsorted(t, a + 60_000 * np.arange(121), side="right")
            M1.append(pl.DataFrame(dict(quoter=[q] * 121, minute=np.arange(121), mid=mid[np.maximum(mm, 0)] * L21.TICK, pos=np.r_[0.0, pos][pp])))
            k = (t - a) // STEP; ii = np.searchsorted(ts, a + STEP * np.arange(12), side="left")
            for j in range(12):
                m = k == j
                PQ.append(dict(quoter=q, step=j, mid=float(mid[min(ii[j], len(mid) - 1)]), fills=int(m.sum()), adverse=float(F["adverse"].to_numpy()[m].mean()) if m.any() else np.nan, m10=float(mk[m].mean()) if m.any() else np.nan, buys=int((sd[m] == 1).sum()), sells=int((sd[m] == -1).sum()), pos=float(pos[m][-1]) if m.any() else np.nan))
    X = pl.scan_parquet(L21.OUT / "s32" / "orders" / f"{day}.parquet").filter((pl.col("t") >= a) & (pl.col("t") < b)).collect()
    T.append(X.group_by("S", "L").agg(taker(X)).with_columns(pl.lit(day).alias("day")))
    if day == CRASH: PT = X.filter(pl.col("L") == 50).with_columns(((pl.col("t") - a) // STEP).alias("step")).group_by("S", "step").agg(taker(X)).sort("S", "step")
    del X, D
pl.DataFrame(Q).write_parquet(OUT / "days.parquet"); pl.concat(T).write_parquet(OUT / "taker.parquet")
pl.DataFrame(PQ).write_parquet(OUT / "path.parquet"); pl.concat(M1).write_parquet(OUT / "minutes.parquet"); PT.write_parquet(OUT / "path_taker.parquet")
H = (pl.scan_parquet(str(L21.OUT / "s33" / "*.parquet")).select("day", "sent", "price", "rule", "fill", "mid10").collect()
     .with_columns(((pl.col("sent") - pl.col("day").map_elements(L21.ms, return_dtype=pl.Int64)) // 1_800_000).alias("hh"), ((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10")))
R = (H.with_columns((pl.when(pl.col("day") == CRASH).then(pl.col("hh").cast(pl.String)).otherwise(pl.lit("other"))).alias("when")).filter((pl.col("when") == "other") | pl.col("when").is_in(["43", "44"]))
     .group_by("when", "rule").agg(pl.len().alias("n"), pl.col("fill").is_not_null().mean().alias("filled"), pl.col("m10").filter(pl.col("fill").is_not_null()).mean().alias("m10")).sort("when", "rule")); R.write_parquet(OUT / "rules.parquet")
with pl.Config(tbl_rows=80, tbl_cols=20, tbl_width_chars=220):
    A = pl.read_parquet(OUT / "days.parquet"); print(A.filter(pl.col("day") == CRASH)); print(A.group_by("quoter").agg(pl.col("fills", "adverse", "m10", "fill_bp", "max_pos", "usdt", "usdt_10s", "usdt_held").median()))
    B = pl.read_parquet(OUT / "taker.parquet").filter(pl.col("L") == 50); print(B.filter(pl.col("day") == CRASH).sort("S")); print(B.group_by("S").agg(pl.col("worse", "short", "slip", "spread").median(), pl.col("worse", "short", "slip").filter(pl.col("day") != CRASH).max().name.suffix("_max")).sort("S"))
    print(pl.read_parquet(OUT / "path.parquet")); print(PT.filter(pl.col("S") < 0.002)); print(PT.filter(pl.col("S") > 4)); print(R)
    print(B.filter(pl.col("S") < 0.002).group_by(pl.col("day") == CRASH).agg(pl.col("move10", "move10_med").median()))
    print(pl.read_parquet(OUT / "taker.parquet").filter((pl.col("day") == CRASH) & ((pl.col("S") < 0.002) | (pl.col("S") > 4))).sort("S", "L").select("S", "L", "empty", "slip", "worse", "short"))
    print(A.group_by("quoter", pl.col("day") == CRASH).agg(pl.col("m10_sd").median()).sort("quoter", "day"))
    for q in ("instant", "1s"):
        o = A.filter((pl.col("quoter") == q) & (pl.col("day") != CRASH)); print(q, "worst others usdt", o.sort("usdt").head(3).select("day", "usdt", "usdt_10s", "usdt_held", "max_pos").rows(), "best", o["usdt"].max(), "share of days with held<0", (o["usdt_held"] < 0).mean(), "max pos other", o["max_pos"].max())
