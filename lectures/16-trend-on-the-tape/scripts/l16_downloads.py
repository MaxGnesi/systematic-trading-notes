"""Lecture 16: download what the tape of Lecture 12 does not contain. Binance's premium index of BTCUSDT (perpetual against the spot index) as 1-hour and
8-hour candles, and spot BTCUSDT daily candles, October 2021 to September 2026, monthly files from data.binance.vision. Files already present are skipped."""
import sys, time, urllib.request
from pathlib import Path
import os, sys
if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # tables print on any console; Jupyter handles its own
HERE = Path(__file__).resolve().parent                                     # lectures/16-.../scripts
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "13-bars-not-cut-by-time" / "scripts"), str(HERE.parents[1] / "12-tick-data-the-tape"), str(HERE.parents[2])]
import tape
L16_RESULTS = tape.ROOT / "interim" / "l16"; L16_RESULTS.mkdir(parents=True, exist_ok=True)          # results: in the data folder, never committed
FIG = Path(os.environ.get("L16_FIG", HERE.parent / "figures")); FIG.mkdir(parents=True, exist_ok=True)
PREFIX = os.environ.get("L16_PREFIX", "nb_")                               # "nb_": the lecture's own figures are never overwritten
import tape

MONTHS = [f"{y}-{m:02d}" for y in range(2021, 2027) for m in range(1, 13) if "2021-09" <= f"{y}-{m:02d}" <= "2026-09"]
JOBS = [("futures/um/monthly/premiumIndexKlines/BTCUSDT/1h", "1h", tape.ROOT / "raw" / "binance" / "um" / "premiumIndexKlines" / "BTCUSDT"),
        ("futures/um/monthly/premiumIndexKlines/BTCUSDT/8h", "8h", tape.ROOT / "raw" / "binance" / "um" / "premiumIndexKlines" / "BTCUSDT_8h"),
        ("spot/monthly/klines/BTCUSDT/1d", "1d", tape.ROOT / "raw" / "binance" / "spot_klines_1d" / "BTCUSDT")]
for path, iv, folder in JOBS:
    folder.mkdir(parents=True, exist_ok=True); got = 0
    for ym in MONTHS:
        if path.startswith("spot") and ym < "2021-10": continue
        f = folder / f"BTCUSDT-{iv}-{ym}.zip"
        if f.exists(): continue
        for k in range(3):
            try:
                f.write_bytes(urllib.request.urlopen(f"https://data.binance.vision/data/{path}/BTCUSDT-{iv}-{ym}.zip", timeout=60).read()); got += 1; break
            except Exception as e:
                if k == 2: print("missing", path, ym, e)
                time.sleep(2)
    print(f"{path}: {len(list(folder.glob('*.zip')))} files ({got} new)")
