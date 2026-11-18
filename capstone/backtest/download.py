"""Download Deribit's history for the backtest: one-minute candles and hourly funding of BTC-PERPETUAL.

Public data, no account. Deribit returns at most 5,001 one-minute candles per request (checked live,
18 November 2026), so the history is fetched in chunks of 5,000 minutes and saved one month per file
(capstone/data/history/, git-ignored). A finished month is never fetched again: the download can be
stopped and resumed. Requests are spaced out so as not to strain the exchange.

Usage: python -m capstone.backtest.download --start 2019-01 --end 2026-10
"""
import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from capstone.security.redact import install_log_scrubbing

BASE = "https://www.deribit.com/api/v2"
OUT = Path(__file__).resolve().parents[1] / "data" / "history"
INSTRUMENT = "BTC-PERPETUAL"
MINUTE = 60_000
log = logging.getLogger("download")


def _get(method: str, params: dict) -> dict | list:
    for attempt in range(5):
        try:
            r = requests.get(f"{BASE}/{method}", params=params, timeout=20)
            body = r.json()
            if "error" in body:
                raise RuntimeError(f"{method}: {body['error'].get('message')}")
            return body["result"]
        except (requests.RequestException, ValueError) as e:
            wait = 2 ** attempt
            log.warning("%s failed (%s), retrying in %s s", method, type(e).__name__, wait)
            time.sleep(wait)
    raise RuntimeError(f"{method}: gave up after 5 attempts")


def month_bounds(ym: str) -> tuple[int, int]:
    y, m = map(int, ym.split("-"))
    a = datetime(y, m, 1, tzinfo=timezone.utc)
    b = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=timezone.utc)
    return int(a.timestamp() * 1000), int(b.timestamp() * 1000)


def candles_month(ym: str, pause: float = 0.15) -> pd.DataFrame:
    a, b = month_bounds(ym)
    rows = []
    t = a
    while t < b:
        e = min(t + 5000 * MINUTE, b) - MINUTE
        r = _get("public/get_tradingview_chart_data", {"instrument_name": INSTRUMENT, "resolution": "1",
                                                       "start_timestamp": t, "end_timestamp": e})
        if r.get("status") == "ok":
            rows.append(pd.DataFrame({"ts": r["ticks"], "open": r["open"], "high": r["high"], "low": r["low"],
                                      "close": r["close"], "volume": r["volume"]}))
        t = e + MINUTE
        time.sleep(pause)
    if not rows:
        return pd.DataFrame()
    df = pd.concat(rows).drop_duplicates("ts").sort_values("ts")
    return df[(df.ts >= a) & (df.ts < b)].reset_index(drop=True)


def funding_month(ym: str) -> pd.DataFrame:
    a, b = month_bounds(ym)
    r = _get("public/get_funding_rate_history", {"instrument_name": INSTRUMENT, "start_timestamp": a, "end_timestamp": b})
    return pd.DataFrame([{"ts": x["timestamp"], "interest_1h": x["interest_1h"]} for x in r]).drop_duplicates("ts")


def months(start: str, end: str):
    y, m = map(int, start.split("-")); ye, me = map(int, end.split("-"))
    while (y, m) <= (ye, me):
        yield f"{y:04d}-{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01"); ap.add_argument("--end", required=True)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for ym in months(a.start, a.end):
        fc, ff = OUT / f"candles_1m_{ym}.parquet", OUT / f"funding_1h_{ym}.parquet"
        if fc.exists() and ff.exists():
            continue
        t0 = time.time()
        c = candles_month(ym); f = funding_month(ym)
        c.to_parquet(fc, index=False); f.to_parquet(ff, index=False)
        log.info("%s: %s candles, %s funding hours, %.0f s", ym, len(c), len(f), time.time() - t0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    install_log_scrubbing()
    main()
