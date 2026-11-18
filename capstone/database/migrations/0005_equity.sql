-- Equity as the exchange reports it, recorded by the live bot's heartbeat (Lecture 24 §7).
-- The kill switch measures its drawdown from the highest equity recorded here.

CREATE TABLE IF NOT EXISTS equity_snapshots (
    id                 {ID},
    at                 {TS} NOT NULL,
    equity_btc         {DEC} NOT NULL,
    price              {DEC},                    -- index or mid price at the time, to read equity in USD
    position_usd       {DEC}
);
