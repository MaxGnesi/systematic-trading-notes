"""Lecture 13 §6: out-of-sample test of the fixed-band imbalance clock, September to November 2025 (with the crash of 10 October 2025).
Every setting fixed before the run: horizon 30 minutes, constant from the burn-in (Oct–Dec 2021), window 28 days, no minimum length."""
import json, sys
from datetime import date
from pathlib import Path
import numpy as np, polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/13-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]   # this folder, tape.py, trading_models
import tape
L13_RESULTS = tape.ROOT / "interim" / "l13"; L13_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L13_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L13_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import bars, l13_s6 as m, l13_s6_horizon as hz
from l13_s6_stats import stats

K = json.loads((L13_RESULTS / "l13_s6_horizon_raw.json").read_text())["K"]["1800"]
hz.HS, hz.MS = (1800,), (0,)
a, z = date(2025, 9, 1), date(2025, 11, 30)
cnt = hz.run("oos", a, z, {1800: K})["band_H1800_m0"]
bpd = np.array(list(cnt.values()))
lo, hi = int(np.datetime64(a, "ms").astype(np.int64)), int(np.datetime64(z, "ms").astype(np.int64)) + 86_400_000
R = {"K": K, "band": dict(bpd_mean=round(float(bpd.mean()), 1), bpd_min=int(bpd.min()), bpd_max=int(bpd.max()), oct10=cnt["2025-10-10"], oct11=cnt["2025-10-11"],
                          **stats(pl.read_parquet(m.OUT / "oos_band_H1800_m0.parquet")))}
for k in ("dollar", "time"):
    b = pl.concat([pl.read_parquet(bars.bars_dir("BTCUSDT", k) / f"{ym}.parquet") for ym in ("2025-09", "2025-10", "2025-11")]).filter(pl.col("end_ms").is_between(lo, hi, closed="left")).sort("end_ms")
    d = b.group_by(pl.col("end_ms") // 86_400_000).len()["len"].to_numpy()
    R[k] = dict(bpd_mean=round(float(d.mean()), 1), bpd_min=int(d.min()), bpd_max=int(d.max()), **stats(b))
(L13_RESULTS / "l13_s6_oos.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
