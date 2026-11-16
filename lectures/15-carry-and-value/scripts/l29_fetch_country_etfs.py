"""Lecture 15: download, once, the iShares MSCI country ETFs (Yahoo, free) for the cross-country equity group: adjusted close (total return),
unadjusted close (price only) and distributions, into data/raw/l29_long/country_etfs/<ticker>_{adj,close,div}.csv. One fund at a time with
pauses; funds already saved are skipped, so the script can be rerun until all are in. SPY stands for the US."""
import time
from pathlib import Path
import pandas as pd, yfinance as yf
OUT = Path(__file__).resolve().parents[3].parent / "data" / "raw" / "l29_long" / "country_etfs"; OUT.mkdir(parents=True, exist_ok=True)
FUNDS = {"SPY": "US", "EWJ": "JP", "EWG": "DE", "EWU": "GB", "EWC": "CA", "EWA": "AU", "EWL": "CH", "EWQ": "FR", "EWI": "IT", "EWP": "ES",
         "EWD": "SE", "EWN": "NL", "EWH": "HK", "EWK": "BE", "EWO": "AT"}

if __name__ == "__main__":
    for t in FUNDS:
        if all((OUT / f"{t}_{k}.csv").exists() for k in ("adj", "close", "div")): continue
        for attempt in range(6):
            try:
                px = yf.download(t, start="1993-01-01", end="2026-11-14", auto_adjust=False, progress=False)
                dv = yf.Ticker(t).dividends
                if px is not None and len(px) and dv is not None and len(dv):
                    for k, x in (("adj", px["Adj Close"]), ("close", px["Close"]), ("div", dv)):
                        x = x.squeeze() if hasattr(x, "squeeze") else x; x.index = pd.to_datetime(x.index).tz_localize(None); x.to_csv(OUT / f"{t}_{k}.csv")
                    print(t, len(px), len(dv), flush=True); break
            except Exception as e:
                print(t, "retry", attempt, type(e).__name__, flush=True)
            time.sleep(20 * (attempt + 1))
        time.sleep(8)
    print("done:", sorted({p.name.split("_")[0] for p in OUT.glob("*_adj.csv")}))
