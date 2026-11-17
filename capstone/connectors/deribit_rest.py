"""Deribit's public REST API: one question, one answer (Lecture 24 §2).

Public methods need no key: instrument details, the server time, past candles. Every answer is a
JSON-RPC envelope, {"jsonrpc": "2.0", "result": ...} or {"error": {...}}; an error is raised, never ignored.

Verified live (17 November 2026), mainnet and testnet alike: BTC-PERPETUAL is an inverse ("reversed")
contract settled in BTC and quoted in USD; tick 0.5 USD; order amounts are in USD, in steps of the
contract size, 10 USD, with a minimum of 10 USD.
"""
from dataclasses import dataclass
from decimal import Decimal

import requests

BASE = {"mainnet": "https://www.deribit.com/api/v2", "testnet": "https://test.deribit.com/api/v2"}
TIMEOUT = 10


class DeribitError(Exception):
    pass


def _get(env: str, method: str, params: dict) -> dict | list:
    r = requests.get(f"{BASE[env]}/{method}", params=params, timeout=TIMEOUT)
    body = r.json()
    if "error" in body:
        raise DeribitError(f"{method}: {body['error'].get('code')} {body['error'].get('message')}")
    r.raise_for_status()
    return body["result"]


@dataclass(frozen=True)
class Instrument:
    """What the exchange means by price and amount for one contract: the connector's job to know."""
    name: str
    kind: str
    instrument_type: str     # 'reversed' = inverse: amount in USD, profit and loss in BTC
    tick_size: Decimal       # prices must be multiples of this
    contract_size: Decimal   # amounts must be multiples of this (USD for an inverse contract)
    min_amount: Decimal
    is_active: bool

    def round_price(self, price: Decimal) -> Decimal:
        return (price / self.tick_size).to_integral_value() * self.tick_size

    def round_amount_down(self, amount: Decimal) -> Decimal:
        return (amount / self.contract_size).to_integral_value(rounding="ROUND_DOWN") * self.contract_size


def instrument(env: str, name: str) -> Instrument:
    i = _get(env, "public/get_instrument", {"instrument_name": name})
    return Instrument(name=i["instrument_name"], kind=i["kind"], instrument_type=i.get("instrument_type", ""),
                      tick_size=Decimal(str(i["tick_size"])), contract_size=Decimal(str(i["contract_size"])),
                      min_amount=Decimal(str(i["min_trade_amount"])), is_active=bool(i["is_active"]))


def server_time_ms(env: str) -> int:
    """The exchange's clock. Used by the health check, and to check that our own clock is not off."""
    return int(_get(env, "public/get_time", {}))


def candles(env: str, name: str, start_ms: int, end_ms: int, resolution: str = "1") -> list[dict]:
    """Past candles, oldest first; resolution in minutes ("1", "3", "5", ...) or "1D". Volume as Deribit
    reports it for the contract (for BTC-PERPETUAL, in BTC)."""
    r = _get(env, "public/get_tradingview_chart_data", {"instrument_name": name, "resolution": resolution,
                                                       "start_timestamp": start_ms, "end_timestamp": end_ms})
    if r.get("status") != "ok":
        return []
    keys = ("ticks", "open", "high", "low", "close", "volume")
    return [dict(start_ms=int(t), open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(lo)), close=Decimal(str(c)),
                 volume=Decimal(str(v))) for t, o, h, lo, c, v in zip(*(r[k] for k in keys))]
