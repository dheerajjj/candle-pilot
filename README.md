# Candle Pilot — Personal Kite stock research agent

Python 3.11+; standard library only. Research and paper trading work with CSV data; Kite access needs your own official Kite Connect app and daily authenticated access token. This is a starter strategy, **not a proven profitable system**. No forecast or return guarantee is possible.

## Try it now with sample data

The included `examples/demo_synthetic.csv` contains **fabricated prices**, only to verify that the program runs. It is not INFY or any real stock; its returns say nothing about investment performance. From the repository folder, run:

```bash
python agent.py backtest --csv examples/demo_synthetic.csv --output demo_results.json
python agent.py paper --csv examples/demo_synthetic.csv --symbol DEMO --state demo_paper.json
```

For real analysis, supply a daily CSV exported from an authorized market data provider, or fetch candles with your own Kite Connect credentials as shown below. A filename like `daily.csv` in the commands is a placeholder: create that file first or pass the actual path.

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

## Automated daily runner

`autopilot.py` fetches recent **real** Kite daily candles for your selected NSE stocks, calculates yesterday's signal, checks a current quote, and makes a daily decision. It can place CNC limit orders when explicitly configured for live mode. It does not read market-wide news, predict returns, or guarantee profits. Start in paper mode to observe it first.

1. Create a [Kite Connect app](https://kite.trade/docs/connect/v3/) and obtain a valid daily access token using Zerodha's **official** login flow. Put `KITE_API_KEY` and `KITE_ACCESS_TOKEN` in local environment variables or a secret manager. Never put them in this public repository or send them in chat.
2. Copy `autopilot_config.example.json` to `autopilot_config.json`; verify the instrument token for each selected symbol from Kite's instrument list. Set your own risk limits, at most ₹5,000 per order and ₹5,000 bought per day in this version. The default is `paper`.
3. Run `python autopilot.py --config autopilot_config.json` once during market hours. The output says what it decided; it records decisions in `autopilot_state.json` to avoid submitting a duplicate on the same day.
4. To run automatically on Windows, create a **daily 10:00 a.m. IST task** in Windows Task Scheduler that starts `python` with arguments `autopilot.py --config autopilot_config.json` and sets **Start in** to your project folder. Your Kite session token must be valid that day; [Kite documents expiry at 6 a.m. the next day](https://kite.trade/docs/connect/v3/user/). Scheduling does not bypass required Zerodha authentication.

Live mode is an **experimental execution path** that requires changing the local config mode to `live` and setting `ENABLE_LIVE_TRADING=YES`. It checks Kite holdings, available cash, existing tagged orders and daily caps, but this is not a production trading service: there is no live news feed, complete exchange-holiday calendar, corporate-action handling, full multi-day order reconciliation, or automatic token renewal. Do not enable live trading until the strategy is validated on real data, broker/API requirements are confirmed, and the remaining safeguards are built and reviewed. If a Kite order request times out after submission, the program will not retry it; inspect Kite and reconcile the attempt manually.
