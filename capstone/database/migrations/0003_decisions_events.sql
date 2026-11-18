-- The strategy's decisions and the bot's own events (Lecture 24 §5, §7, §10).
-- A decision row records the price at the moment the strategy decided: slippage is measured against it.

CREATE TABLE IF NOT EXISTS decisions (
    id                 {ID},
    at                 {TS} NOT NULL,
    strategy           TEXT NOT NULL,
    symbol             TEXT NOT NULL,
    signal             INTEGER,                  -- -1, 0, +1
    action             TEXT NOT NULL,            -- open_long, open_short, close, hold, kill
    target_qty         {DEC},
    arrival_price      {DEC},                    -- mid at the decision
    reason             TEXT,
    params_hash        TEXT                      -- which settings were in force
);

CREATE TABLE IF NOT EXISTS bot_events (           -- disconnects, gaps, restarts, kill switch, alerts
    id                 {ID},
    at                 {TS} NOT NULL,
    level              TEXT NOT NULL,            -- info, warning, critical
    kind               TEXT NOT NULL,
    detail             TEXT
);
