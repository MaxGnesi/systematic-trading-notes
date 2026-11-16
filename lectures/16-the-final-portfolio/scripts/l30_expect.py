"""Lecture 16: the realistic expectation (plan, measure 5). The rule's backtest Sharpe ratio in each period, cut one source at a time:
measurement (monthly Sharpe ratios run above daily ones: the ratio of trend's daily to monthly Sharpe ratio in the same years), costs (10 bp per
trade on carry instead of 5), and the period (the average across 1990-2005, 2006-2022 and 2013-2026, rather than the best one).
Selection: the 1990-2005 test involved no choice among carry versions; in-sample the deflated Sharpe ratio (Lecture 15: 0.90) is reported.
Output: results/expect.json."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); import l30_data as D
import l29_combined as M, l29_bonds_g10 as G, l29 as L
RES = Path(os.environ.get("L30_RESULTS", HERE.parent / "results"))

if __name__ == "__main__":
    T = json.loads((RES / "test.json").read_text(encoding="utf-8"))
    import l28_confirm as CF
    d90 = CF.portfolio(CF.returns()).loc["1990-01-01":"2005-12-31"]
    d06 = pd.read_parquet(L.RAW / "l29_trend_futures_fixed.parquet")["ret"].loc["2006-01-01":"2022-10-31"]
    daily = lambda r: float(r.mean() / r.std() * np.sqrt(252))
    ratio = {"1990-2005": daily(d90) / G.sharpe_m(M.compound(d90)), "2006-2022": daily(d06) / G.sharpe_m(M.compound(d06))}
    rows = {}
    for pn in ("1990-2005", "2006-2022"):
        bt = T[pn]["rule: trend + carry"]["sharpe"]; c10 = T["costs"]["10 bp"][pn]
        rows[pn] = dict(backtest=bt, daily_equivalent=bt * ratio[pn], plus_costs_10bp=c10 * ratio[pn])
    r_avg = float(np.mean(list(ratio.values())))
    rows["2013-2026"] = dict(backtest=0.45, daily_equivalent=0.45 * r_avg, plus_costs_10bp=None)   # Lecture 15 §6.5, ETF trend + carry
    final = [rows["1990-2005"]["plus_costs_10bp"], rows["2006-2022"]["plus_costs_10bp"], rows["2013-2026"]["daily_equivalent"]]
    out = dict(daily_to_monthly=ratio, rows=rows, average_after_haircuts=float(np.mean(final)), range_after_haircuts=[float(min(final)), float(max(final))])
    print(json.dumps(out, indent=1)); (RES / "expect.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
