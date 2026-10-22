"""Lecture 13 §6: statistics of the imbalance clocks from l13_s6.py, with dollar and time bars on the same windows."""
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
import bars, l13_s6 as m

def stats(b):
    r = np.diff(np.log(b["close"].to_numpy())); z = (r - r.mean()) / r.std(); ac = lambda x: float(np.corrcoef(x[:-1], x[1:])[0, 1])
    e = b["end_ms"].to_numpy(); dur = np.diff(e) / 60000
    fl = (b["signed_usd"] / b["usd"]).to_numpy()[1:]
    return dict(bars=len(r), kurt=round(float(np.mean(z**4) - 3), 1), beyond4=round(float((np.abs(z) > 4).mean() * 1e4), 1),
                ac1_ret=round(ac(r), 3), ac1_abs=round(ac(np.abs(r)), 3), usd_cv=round(float(b["usd"].std() / b["usd"].mean()), 2),
                min_p10=round(float(np.quantile(dur, .1)), 2), min_med=round(float(np.median(dur)), 1), min_p90=round(float(np.quantile(dur, .9)), 1),
                min_max=round(float(dur.max()), 0), flow_ret_corr=round(float(np.corrcoef(fl, r)[0, 1]), 2))

if __name__ == "__main__":
    RAW = json.loads((L13_RESULTS / "l13_s6_raw.json").read_text())
    out = {}
    for w, (a, z) in m.WINDOWS.items():
        lo = int(np.datetime64(a, "ms").astype(np.int64)); hi = int(np.datetime64(z, "ms").astype(np.int64)) + 86_400_000
        for k in ("dollar", "time"):
            b = pl.concat([pl.read_parquet(bars.bars_dir("BTCUSDT", k) / f"{ym}.parquet") for ym in sorted({d.strftime('%Y-%m') for d in pl.date_range(a, z, eager=True)})]).filter(pl.col("end_ms").is_between(lo, hi, closed="left")).sort("end_ms")
            bpd = b.group_by((pl.col("end_ms") // 86_400_000)).len()["len"].to_numpy()
            out[f"{w}|{k}"] = dict(bpd_mean=round(float(bpd.mean()), 1), bpd_cv=round(float(bpd.std() / bpd.mean()), 2), bpd_max=int(bpd.max()), **stats(b))
        for name, v in RAW[w].items():
            if name.startswith("_"): continue
            bpd = np.array(list(v["bars_per_day"].values())); f = m.OUT / f"{w}_{name}.parquet"
            row = dict(bpd_mean=round(float(bpd.mean()), 1), bpd_cv=round(float(bpd.std() / bpd.mean()), 2) if bpd.mean() else None, bpd_max=int(bpd.max()), bpd_min=int(bpd.min()))
            if f.exists() and bpd.max() <= m.MAX_STORE: row.update(stats(pl.read_parquet(f)))
            out[f"{w}|{name}"] = row
    (L13_RESULTS / "l13_s6.json").write_text(json.dumps(out, indent=0))
    for key in out:
        if "ldp" in key or "dollar" in key or "time" in key or "K1.0_W28" in key: print(key, out[key])
