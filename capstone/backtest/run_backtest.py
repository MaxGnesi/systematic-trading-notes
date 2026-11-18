"""Run the strategy and its rivals on Deribit's history (Lecture 24 §10; hypotheses fixed 18 Nov 2026).

Variants, all on the same hours and the same random delays:
  base            the strategy as fixed: speeds 2 and 7 days, 5-sigma take profit, taker orders
  speed_2d        rival 1: the 2-day speed alone
  speed_7d        rival 1: the 7-day speed alone
  no_tp           rival 2: without the take profit
  patient         rival 3: post-only at the decision price, market order after a minute if not filled
  window_10..40   rival 4: trade after one minute if the price moved our way by 10-40 bp, else after two
  check_phase_00  robustness check added after the hypotheses (18 Nov 2026, labelled as such): the same
                  strategy deciding at round hours (:00) instead of :23, to see whether the phase matters
Reported: Sharpe ratio, return, volatility, worst month, monthly skew, drawdown, fees and funding, by year;
for each rival, the difference against base with a 90% band from a block bootstrap of months.
Output: lectures/24-a-live-trend-bot/results/backtest.json. Usage: python -m capstone.backtest.run_backtest
"""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from capstone.backtest import engine
from capstone.security.redact import install_log_scrubbing
from capstone.strategies.trend import params as P

OUT = Path(__file__).resolve().parents[2] / "lectures" / "24-a-live-trend-bot" / "results" / "backtest.json"
log = logging.getLogger("run_backtest")


def monthly(o: pd.DataFrame) -> pd.Series:
    eq = o["equity"]; live = o["position"].abs().cumsum() > 0
    return eq[live].resample("ME").last().pct_change().dropna()


def band(a: pd.Series, b: pd.Series, stat, n: int = 2000, block: int = 3, seed: int = 1):
    """90% band of stat(a) - stat(b), resampling blocks of `block` months, the same months for both."""
    j = a.index.intersection(b.index); a, b = a[j].to_numpy(), b[j].to_numpy()
    rng = np.random.default_rng(seed); k = len(a); out = []
    for _ in range(n):
        starts = rng.integers(0, k - block + 1, size=k // block + 1)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:k]
        out.append(stat(a[idx]) - stat(b[idx]))
    return float(stat(a) - stat(b)), [float(np.percentile(out, 5)), float(np.percentile(out, 95))]


def sharpe_m(x):
    return x.mean() / x.std() * np.sqrt(12) if x.std() > 0 else 0.0


def skew_m(x):
    return float(pd.Series(x).skew())


def by_year(o: pd.DataFrame) -> dict:
    r = o["equity"].pct_change()
    r = r[(o["position"].abs().cumsum() > 0)]
    return {str(y): round(float(g.mean() / g.std() * np.sqrt(24 * 365)), 2) for y, g in r.groupby(r.index.year) if g.std() > 0}


def main():
    p = P.load()
    c, f = engine.load_minutes()
    h = engine.hourly_frame(c, f, p.decision_minute)
    log.info("history: %s to %s, %s decision hours", h.index[0], h.index[-1], len(h))
    variants = {"base": (p, "base", 0), "speed_2d": (p.replace(fast_spans_days=(2.0,)), "base", 0),
                "speed_7d": (p.replace(fast_spans_days=(7.0,)), "base", 0), "no_tp": (p.replace(take_profit=False), "base", 0),
                "patient": (p, "patient", 0)}
    for x in (10, 20, 30, 40):
        variants[f"window_{x}"] = (p, "window", x)
    variants["check_phase_00"] = (p.replace(decision_minute=0), "base", 0)
    frames = {p.decision_minute: h, 0: engine.hourly_frame(c, f, 0)}
    res, mon = {}, {}
    for name, (pp, rival, x) in variants.items():
        r = engine.run(frames[pp.decision_minute], pp, rival=rival, x_bp=x)
        mon[name] = monthly(r.hourly)
        extra = {}
        if rival in ("patient", "window"):
            traded = r.hourly["traded"] != 0
            extra["share_of_trades_flagged"] = round(float(r.hourly.loc[traded, "flag"].mean()), 4)
        tp_cols = [c for c in r.hourly if c.startswith("tp")]
        if tp_cols:
            extra["share_of_hours_tp_flat"] = {c: round(float(r.hourly[c].astype(float).mean()), 4) for c in tp_cols}
        res[name] = {**{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.stats.items()}, "sharpe_by_year": by_year(r.hourly), **extra}
        log.info("%-10s Sharpe %.2f  return %.1f%%  vol %.1f%%  worst month %.1f%%  skew %.2f  fees %.4f BTC/yr", name, r.stats["sharpe"],
                 100 * r.stats["ann_return"], 100 * r.stats["ann_vol"], 100 * r.stats["worst_month"], r.stats["month_skew"], r.stats["fees_per_year"])
    diffs = {}
    for name in res:
        if name == "base":
            continue
        d_s, b_s = band(mon[name], mon["base"], sharpe_m)
        d_k, b_k = band(mon[name], mon["base"], skew_m)
        diffs[name] = {"sharpe_minus_base": round(d_s, 3), "band90": [round(v, 3) for v in b_s],
                       "skew_minus_base": round(d_k, 3), "skew_band90": [round(v, 3) for v in b_k]}
    OUT.write_text(json.dumps({"history": [str(h.index[0]), str(h.index[-1])], "hours": len(h), "variants": res,
                               "differences_vs_base_monthly": diffs}, indent=1), encoding="utf-8")
    log.info("written %s", OUT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_log_scrubbing()
    main()
