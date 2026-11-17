"""Bybit's public REST API: one question, one answer (Lecture 24 §2).

Public endpoints need no key: anyone can ask for instrument details, the server time or past candles.
Every answer has the same envelope, {"retCode": 0, "retMsg": "OK", "result": ...}; a retCode other than
0 is an error and is raised, never ignored.

Verified live (17 November 2026): BTCUSDT on the linear category, tick 0.10, minimum and step 0.001 BTC,
the same on the testnet.
"""
from dataclasses import dataclass
from decimal import Decimal

import requests

BASE = {"mainnet": "https://api.bybit.com", "testnet": "https://api-testnet.bybit.com"}
TIMEOUT = 10


class BybitError(Exception):
    pass


def _get(env: str, path: str, params: dict) -> dict:
    r = requests.get(BASE[env] + path, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    body = r.json()
    if body.get("retCode") != 0:
        raise BybitError(f"{path}: retCode {body.get('retCode')} {body.get('retMsg')}")
    return body["result"]


@dataclass(frozen=True)
class Instrument:
    """What the exchange means by price and quantity for one contract: the connector's job to know."""
    symbol: str
    status: str
    tick_size: Decimal       # prices must be multiples of this
    qty_step: Decimal        # quantities, in BTC for a linear contract, must be multiples of this
    min_qty: Decimal
    min_notional: Decimal    # smallest order value, in USDT

    def round_price(self, price: Decimal) -> Decimal:
        return (price / self.tick_size).to_integral_value() * self.tick_size

    def round_qty_down(self, qty: Decimal) -> Decimal:
        return (qty / self.qty_step).to_integral_value(rounding="ROUND_DOWN") * self.qty_step


def instrument(env: str, symbol: str, category: str = "linear") -> Instrument:
    i = _get(env, "/v5/market/instruments-info", {"category": category, "symbol": symbol})["list"][0]
    pf, lf = i["priceFilter"], i["lotSizeFilter"]
    return Instrument(symbol=i["symbol"], status=i["status"], tick_size=Decimal(pf["tickSize"]),
                      qty_step=Decimal(lf["qtyStep"]), min_qty=Decimal(lf["minOrderQty"]),
                      min_notional=Decimal(lf.get("minNotionalValue", "0")))


def server_time_ms(env: str) -> int:
    """The exchange's clock. Used by the health check, and to check that our own clock is not off."""
    return int(_get(env, "/v5/market/time", {})["timeNano"]) // 1_000_000


def klines(env: str, symbol: str, interval: str = "1", limit: int = 200, category: str = "linear") -> list[dict]:
    """Past candles, oldest first: interval in minutes ("1", "3", "5", ...) or "D"."""
    rows = _get(env, "/v5/market/kline", {"category": category, "symbol": symbol, "interval": interval, "limit": limit})["list"]
    out = [dict(start_ms=int(r[0]), open=Decimal(r[1]), high=Decimal(r[2]), low=Decimal(r[3]), close=Decimal(r[4]),
                volume=Decimal(r[5])) for r in rows]
    return sorted(out, key=lambda b: b["start_ms"])
