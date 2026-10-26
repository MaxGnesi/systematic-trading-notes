"""Lecture 15 §3: sweeps and recovery.
Step 1 (extract): every aggressive order (trades in the same millisecond on the same side) whose fills move the price by at least 5 bp from the first
to the last fill; with the price just before it, its size, the prices it took, and the last traded price 10 s, 1 min, 10 min and 1 h after it.
Saved to data/interim/l15_sweeps.parquet. Step 2 (in l15_sweeps_matrix.py): recovery by trend relation x volatility regime."""
import sys, time
from datetime import datetime, timezone
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

SYM = "BTCUSDT"; D = tape.ROOT / "interim" / "tape" / SYM; OUT = tape.ROOT / "interim" / "l15_sweeps.parquet"; PART = tape.ROOT / "interim" / "l15_sweeps_months"
MIN_BP = 5.0; HOR = {"10s": 10_000, "1m": 60_000, "10m": 600_000, "1h": 3_600_000}


def day_trades(d0, extra_ms):
    a = int(datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc).timestamp() * 1000)
    lf = [tape.source(SYM, d0.strftime("%Y-%m"))]
    nxt = datetime.fromtimestamp((a + 86_400_000) / 1000, timezone.utc)
    if nxt.strftime("%Y-%m") != d0.strftime("%Y-%m") and Path(tape.source(SYM, nxt.strftime("%Y-%m"))).exists():
        lf.append(tape.source(SYM, nxt.strftime("%Y-%m")))                      # the hour after midnight may be in the next month's file
    return a, (pl.scan_parquet(lf).filter(pl.col("transact_time").is_between(a - 1000, a + 86_400_000 + extra_ms, closed="left"))
                 .select("transact_time", "price", "quantity", "is_buyer_maker").collect().sort("transact_time"))


if __name__ == "__main__":
    days = pl.scan_parquet(sorted(D.glob("*/rv_days.parquet"))).select("day").collect()["day"].to_list()
    PART.mkdir(parents=True, exist_ok=True); t0 = time.time()
    months = sorted({d.strftime("%Y-%m") for d in days})
    for ym in months:
        f = PART / f"{ym}.parquet"
        if f.exists(): continue                                            # done in an earlier run
        rows = []
        for d0 in [d for d in days if d.strftime("%Y-%m") == ym]:
            tape.wait_for_memory(1.5)
            a, t = day_trades(d0, HOR["1h"])
            if t.height == 0: continue
            ts = t["transact_time"].to_numpy(); p = t["price"].to_numpy(); q = t["quantity"].to_numpy(); sell = t["is_buyer_maker"].to_numpy()
            new = np.r_[True, (ts[1:] != ts[:-1]) | (sell[1:] != sell[:-1])]; start = np.nonzero(new)[0]; end = np.r_[start[1:] - 1, len(ts) - 1]
            first, last = p[start], p[end]; move = np.abs(np.log(last / first)) * 1e4
            k = np.nonzero((move >= MIN_BP) & (ts[start] >= a) & (ts[start] < a + 86_400_000) & (start > 0))[0]
            if len(k) == 0: continue
            s_, e = start[k], end[k]
            usd = np.add.reduceat(p * q, start)[k]
            out = dict(time_ms=ts[s_], side=np.where(sell[s_], -1, 1).astype(np.int8), p_before=p[s_ - 1], p_first=first[k], p_last=last[k], move_bp=move[k], usd=usd,
                       prices=np.array([len(np.unique(p[x:y + 1])) for x, y in zip(s_, e)]))
            for lab, h in HOR.items():
                j = np.searchsorted(ts, ts[s_] + h, side="right") - 1
                out[f"p_{lab}"] = np.where(ts[-1] >= ts[s_] + h, p[j], np.nan)
            rows.append(pl.DataFrame(out))
        if rows: pl.concat(rows).write_parquet(f)
        print(ym, sum(r.height for r in rows), "sweeps", f"{time.time() - t0:.0f}s", tape.peak_private_gb(), "GB", flush=True)
    S = pl.concat([pl.read_parquet(f) for f in sorted(PART.glob("*.parquet"))]); S.write_parquet(OUT)
    print("sweeps", S.height, ">=10 bp:", S.filter(pl.col("move_bp") >= 10).height, ">=20 bp:", S.filter(pl.col("move_bp") >= 20).height)
