"""The private REST gateway: our account, our orders (Lecture 24 §2, §6).

Plain mechanism, no decisions: log in, ask, send, cancel. What to do is the strategy's job. Every request
after the login carries the access token in a header ("Authorization: bearer ..."); the token is a secret
too, so it is never logged, and every exchange error is passed through scrub() before it is shown.

Order rules, learned the hard way in the course author's own Deribit backend:
  - **No market order unless the caller says so explicitly** (allow_market=True). A market order ignores
    price and fills at once; a loop that "tries order types" must never send one by accident.
  - **Every order carries our own label** (client_order_id), so a resent order can be recognised and the
    database can follow it before the exchange has given it an id.
  - **Amending needs both amount and price** on Deribit (verified in the author's backend).
  - **Limit prices must lie within the exchange's band** (min_price, max_price in the ticker; about +-3% of
    the mark on BTC-PERPETUAL, checked live 18 November 2026); outside it the order is refused.
"""
import logging
import os
import time
from decimal import Decimal

import requests

from capstone.connectors.deribit_rest import BASE, DeribitError
from capstone.executors.deribit_auth import login_params
from capstone.security.redact import scrub

TIMEOUT = 10
log = logging.getLogger(__name__)


class Gateway:
    def __init__(self, env: str | None = None):
        self.env = env or os.environ.get("DERIBIT_ENV", "testnet")
        if self.env != "testnet":
            raise RuntimeError("the capstone trades on the testnet only")
        self._token, self._expires = None, 0.0

    def _login(self):
        r = requests.get(f"{BASE[self.env]}/public/auth", params=login_params(), timeout=TIMEOUT)
        body = r.json()
        if "error" in body:
            raise DeribitError(scrub(f"login failed: {body['error'].get('code')} {body['error'].get('message')}"))
        res = body["result"]
        self._token = res["access_token"]
        self._expires = time.time() + int(res["expires_in"]) - 60       # renew a minute early
        self.scope = res.get("scope", "")

    def call(self, method: str, params: dict | None = None):
        """A private call; logs in (again) when the token is missing or about to expire.
        Reads (private/get_...) are retried on a timeout. Orders are NEVER retried automatically: after a
        timeout we do not know whether the order arrived, and sending it again could trade twice. The caller
        records the failure and the next reconciliation shows what really happened."""
        if self._token is None or time.time() > self._expires:
            self._login()
        attempts = 3 if method.startswith("private/get_") else 1
        for i in range(attempts):
            try:
                r = requests.get(f"{BASE[self.env]}/{method}", params=params or {}, timeout=TIMEOUT,
                                 headers={"Authorization": f"bearer {self._token}"})
                break
            except (requests.Timeout, requests.ConnectionError):
                if i == attempts - 1:
                    raise
                time.sleep(2 ** i)
        body = r.json()
        if "error" in body:
            raise DeribitError(scrub(f"{method}: {body['error'].get('code')} {body['error'].get('message')}"))
        return body["result"]

    def account_summary(self, currency: str = "BTC") -> dict:
        s = self.call("private/get_account_summary", {"currency": currency})
        return {k: Decimal(str(s[k])) for k in ("equity", "balance", "available_funds", "initial_margin", "maintenance_margin") if k in s}

    @staticmethod
    def _order(o: dict) -> dict:
        """Deribit's order -> the bot's own fields (the connector's translation job)."""
        return dict(exchange_order_id=o["order_id"], client_order_id=o.get("label") or None, instrument=o["instrument_name"],
                    side=o["direction"], order_type=o["order_type"], price=Decimal(str(o["price"])) if o.get("price") not in (None, "market_price") else None,
                    amount=Decimal(str(o["amount"])), filled=Decimal(str(o.get("filled_amount", 0))), state=o["order_state"],
                    post_only=bool(o.get("post_only")), reduce_only=bool(o.get("reduce_only")), updated_ms=o.get("last_update_timestamp"))

    def submit(self, instrument: str, side: str, amount: Decimal, client_order_id: str, price: Decimal | None = None,
               order_type: str = "limit", post_only: bool = True, reduce_only: bool = False, allow_market: bool = False) -> dict:
        if order_type == "market" and not allow_market:
            raise ValueError("market order refused: pass allow_market=True deliberately")
        if order_type == "limit" and price is None:
            raise ValueError("a limit order needs a price")
        params = {"instrument_name": instrument, "amount": str(amount), "type": order_type, "label": client_order_id,
                  "reduce_only": str(reduce_only).lower()}
        if order_type == "limit":
            params.update(price=str(price), post_only=str(post_only).lower(), time_in_force="good_til_cancelled")
        res = self.call(f"private/{'buy' if side == 'buy' else 'sell'}", params)
        return self._order(res["order"])

    def edit(self, exchange_order_id: str, amount: Decimal, price: Decimal, post_only: bool = True) -> dict:
        res = self.call("private/edit", {"order_id": exchange_order_id, "amount": str(amount), "price": str(price),
                                         "post_only": str(post_only).lower()})
        return self._order(res["order"])

    def cancel(self, exchange_order_id: str) -> dict:
        return self._order(self.call("private/cancel", {"order_id": exchange_order_id}))

    def order_state(self, exchange_order_id: str) -> dict:
        return self._order(self.call("private/get_order_state", {"order_id": exchange_order_id}))

    def open_orders(self, instrument: str) -> list[dict]:
        return [self._order(o) for o in self.call("private/get_open_orders_by_instrument", {"instrument_name": instrument})]

    def fills_of_order(self, exchange_order_id: str) -> list[dict]:
        """The executions of one order, in the bot's own fields. A market order may fill in several pieces."""
        out = []
        for t in self.call("private/get_user_trades_by_order", {"order_id": exchange_order_id}):
            out.append(dict(exec_id=str(t["trade_id"]), exchange_order_id=t["order_id"], client_order_id=t.get("label") or None,
                            instrument=t["instrument_name"], side=t["direction"], price=Decimal(str(t["price"])),
                            amount=Decimal(str(t["amount"])), fee=Decimal(str(t["fee"])), fee_currency=t.get("fee_currency"),
                            is_maker=t.get("liquidity") == "M", ts_ms=int(t["timestamp"])))
        return out

    def position(self, instrument: str) -> dict:
        p = self.call("private/get_position", {"instrument_name": instrument})
        return {"size_usd": Decimal(str(p["size"])), "average_price": Decimal(str(p.get("average_price") or 0)),
                "direction": p.get("direction")}
