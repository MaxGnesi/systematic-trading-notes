-- Reconciliation (Lecture 24 §6): trust the exchange for trading, but never silently accept a
-- difference between what we think happened and what the exchange says.

CREATE TABLE IF NOT EXISTS position_snapshots (
    id                 {ID},
    at                 {TS} NOT NULL,
    source             TEXT NOT NULL,            -- 'exchange' (asked over REST) or 'ledger' (summed from our fills)
    symbol             TEXT NOT NULL,
    size               {DEC} NOT NULL,           -- signed, in BTC: positive long, negative short
    avg_price          {DEC}
);

CREATE TABLE IF NOT EXISTS reconciliation_events (
    id                 {ID},
    at                 {TS} NOT NULL,
    kind               TEXT NOT NULL,            -- 'position' or 'open_orders'
    status             TEXT NOT NULL,            -- 'ok' or 'drift'
    ours               TEXT,                     -- what our records say
    theirs             TEXT,                     -- what the exchange says
    action             TEXT                      -- what was done: nothing, paused the strategy, alerted
);
