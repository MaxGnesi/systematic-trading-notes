"""Lecture 15 §4: download Binance's 5-minute futures metrics for BTCUSDT (open interest, long/short ratios), October 2021 to September 2026, one zip per day,
into data/raw/binance/metrics/BTCUSDT; then parse all into data/interim/l15_metrics.parquet. Files already downloaded are skipped."""
import io, sys, time, urllib.request, zipfile
from datetime import date, timedelta
from pathlib import Path
import polars as pl
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/15-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L15_RESULTS = tape.ROOT / "interim" / "l15"; L15_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L15_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L15_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

RAW = tape.ROOT / "raw" / "binance" / "metrics" / "BTCUSDT"; RAW.mkdir(parents=True, exist_ok=True)
URL = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{}.zip"
d, end, miss = date(2021, 10, 1), date(2026, 9, 30), []
while d <= end:
    f = RAW / f"{d}.zip"
    if not f.exists():
        for k in range(3):
            try:
                f.write_bytes(urllib.request.urlopen(URL.format(d), timeout=30).read()); break
            except Exception as e:
                if k == 2: miss.append(str(d)); print("missing", d, e, flush=True)
                time.sleep(2)
    d += timedelta(days=1)
frames = []
for f in sorted(RAW.glob("*.zip")):
    z = zipfile.ZipFile(f)
    frames.append(pl.read_csv(io.BytesIO(z.read(z.namelist()[0])), infer_schema_length=0))
M = (pl.concat(frames).select(pl.col("create_time").str.to_datetime("%Y-%m-%d %H:%M:%S").alias("time"),
                              *[pl.col(c).cast(pl.Float64, strict=False) for c in ("sum_open_interest", "sum_open_interest_value", "count_toptrader_long_short_ratio",
                                                                     "sum_toptrader_long_short_ratio", "count_long_short_ratio", "sum_taker_long_short_vol_ratio")])
     .unique("time").sort("time"))
M.write_parquet(tape.ROOT / "interim" / "l15_metrics.parquet")
gap = M["time"].diff().dt.total_minutes()
print("rows", M.height, M["time"].min(), M["time"].max(), "missing days", len(miss), "gaps > 5 min:", int((gap > 5).sum()), "largest gap, min:", gap.max())
