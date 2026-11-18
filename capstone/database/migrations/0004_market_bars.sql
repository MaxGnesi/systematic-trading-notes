-- One-minute bars built from the public trades, for the strategy, the backtest and the dashboard.

CREATE TABLE IF NOT EXISTS bars_1m (
    symbol             TEXT NOT NULL,
    start_ms           BIGINT NOT NULL,          -- bar start, exchange time in milliseconds
    open               {DEC} NOT NULL,
    high               {DEC} NOT NULL,
    low                {DEC} NOT NULL,
    close              {DEC} NOT NULL,
    volume             {DEC} NOT NULL,           -- BTC traded
    trades             INTEGER,
    source             TEXT NOT NULL,            -- 'live' (built from our feed) or 'rest' (the exchange's own candles)
    PRIMARY KEY (symbol, start_ms)
);
