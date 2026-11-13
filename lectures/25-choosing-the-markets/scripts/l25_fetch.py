"""Download daily adjusted prices and volume of the Lecture 25 ETFs from Yahoo Finance (free, via yfinance), one ticker at a time with retries
(Yahoo limits bulk requests). Writes PORTFOLIO_DATA/etf_daily.csv, columns (field, ticker); reruns fetch only the tickers still missing.
Closed ETFs (RSX, IRBO) have no data on Yahoo: the universe holds survivors only."""
import sys, time
from pathlib import Path
import pandas as pd, yfinance as yf
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l25 as L

if __name__ == "__main__":
    L.DATA.mkdir(parents=True, exist_ok=True); tickers = [t for v in L.UNIVERSE.values() for t in v]
    have = pd.read_csv(L.RAW, header=[0, 1], index_col=0, parse_dates=True) if L.RAW.exists() else pd.DataFrame()
    got = {t for t in tickers if ("Close", t) in have.columns and have[("Close", t)].notna().any()}
    todo = [t for t in tickers if t not in got]; parts = []; print("to fetch:", len(todo), flush=True)
    for t in todo:
        for _ in range(3):
            try:
                d = yf.download(t, start="1993-01-01", auto_adjust=True, actions=False, progress=False, group_by="column")
                if len(d):
                    d.columns = pd.MultiIndex.from_tuples([(c[0], t) for c in d.columns]); parts.append(d); print(t, len(d), flush=True); break
            except Exception as e: print(t, "error", e)
            time.sleep(3)
        else: print(t, "no data", flush=True)
        time.sleep(1.5)
    keep = have.loc[:, [c for c in have.columns if c[1] in got]] if len(have) else None
    out = pd.concat(([keep] if keep is not None else []) + parts, axis=1).sort_index(); out.to_csv(L.RAW); print("saved", out.shape)
