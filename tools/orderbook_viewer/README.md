# Order-book viewer

A small local web app to scan through the Bybit BTCUSDT order book and trades of Part IV (Lecture 18 onwards): the book over time as a heatmap with every trade, the ladder and the tape at any moment, and the liquidity measures of Lecture 18, §5, through the day.

**Before you start.** Download and convert the data as in Lecture 18, §3.4, so that `parquet/orderbook/BTCUSDT/` and `parquet/trades/BTCUSDT/` exist under one folder. The app needs `fastapi` and `uvicorn` (`pip install fastapi uvicorn`) besides `polars` and `numpy`.

**Start it.**

```
set BYBIT_ROOT=D:\trading-data\bybit        (the folder holding parquet/; Windows; on macOS or Linux: export BYBIT_ROOT=...)
python server.py
```

then open http://127.0.0.1:8077 (another port: set `VIEWER_PORT`).

**First use of a day.** The book can only be rebuilt from a day's midnight snapshot, so the first time a day is opened the app replays it once (15 to 30 seconds) and caches the book of every minute and a summary of every second next to the data. `python build_all_caches.py` prepares all days in advance.

**What it shows.**

| Panel | Content |
|---|---|
| The day at a glance | The day's price and volume, or one of the liquidity measures (spread, depth within 5 bp, book imbalance, cost of a 1 or 5 BTC market buy); feed gaps and events marked; click to jump |
| The book over time | Resting size by price and time (bids blue, asks pink), best bid and ask, every trade (green: buyer aggressive, orange: seller aggressive); click to set the cursor |
| Ladder at the cursor | The best 15 levels on each side at that moment |
| Tape | The trades of the 20 seconds up to the cursor |
| At the cursor | Spread, depth within 5 bp, book imbalance, the cost of 1 and 5 BTC market orders |
