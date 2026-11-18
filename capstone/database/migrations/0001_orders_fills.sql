-- Orders, their history and their fills: the audit trail (Lecture 24 §5).
-- Three tables, not one: an order has one current state but many state changes, and zero, one or
-- many fills (partial fills). {ID}, {DEC} and {TS} are filled in by migrate.py for SQLite or Postgres.

CREATE TABLE IF NOT EXISTS orders (
    id                 {ID},
    client_order_id    TEXT NOT NULL UNIQUE,     -- our own id, sent with the order: a resent order is never doubled
    exchange_order_id  TEXT,                     -- the exchange's id, known once it accepts the order
    symbol             TEXT NOT NULL,
    side               TEXT NOT NULL,            -- Buy or Sell
    order_type         TEXT NOT NULL,            -- Limit or Market
    time_in_force      TEXT,                     -- GTC, IOC, PostOnly
    price              {DEC},
    qty                {DEC} NOT NULL,
    reduce_only        INTEGER NOT NULL DEFAULT 0,
    status             TEXT NOT NULL,            -- current state only; the history is below
    reason             TEXT,                     -- why the strategy sent it: entry, stop_loss, take_profit, ...
    created_at         {TS} NOT NULL,
    updated_at         {TS} NOT NULL
);

CREATE TABLE IF NOT EXISTS order_status_history (   -- append-only: every transition, with when
    id                 {ID},
    client_order_id    TEXT NOT NULL REFERENCES orders(client_order_id),
    status             TEXT NOT NULL,
    at                 {TS} NOT NULL,
    detail             TEXT
);

CREATE TABLE IF NOT EXISTS fills (
    id                 {ID},
    exec_id            TEXT NOT NULL UNIQUE,     -- the exchange's id of this execution: a fill is never counted twice
    client_order_id    TEXT REFERENCES orders(client_order_id),
    exchange_order_id  TEXT,
    symbol             TEXT NOT NULL,
    side               TEXT NOT NULL,
    price              {DEC} NOT NULL,
    qty                {DEC} NOT NULL,
    fee                {DEC},
    fee_currency       TEXT,
    is_maker           INTEGER,
    at                 {TS} NOT NULL
);
