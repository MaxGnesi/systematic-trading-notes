"""Step 2 tests, no network: the signature login and the gateway's safety rules.
Run: python -m capstone.tests.test_step2"""
import base64
from decimal import Decimal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from capstone.database.connection import DB
from capstone.database.migrate import migrate
from capstone.database.store import reconcile, record_order
from capstone.executors.deribit_auth import signature_params
from capstone.executors.gateway import Gateway


def test_ed25519_signature():
    key = Ed25519PrivateKey.generate()                    # a throwaway key, never stored
    p = signature_params("client", private_key=key, now_ms=1700000000000, nonce="abc")
    assert p["grant_type"] == "client_signature" and "client_secret" not in p
    sig = base64.urlsafe_b64decode(p["signature"] + "=" * (-len(p["signature"]) % 4))
    key.public_key().verify(sig, b"1700000000000\nabc\n")   # raises if the signature is wrong


def test_hmac_signature_is_hex():
    p = signature_params("client", client_secret="s" * 20, now_ms=1, nonce="n")
    assert len(p["signature"]) == 64 and all(c in "0123456789abcdef" for c in p["signature"])


def test_no_market_order_by_accident():
    g = Gateway.__new__(Gateway)                          # no login: the check comes before any network call
    try:
        g.submit("BTC-PERPETUAL", "buy", Decimal("10"), "x", order_type="market")
        raise AssertionError("market order not refused")
    except ValueError:
        pass


def test_testnet_only():
    try:
        Gateway("mainnet")
        raise AssertionError("mainnet not refused")
    except RuntimeError:
        pass


def test_order_history_and_reconcile():
    db = DB("sqlite:///:memory:"); migrate(db)
    o = dict(client_order_id="c1", exchange_order_id="e1", instrument="BTC-PERPETUAL", side="buy", order_type="limit",
             price=Decimal("60000"), amount=Decimal("10"), state="open", post_only=True)
    record_order(db, o)
    assert reconcile(db, "BTC-PERPETUAL", [o], Decimal("0"), Decimal("0")) == []
    assert reconcile(db, "BTC-PERPETUAL", [], Decimal("0"), Decimal("0")), "an order missing on the exchange is drift"
    record_order(db, {**o, "state": "cancelled"})
    hist = [r[0] for r in db.query("SELECT status FROM order_status_history WHERE client_order_id = 'c1' ORDER BY id")]
    assert hist == ["open", "cancelled"]
    assert reconcile(db, "BTC-PERPETUAL", [], Decimal("10"), Decimal("0")), "a position we did not record is drift"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
