"""Lecture 26: daily net returns of the 36 trend streams for every ETF of the given classes (default all), one parquet per market in L26_OUT/streams,
plus turnover. Signals and profits on excess returns over the 3-month bill rate. Usage: python l26_streams.py [Class ...]. Prints a first picture per class: Sharpe ratio after costs by speed, median over markets."""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); import l26 as L

if __name__ == "__main__":
    classes = sys.argv[1:] or list(L.CLASSES); close, high, low, dv, rf = L.load_daily(); D = L.OUT / "streams"; D.mkdir(exist_ok=True)
    for k in classes:
        names = [t for t in close.columns if L.CLASS[t] == k]; t0 = time.time(); sh = {}
        for t in names:
            c = close[t].dropna(); x, xh, xl = L.excess(c, high[t].reindex(c.index), low[t].reindex(c.index), rf); S = L.stream_returns(x, xh, xl); S.to_parquet(D / f"{t}.parquet")
            sh[t] = L.net(S)[L.START:].apply(L.sharpe)
        T = pd.DataFrame(sh).T; print(f"\n{k}: {len(names)} markets, {time.time() - t0:.0f} s; Sharpe after 5 bp, 2007 on, median over markets:")
        M = T.median().to_numpy().reshape(len(L.RULES), len(L.SPEEDS))
        print(pd.DataFrame(M, index=L.RULES, columns=L.SPEEDS).round(2).to_string())
