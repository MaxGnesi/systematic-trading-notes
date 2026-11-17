"""Step 1 tests, no network: the local order book, bars, the database and the secrets rules.
Run: python -m capstone.tests.test_step1"""
import logging
import os
import subprocess
from decimal import Decimal
from pathlib import Path

from capstone.connectors.bars import BarBuilder
from capstone.connectors.order_book import BookGap, OrderBook
from capstone.database.connection import DB, dec
from capstone.database.migrate import migrate
from capstone.security.redact import install_log_scrubbing, scrub

ROOT = Path(__file__).resolve().parents[1]


def test_book_snapshot_change_gap():
    b = OrderBook("BTC-PERPETUAL")
    b.change([("1", "1")], [], 5, 4)                                    # before a snapshot: ignored
    assert not b.valid
    b.snapshot([("100.0", "2"), ("99.5", "1")], [("100.5", "3")], change_id=10)
    assert b.best_bid() == Decimal("100.0") and b.best_ask() == Decimal("100.5")
    b.change([("100.0", 0)], [("101.0", "1")], change_id=17, prev_change_id=10)   # size 0 removes the level
    assert b.best_bid() == Decimal("99.5") and len(b.asks) == 2
    assert b.mid() == (Decimal("99.5") + Decimal("100.5")) / 2
    try:
        b.change([], [], change_id=30, prev_change_id=25)               # the change after 17 is missing
        raise AssertionError("gap not detected")
    except BookGap:
        assert not b.valid
    b.snapshot([("100", "1")], [("101", "1")], change_id=40)            # a fresh snapshot repairs it
    assert b.valid and not b.crossed()


def test_deribit_levels():
    from capstone.connectors.deribit_public_feed import _levels
    assert _levels([["new", 100.5, 10.0], ["change", 101.0, 20.0], ["delete", 99.0, 0.0]]) == [(100.5, 10.0), (101.0, 20.0), (99.0, 0)]


def test_bars():
    out = []
    bb = BarBuilder(out.append)
    for ts, p, q in [(30_000, "8", "1"), (60_000, "10", "1"), (60_500, "12", "2"), (119_999, "9", "1"), (120_000, "11", "1")]:
        bb.add_trade(dict(ts_ms=ts, price=Decimal(p), qty=Decimal(q)))
    assert len(out) == 1, "only finished bars are handed on, and the first, partial bar is dropped"
    b = out[0]
    assert (b["open"], b["high"], b["low"], b["close"], b["volume"], b["trades"]) == (Decimal("10"), Decimal("12"), Decimal("9"), Decimal("9"), Decimal("4"), 3)


def test_database_exact_decimals():
    db = DB("sqlite:///:memory:")
    applied = migrate(db)
    assert applied == sorted(applied) and len(applied) >= 4
    assert migrate(db) == [], "a migration must never run twice"
    db.execute("INSERT INTO fills (exec_id, symbol, side, price, qty, fee, at) VALUES (?,?,?,?,?,?,?)",
               ("e1", "BTC-PERPETUAL", "buy", Decimal("64592.5"), Decimal("10"), Decimal("0.00000077"), "2026-11-17T00:00:00Z"))
    price, fee = db.query("SELECT price, fee FROM fills WHERE exec_id = 'e1'")[0]
    assert dec(price) == Decimal("64592.5") and dec(fee) == Decimal("0.00000077"), "money must come back exact"


def test_scrub():
    os.environ["DERIBIT_CLIENT_SECRET_TEST"] = "s3cr3t-value-123456"
    try:
        assert "s3cr3t" not in scrub("login failed for s3cr3t-value-123456")
        assert "abcdef0123456789" not in scrub("signature=abcdef0123456789")
        logging.basicConfig(level=logging.INFO)
        install_log_scrubbing()
    finally:
        del os.environ["DERIBIT_CLIENT_SECRET_TEST"]


def test_conformance():
    """Rules that must hold in every file: no secrets in the repository, every program scrubs its logs."""
    tracked = subprocess.run(["git", "ls-files", str(ROOT)], capture_output=True, text=True, cwd=ROOT).stdout.split()
    bad = [f for f in tracked if f.endswith((".env", ".pem", ".key")) or "/.keys/" in f]
    assert not bad, f"secret files tracked by git: {bad}"
    for f in ROOT.rglob("*.py"):
        s = f.read_text(encoding="utf-8")
        if "logging.basicConfig(" in s and "tests" not in f.parts:
            assert "install_log_scrubbing()" in s, f"{f.name} sets up logging without scrubbing"
        if "tests" not in f.parts:
            assert "print(os.environ" not in s and "print(os.getenv" not in s, f"{f.name} prints the environment"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
