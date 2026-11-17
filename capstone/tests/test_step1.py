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


def test_book_snapshot_delta_gap():
    b = OrderBook("BTCUSDT")
    b.apply("delta", {"u": 5, "b": [["1", "1"]], "a": []})            # before a snapshot: ignored
    assert not b.valid
    b.apply("snapshot", {"u": 10, "b": [["100.0", "2"], ["99.9", "1"]], "a": [["100.1", "3"]]})
    assert b.best_bid() == Decimal("100.0") and b.best_ask() == Decimal("100.1")
    b.apply("delta", {"u": 11, "b": [["100.0", "0"]], "a": [["100.2", "1"]]})   # size 0 removes the level
    assert b.best_bid() == Decimal("99.9") and len(b.asks) == 2
    assert b.mid() == (Decimal("99.9") + Decimal("100.1")) / 2
    try:
        b.apply("delta", {"u": 13, "b": [], "a": []})                    # 12 is missing
        raise AssertionError("gap not detected")
    except BookGap:
        assert not b.valid
    b.apply("snapshot", {"u": 1, "b": [["100", "1"]], "a": [["101", "1"]]})   # a fresh snapshot repairs it
    assert b.valid and not b.crossed()


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
               ("e1", "BTCUSDT", "Buy", Decimal("64029.30"), Decimal("0.001"), Decimal("0.0002"), "2026-11-17T00:00:00Z"))
    price, fee = db.query("SELECT price, fee FROM fills WHERE exec_id = 'e1'")[0]
    assert dec(price) == Decimal("64029.30") and dec(fee) == Decimal("0.0002"), "money must come back exact"


def test_scrub():
    os.environ["BYBIT_API_SECRET_TEST"] = "s3cr3t-value-123456"
    try:
        assert "s3cr3t" not in scrub("login failed for s3cr3t-value-123456")
        assert "abcdef0123456789" not in scrub("X-BAPI-SIGN: abcdef0123456789")
        logging.basicConfig(level=logging.INFO)
        install_log_scrubbing()
    finally:
        del os.environ["BYBIT_API_SECRET_TEST"]


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
