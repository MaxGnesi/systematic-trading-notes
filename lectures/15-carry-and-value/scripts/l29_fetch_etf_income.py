"""Lecture 15: download, once, the distributions and unadjusted closes of Lecture 11's bond and credit ETFs (Yahoo, free) into
data/raw/l29_long/etf_income/<ticker>_{div,close}.csv. One fund at a time with pauses (Yahoo refuses rapid repeated requests); funds already
saved are skipped, so the script can be rerun until all are in."""
import time
from pathlib import Path
import pandas as pd, yfinance as yf
OUT = Path(__file__).resolve().parents[3].parent / "data" / "raw" / "l29_long" / "etf_income"; OUT.mkdir(parents=True, exist_ok=True)
FUNDS = ["SHY", "IEI", "IEF", "TLT", "TIP", "BWX", "BNDX", "LQD", "HYG", "EMB", "MBB", "BKLN"]

for t in FUNDS:
    for kind in ("div", "close"):
        f = OUT / f"{t}_{kind}.csv"
        if f.exists(): continue
        for attempt in range(6):
            try:
                if kind == "div": x = yf.Ticker(t).dividends
                else: x = yf.download(t, start="2002-01-01", end="2026-11-14", auto_adjust=False, progress=False)["Close"]
                if x is not None and len(x):
                    x.index = pd.to_datetime(x.index).tz_localize(None); x.to_csv(f); print(t, kind, len(x), flush=True); break
            except Exception as e:
                print(t, kind, "retry", attempt, type(e).__name__, flush=True)
            time.sleep(20 * (attempt + 1))
        time.sleep(8)
print("done:", sorted(p.name for p in OUT.glob("*.csv")))
