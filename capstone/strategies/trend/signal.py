"""The trend strategy's decisions, from hourly prices (Lecture 24 §8). Used by the backtest and the live bot
alike, so both decide in exactly the same way.

For each speed (fast span f hours, slow span 4f):
  1. raw     = (EWMA_fast(price) - EWMA_slow(price)) / volatility of hourly price changes
  2. scaled  = raw / its average absolute size so far, so that 1 is a typical signal (no cap)
  3. take profit: the open gain since this speed's signal last changed sign, sum of sign x hourly return,
     in units of the speed's risk at entry (hourly volatility at entry x sqrt(f hours)); once it reaches
     `tp_sigmas`, the speed is flat until its sign changes (Lecture 8 §4.8)
Then: blend = average over the speeds; target position = blend x target_vol x equity / annual volatility,
with the volatility of hourly returns over the past `vol_window_days`. Only information up to each hour
is used: every rolling quantity is computed on the past and shifted where needed.
"""
import numpy as np
import pandas as pd

from capstone.strategies.trend.params import Params

HOURS_PER_YEAR = 24 * 365


def speed_forecast(price: pd.Series, fast_h: float, p: Params, hourly_vol: pd.Series) -> pd.DataFrame:
    ret = price.pct_change()
    dp_vol = price.diff().ewm(span=p.dp_vol_span_days * 24, min_periods=24 * 7).std()
    raw = (price.ewm(span=fast_h).mean() - price.ewm(span=fast_h * p.slow_over_fast).mean()) / dp_vol
    scale = raw.abs().expanding(min_periods=24 * 30).mean()
    f = raw / scale
    sign = np.sign(f).fillna(0)
    out = pd.DataFrame({"forecast": f, "sign": sign})
    if not p.take_profit:
        out["forecast_tp"] = f
        out["tp_flat"] = False
        return out
    out["forecast_tp"], out["tp_flat"] = take_profit(f.to_numpy(), ret.to_numpy(), hourly_vol.to_numpy(), fast_h, p.tp_sigmas)
    return out


def take_profit(f, ret, hourly_vol, fast_h: float, sigmas: float):
    """Per hour t, using only data up to t: the speed's forecast, or 0 once the open gain of its current
    sign has reached `sigmas` units of risk. The gain restarts, and the speed trades again, when the sign
    of the forecast changes. Plain loop on purpose: easy to read and to check by hand."""
    n = len(f)
    out, flat_out = np.zeros(n), np.zeros(n, dtype=bool)
    prev_sign, gain, unit, flat = 0.0, 0.0, np.nan, False
    for t in range(n):
        if np.isnan(f[t]):
            out[t] = np.nan; continue
        sign = np.sign(f[t])
        if sign != prev_sign:                        # a new trade of this speed starts here
            gain, unit, flat = 0.0, hourly_vol[t] * np.sqrt(fast_h), False
        elif not np.isnan(ret[t]):
            gain += prev_sign * ret[t]               # what the signal earned over the last hour
            if unit > 0 and gain / unit >= sigmas - 1e-9:       # tolerance: float sums must not delay it by an hour
                flat = True
        out[t] = 0.0 if flat else f[t]
        flat_out[t] = flat
        prev_sign = sign
    return out, flat_out


def targets(price: pd.Series, p: Params) -> pd.DataFrame:
    """Per hour: each speed's forecast after the take profit, the blend, the annual volatility, and the
    target position as a multiple of equity (multiply by equity in USD for the USD amount)."""
    ret = price.pct_change()
    w = int(p.vol_window_days * 24)
    hourly_vol = ret.rolling(w, min_periods=w // 2).std()
    cols = {}
    for days in p.fast_spans_days:
        s = speed_forecast(price, days * 24, p, hourly_vol)
        cols[f"f{days:g}d"] = s["forecast_tp"]
        cols[f"tp{days:g}d"] = s["tp_flat"]
    df = pd.DataFrame(cols)
    fc = df[[c for c in df if c.startswith("f")]]
    df["blend"] = fc.mean(axis=1)
    df["ann_vol"] = hourly_vol * np.sqrt(HOURS_PER_YEAR)
    df["target_x_equity"] = df["blend"] * p.target_vol / df["ann_vol"]
    return df
