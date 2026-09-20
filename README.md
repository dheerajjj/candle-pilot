# Candle Pilot — Personal Kite stock research agent

Python 3.11+; standard library only. Research and paper trading work with CSV data; Kite access needs your own official Kite Connect app and daily authenticated access token. This is a starter strategy, **not a proven profitable system**. No forecast or return guarantee is possible.

## Inputs

`daily.csv` needs `date,open,high,low,close,volume` in ascending date order, at least 65 rows. `open` is retained on fetch but this prototype fills on the next **close** to avoid same-day look-ahead. Its simulated price, fees and slippage are approximations; real execution can differ. Adjust prices for splits and dividends when evaluating long histories. Optional `news.csv` is `date,score`, with a *point-in-time* score from -1 to 1 (negative news below -0.5 vetoes holding). There is no built-in live news feed or LLM: news scores must come from a properly licensed external data service and be timestamped before trading. Never backfill hindsight headlines into tests.

## Run

```bash
python -m unittest discover -s tests -v
python agent.py backtest --csv daily.csv --output results.json
python agent.py signal --csv daily.csv --symbol INFY
python agent.py paper --csv daily.csv --symbol INFY --state paper.json
```

Paper command processes the final row of a daily CSV once. Run again with another completed daily candle: yesterday's pending signal fills at that new day's close. Keep `paper.json` private and backed up. To paper trade multiple symbols, use the same state and call once per symbol daily; the sizing limit uses starting capital and is an approximation. `backtest` reports full-period return, maximum drawdown, buy-and-hold return, trades and equity curve. Reserve the last 25–30% of chronological data as untouched validation and compare against buy-and-hold and costs; a single backtest is not evidence of an edge.

## Kite market data

Follow [Kite Connect's official login flow](https://kite.trade/docs/connect/v3/user/) to obtain a session access token. Set `KITE_API_KEY` and `KITE_ACCESS_TOKEN` in your shell or secret manager (never commit them). Find the *instrument token* from [Kite's instrument list](https://kite.trade/docs/connect/v3/market-quotes/#instruments); a symbol alone is not the token.

```bash
python agent.py fetch --symbol INFY --instrument-token YOUR_TOKEN --start 2024-01-01 --end 2026-09-19 --output daily.csv
```

Kite may impose historical data range and request limits; fetch smaller ranges and concatenate chronologically when needed. `fetch` reads live credentials; no live orders occur unless you explicitly run `order`.

## Live order gate (optional)

Verify your current broker and SEBI algo/API requirements before enabling live trading. The CLI has **no unattended trading scheduler**, no live market-wide news feed, and does not auto convert signals to orders. It supports only manually confirmed NSE equity CNC **limit** orders up to 10 shares and ₹5,000 per order. An order can remain open or be rejected; inspect the returned history and Kite before taking any further action. Do not retry blindly on a timeout, as a submitted order may still exist.

```bash
export ENABLE_LIVE_TRADING=YES
python agent.py order --symbol INFY --side BUY --quantity 1 --limit-price 1500 --confirm BUY:INFY:1:1500.0
```

Before any unattended live system, add authenticated position reconciliation, stale-data checks, broker-compliant rate and order limits, trading-hours checks, daily-loss guard across holdings, order deduplication after network failures, a kill switch, logging/alerts and broker/exchange rule review. Never put Kite credentials into a chat prompt or source file.
