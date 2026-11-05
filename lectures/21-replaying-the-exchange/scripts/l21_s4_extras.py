"""Lecture 21 §4, two descriptive measures. quoters: the two quoters of l21_mm.py on the eight days (Q2, a = 1, and the other rules): fills per hour, share adverse, 10-s markout; for the fills
of each quoter under Q2 (a = 1, L = 50 ms), those within 1 s of the previous fill on the same side against the rest. rest: limit orders that miss: the minimum-size decisions of §3.2 at
L = 50 ms left short (out of sample, in the half-hours of §3.3) rest at the best price seen; fill share within 120 s under Q2 (a = 1) and 10-s markout, against §3.3's orders at the best.
Output: L21_OUT/s4/quoters.parquet, reentry.parquet, rest.parquet. Usage: python l21_s4_extras.py quoters|rest"""
import sys
from pathlib import Path
import numpy as np, polars as pl
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l21 as L21, l21_mm as MM
from l21_s4_h679 import with_empty
S4 = L21.OUT / "s4"; rng = np.random.default_rng(0); m10 = ((pl.col("mid10") - pl.col("price")) / pl.col("price").abs() * 1e4).alias("m10")
if sys.argv[1] == "quoters":
    F = pl.scan_parquet([L21.OUT / "mm" / f"{d}.parquet" for d in MM.DAYS]); n = len(MM.DAYS); idx = rng.integers(0, n, (2000, n))
    A = (F.group_by("quoter", "rule", "L").agg(pl.len().alias("orders"), pl.col("filled").sum().alias("fills"), pl.col("adverse").filter(pl.col("filled")).mean().alias("adverse"), m10.filter(pl.col("filled")).mean())
         .with_columns((pl.col("fills") / (n * 24)).alias("per_hour"), (pl.col("fills") / pl.col("orders")).alias("fill_rate")).sort("rule", "L", "quoter").collect()); A.write_parquet(S4 / "quoters.parquet")
    Q = (F.filter(pl.col("filled") & (pl.col("rule") == "Q2 a=1") & (pl.col("L") == 50)).select("quoter", "day", "side", "end", "adverse", m10).collect().sort("quoter", "day", "side", "end")
         .with_columns((pl.col("end") - pl.col("end").shift(1).over("quoter", "day", "side")).alias("gap")).with_columns((pl.col("gap") < 1000).fill_null(False).alias("quick")))
    rows = []
    for (q, k), G in Q.group_by("quoter", "quick"):
        d = G.group_by("day").agg(pl.len().alias("n"), pl.col("m10").sum().alias("s")).sort("day").select("n", "s").to_numpy().astype(float); bs = d[idx, 1].sum(1) / d[idx, 0].sum(1)
        rows.append(dict(quoter=q, quick=bool(k), fills=G.height, share=G.height / Q.filter(pl.col("quoter") == q).height, adverse=float(G["adverse"].mean()), m10=float(G["m10"].mean()), lo=float(np.quantile(bs, .025)), hi=float(np.quantile(bs, .975))))
    R = pl.DataFrame(rows).sort("quoter", "quick"); R.write_parquet(S4 / "reentry.parquet")
    d = Q.group_by("quoter", "day").agg(pl.col("m10").mean()).pivot("quoter", index="day", values="m10"); v = (d["1s"] - d["instant"]).to_numpy(); bs = v[rng.integers(0, len(v), (2000, len(v)))].mean(1)
    print(A.filter((pl.col("L") == 50))); print(R); print("1s minus instant, mean of days", v.mean(), np.quantile(bs, [.025, .975]), "days 1s better", int((v > 0).sum()), "of", len(v))
else:
    rows = []
    for day in [p.stem for p in sorted(L21.STATE.glob("*.parquet")) if p.stem >= "2025-10-11"]:
        rg = np.random.default_rng(int(day.replace("-", ""))); halves = np.sort(rg.choice(48, 8, replace=False)); d0 = L21.ms(day)
        O = pl.read_parquet(L21.OUT / "s32" / "orders" / f"{day}.parquet", columns=["t", "side", "L", "S", "ioc_fill"]).filter((pl.col("L") == 50) & (pl.col("S") < 0.002) & (pl.col("ioc_fill") < 1 - 1e-9))
        O = O.filter(((pl.col("t") - d0) // MM.WIN).is_in(halves.tolist()))
        S = pl.read_parquet(L21.STATE / f"{day}.parquet", columns=["ts", "bid", "ask"]).sort("ts"); ts, bid, ask = (S[c].to_numpy() for c in ("ts", "bid", "ask"))
        for sd in (1, -1):
            for hh in halves:
                a0 = d0 + int(hh) * MM.WIN; g = O.filter((pl.col("side") == sd) & (pl.col("t") >= a0) & (pl.col("t") < a0 + MM.WIN))
                if not g.height: continue
                MM.wait_memory(); W = MM.Window(day, a0, a0 + MM.WIN, sd)
                for t in g["t"].to_list():
                    k = np.searchsorted(ts, t, side="right") - 1; p = int(ask[k]) if sd == 1 else -int(bid[k]); ta = t + 50; with_empty(W, p)
                    tf = W.fill(p, ta, ta + 120_000, "Q2", 1.0)
                    rows.append(dict(day=day, side=sd, t=t, wait=None if tf is None else (tf - ta) / 1000, m10=None if tf is None else float((W.mid[W.at(tf + 10_000)] - p) / abs(p) * 1e4), left=float((W.mid[W.at(ta + 120_000)] - p) / abs(p) * 1e4)))
                del W
        print(day, len(rows), flush=True)
    D = pl.DataFrame(rows); D.write_parquet(S4 / "rest.parquet")
    print("orders", D.height, "filled in 120 s", D["wait"].is_not_null().mean(), "median wait", D["wait"].median(), "10-s markout", D["m10"].mean(), "unfilled: mid above our price after 120 s, bp", D.filter(pl.col("wait").is_null())["left"].mean())
