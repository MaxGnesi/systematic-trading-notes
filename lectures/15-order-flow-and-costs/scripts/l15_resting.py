"""Lecture 15 §6: a resting order against a market order, five years of BTCUSDT one-minute bars. At every 7th minute a trader decides to buy (and, mirrored,
to sell). A: market order now, cost = taker fee + effective half-spread (§5, small orders). B: a resting order delta bp beyond the decision price, waiting up
to T minutes; filled when a later bar trades through it (strictly beyond: conservative) or reaches it (optimistic); if not filled by T, it chases with a
market order at the close of minute T. Cost against the decision price, in bp, signed so that positive = worse for the trader. Also: the return after a fill
(next 10 and 60 minutes, in the order's direction) and the move missed by unfilled orders. Decision moments tagged by the last hour's move (after a rise / a
fall / flat), volatility regime (§2 thirds) and whether a sweep of 10 bp or more happened in the 5 minutes before."""
import json, sys
from datetime import timedelta
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

D = tape.ROOT / "interim" / "tape" / "BTCUSDT"
TAKER, MAKER, HALF = 5.0, 2.0, 0.04                                            # fees (regular account) and the effective half-spread of a small order (§5)
DELTAS = [0, 2, 5, 10, 20]; TS = [1, 10, 60]; STEP = 7
m1 = pl.scan_parquet(sorted(D.glob("*/m1.parquet"))).select("time", "high", "low", "close").collect().sort("time")
t0 = m1["time"][0]; n = int((m1["time"][-1] - t0).total_seconds() // 60) + 1
g = (pl.DataFrame({"time": pl.datetime_range(t0, t0 + timedelta(minutes=n - 1), "1m", eager=True)}).join(m1, on="time", how="left").sort("time")
     .with_columns(pl.col("close").forward_fill()).with_columns(pl.col("high").fill_null(pl.col("close")), pl.col("low").fill_null(pl.col("close"))))
c, hi, lo = g["close"].to_numpy(), g["high"].to_numpy(), g["low"].to_numpy(); lc = np.log(c)
r1 = np.r_[0.0, np.diff(lc)]; c2 = np.r_[0.0, np.cumsum(r1 ** 2)]
rv60 = np.r_[np.full(60, np.nan), c2[60:] - c2[:-60]][:n]; med = pl.Series(rv60).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
reg = rv60 / med; q1, q2 = np.nanquantile(reg[28 * 1440:], [1 / 3, 2 / 3])
dvar = pl.Series(r1 ** 2).rolling_sum(1440).rolling_median(28 * 1440, min_samples=7 * 1440).shift(1).to_numpy()
t0ms = int(np.datetime64(t0, "ms").astype(np.int64))
SW = pl.read_parquet(tape.ROOT / "interim" / "l15_sweeps.parquet", columns=["time_ms", "move_bp"]).filter(pl.col("move_bp") >= 10)
swm = np.unique((SW["time_ms"].to_numpy() - t0ms) // 60_000)

I = np.arange(28 * 1440, n - 130, STEP)                                        # decision at the close of minute i
I = I[np.isfinite(reg[I]) & np.isfinite(dvar[I])]
p0 = c[I]; DAY = (I // 1440) - (I // 1440).min()
past = (lc[I] - lc[I - 60]) / np.sqrt(dvar[I] / 24)                            # the last hour's move over its typical size
ctx_move = np.where(past > 1, "after a rise", np.where(past < -1, "after a fall", "flat"))
ctx_vol = np.where(reg[I] < q1, "calm", np.where(reg[I] < q2, "normal", "volatile"))
k = np.searchsorted(swm, I, side="right"); ctx_sweep = (k > 0) & (I - swm[np.maximum(k - 1, 0)] < 5)
# running extremes after the decision: lowest low and highest high over minutes i+1 .. i+T
W = max(TS) + 70
LO = np.full((len(I), W), np.nan); HI = np.full((len(I), W), np.nan); CL = np.full((len(I), W), np.nan)
for j in range(W):
    LO[:, j] = lo[I + 1 + j]; HI[:, j] = hi[I + 1 + j]; CL[:, j] = c[I + 1 + j]

rows = []
for side in (1, -1):                                                          # 1: buy (limit below), -1: sell (limit above)
    for delta in DELTAS:
        lim = p0 * (1 - side * delta / 1e4) - side * 0.1                       # at least one tick ($0.10) better than the last trade: a genuine resting order
        for rule in ("through", "touch"):
            if side == 1: hit = (LO < lim[:, None]) if rule == "through" else (LO <= lim[:, None])
            else: hit = (HI > lim[:, None]) if rule == "through" else (HI >= lim[:, None])
            first = np.where(hit.any(axis=1), hit.argmax(axis=1), 10 ** 6)
            for T in TS:
                filled = first < T
                chase = side * (np.log(CL[:, T - 1] / p0)) * 1e4 + TAKER + HALF            # not filled: market order at the close of minute T
                cost_b = np.where(filled, side * np.log(lim / p0) * 1e4 + MAKER, chase)
                fi = np.minimum(first, W - 61)                                           # return after the fill, in the order's direction, from the limit price
                after10 = side * np.log(CL[np.arange(len(I)), np.minimum(fi + 10, W - 1)] / lim) * 1e4
                after60 = side * np.log(CL[np.arange(len(I)), np.minimum(fi + 60, W - 1)] / lim) * 1e4
                missed = side * np.log(CL[:, T - 1] / p0) * 1e4                           # how far the price ran away from an unfilled order
                # both choices judged one hour after the decision: a market order holds the position from the start; a resting order that is never filled
                # holds nothing (no chase). Positive = the resting order did worse than the market order.
                mkt60 = side * np.log(CL[:, 59] / p0) * 1e4 - (TAKER + HALF)
                nochase = mkt60 - np.where(filled, side * np.log(CL[:, 59] / lim) * 1e4 - MAKER, 0.0)
                diff = cost_b - (TAKER + HALF)
                mv60 = side * np.log(CL[:, 59] / p0) * 1e4                                # the move in the order's direction, decision to one hour later
                for cm in ("all", "after a rise", "after a fall", "flat"):
                    for cv in ("all", "calm", "normal", "volatile"):
                        for cs in ("all", "after sweep"):
                            # 'after a rise' for a buy = buying into strength (trend entry); mirrored for a sell
                            mk = np.ones(len(I), bool)
                            if cm == "after a rise": mk &= (ctx_move == ("after a rise" if side == 1 else "after a fall"))
                            elif cm == "after a fall": mk &= (ctx_move == ("after a fall" if side == 1 else "after a rise"))
                            elif cm == "flat": mk &= (ctx_move == "flat")
                            if cv != "all": mk &= (ctx_vol == cv)
                            if cs == "after sweep": mk &= ctx_sweep
                            if cv != "all" and cs != "all": continue
                            if cm != "all" and cs != "all": continue
                            f = filled[mk]
                            tt = {}
                            for nm, x in (("t_chase", diff), ("t_nochase", nochase)):           # days as clusters
                                dd = DAY[mk]; s_ = np.bincount(dd, x[mk]); k_ = np.bincount(dd); ok = k_ > 0; m_ = s_[ok] / k_[ok]
                                tt[nm] = float(m_.mean() / (m_.std(ddof=1) / np.sqrt(len(m_))))
                            rows.append(dict(side=side, delta=delta, rule=rule, T=T, move=cm, vol=cv, sweep=cs, n=int(mk.sum()), fill=float(f.mean()),
                                             cost_b=float(cost_b[mk].mean()), cost_a=TAKER + HALF,
                                             after10_filled=float(after10[mk][f].mean()) if f.any() else None, after60_filled=float(after60[mk][f].mean()) if f.any() else None,
                                             missed=float(missed[mk][~f].mean()) if (~f).any() else None, nochase_vs_market=float(nochase[mk].mean()), **tt,
                                             m60_filled=float(mv60[mk][f].mean()) if f.any() else None, m60_unfilled=float(mv60[mk][~f].mean()) if (~f).any() else None))
R = pl.DataFrame(rows)
# average the buy and the mirrored sell (drift cancels)
A = (R.group_by("delta", "rule", "T", "move", "vol", "sweep").agg(pl.col("n").sum(), *[pl.col(x).mean() for x in ("fill", "cost_b", "cost_a", "after10_filled", "after60_filled", "missed", "nochase_vs_market", "t_chase", "t_nochase", "m60_filled", "m60_unfilled")])
     .with_columns((pl.col("cost_b") - pl.col("cost_a")).alias("b_minus_a")).sort("move", "vol", "sweep", "rule", "T", "delta"))
A.write_parquet(tape.ROOT / "interim" / "l15_resting.parquet")
(L15_RESULTS / "l15_resting.json").write_text(A.to_pandas().to_json(orient="records", indent=1))
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(20); pl.Config.set_tbl_width_chars(250); pl.Config.set_ascii_tables(True)
print("decisions per side:", len(I))
print(A.filter((pl.col("rule") == "through") & (pl.col("vol") == "all") & (pl.col("sweep") == "all"))
      .select("move", "T", "delta", "fill", "b_minus_a", "t_chase", "m60_filled", "m60_unfilled").with_columns(pl.col(pl.Float64).round(2)))
