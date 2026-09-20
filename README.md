# Candle Pilot — Personal Kite stock research agent

## Version 0.2: readable paper results

After a weekday login, the desktop window shows one card per stock with its paper action, quantity, price and the rule that caused the decision. BUY/SELL prices are simulated fills at the current quote. HOLD displays the last completed daily close as a reference; SKIP may have no price if the quote was not fetched. Quantity zero means no transaction. These are rule explanations, not confidence scores or predictions.

The paper strategy examines around 60 completed daily candles: 20/60-day moving averages, a 20-day high breakout and volume against the prior 20 days. A current quote is used for paper fills and a large-move guard. The desktop flow does **not** supply company news scores, assess a broad market index, recognize candlestick patterns or forecast future returns. It also does not place real orders. More inputs require a trustworthy point-in-time news source, index data and validation on independent periods before they should influence any decisions.

Python 3.11+; uses Zerodha’s official `kiteconnect` SDK and Windows Credential Manager through `keyring`. Install dependencies using `uv sync` or `python -m pip install -r requirements.txt`. Research and paper trading work with CSV data; Kite access needs your own official Kite Connect app and daily authenticated access token. This is a starter strategy, **not a proven profitable system**. No forecast or return guarantee is possible.

## One-click Windows setup (recommended)

1. In your [Kite Connect developer app](https://developers.kite.trade/), register the redirect URL **`http://127.0.0.1:8787/callback`** exactly. This is required by Zerodha once for the local browser login. Keep the app's API key and API secret handy. Do not put them into the code or send them in chat.
2. On Windows, double-click **`CandlePilot.cmd`** in the latest repository download. It installs missing Python dependencies automatically. At first launch, enter your **Kite Connect API key** and **Kite Connect API secret** into the two hidden prompts. They are saved in your Windows Credential Manager. Do not enter your Kite password or TOTP into the app.
3. On each trading morning, double-click `CandlePilot.cmd` and press **Connect Kite and run paper agent**. Complete the official Zerodha browser login; the local callback finishes without copying tokens. The paper run then scans your current NSE holdings and five default watchlist stocks (INFY, RELIANCE, TCS, HDFCBANK, ICICIBANK) and shows its decisions. Instrument tokens are resolved from Kite automatically. Run between **09:20 and 14:55 IST** on trading weekdays.

No real orders are sent by this launcher. The five default stocks are a small initial watchlist, **not the whole market**, and there is no automatic news analysis yet. Daily user login is still required by Zerodha; the Kite access token expires at 6 a.m. the next day. If you already stored the API key and secret with `credentials.py setup`, the launcher reuses them and prompts only for anything missing. If Windows blocks the local callback, allow localhost access to port 8787 for this app. If `CandlePilot.cmd` cannot find Python, install Python 3.11+ for Windows with the launcher enabled and try again.

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

Follow [Kite Connect's official login flow](https://kite.trade/docs/connect/v3/user/) to obtain a session access token. Candle Pilot uses `KiteConnect.login_url()` and `generate_session()` from Zerodha’s Python SDK. Use `python credentials.py setup` and `python credentials.py login` below to keep credentials in Windows Credential Manager (never commit them). Find the *instrument token* from [Kite's instrument list](https://kite.trade/docs/connect/v3/market-quotes/#instruments); a symbol alone is not the token.

```bash
python agent.py fetch --symbol INFY --instrument-token YOUR_TOKEN --start 2024-01-01 --end 2026-09-19 --output daily.csv
```

Kite may impose historical data range and request limits; fetch smaller ranges and concatenate chronologically when needed. `fetch` reads live credentials; no live orders occur unless you explicitly run `order`.

## Live order gate (optional)

Verify your current broker and SEBI algo/API requirements before enabling live trading. The manual `agent.py order` command has no scheduling or automatic signals; the separate `autopilot.py` runner handles scheduled decisions. Neither has a live market-wide news feed. It supports only manually confirmed NSE equity CNC **limit** orders up to 10 shares and ₹5,000 per order. An order can remain open or be rejected; inspect the returned history and Kite before taking any further action. Do not retry blindly on a timeout, as a submitted order may still exist.

```bash
export ENABLE_LIVE_TRADING=YES
python agent.py order --symbol INFY --side BUY --quantity 1 --limit-price 1500 --confirm BUY:INFY:1:1500.0
```

Before any unattended live system, add authenticated position reconciliation, stale-data checks, broker-compliant rate and order limits, trading-hours checks, daily-loss guard across holdings, order deduplication after network failures, a kill switch, logging/alerts and broker/exchange rule review. Never put Kite credentials into a chat prompt or source file.

## Automated daily runner

`autopilot.py` fetches recent **real** Kite daily candles for your selected NSE stocks, calculates yesterday's signal, checks a current quote, and makes a daily decision. It can place CNC limit orders when explicitly configured for live mode. It does not read market-wide news, predict returns, or guarantee profits. Start in paper mode to observe it first.

1. Create a [Kite Connect app](https://kite.trade/docs/connect/v3/) and set up Windows Credential Manager using the exact steps below. Log in via Zerodha's **official** login flow each trading day. Never put tokens in this public repository or send them in chat.
2. Copy `autopilot_config.example.json` to `autopilot_config.json`; verify the instrument token for each selected symbol from Kite's instrument list. Set your own risk limits, at most ₹5,000 per order and ₹5,000 bought per day in this version. The default is `paper`.
3. Run `python autopilot.py --config autopilot_config.json` once during market hours. The output says what it decided; it records decisions in `autopilot_state.json` to avoid submitting a duplicate on the same day.
4. To run automatically on Windows, create a **daily 10:00 a.m. IST task** in Windows Task Scheduler that starts `python` with arguments `autopilot.py --config autopilot_config.json` and sets **Start in** to your project folder. Your Kite session token must be valid that day; [Kite documents expiry at 6 a.m. the next day](https://kite.trade/docs/connect/v3/user/). Scheduling does not bypass required Zerodha authentication.

Live mode is an **experimental execution path** that requires changing the local config mode to `live` and setting `ENABLE_LIVE_TRADING=YES`. It checks Kite holdings, available cash, existing tagged orders and daily caps, but this is not a production trading service: there is no live news feed, complete exchange-holiday calendar, corporate-action handling, full multi-day order reconciliation, or automatic token renewal. Do not enable live trading until the strategy is validated on real data, broker/API requirements are confirmed, and the remaining safeguards are built and reviewed. If a Kite order request times out after submission, the program will not retry it; inspect Kite and reconcile the attempt manually.

## Windows credentials: exact setup

**Do not use “Add a Windows Credential” by hand.** Candle Pilot creates its own entry safely through Python's `keyring` library. Use native Windows Python from Git Bash or PowerShell; WSL is not supported for this setup.

1. Create a Kite Connect app in [Zerodha's developer portal](https://developers.kite.trade/), with a redirect URL that you control (for example, `http://127.0.0.1:8787/callback`). Keep the app's **API key** and **API secret** ready; these are issued by Zerodha. The callback URL may show a connection error after login; the address bar still contains the short-lived `request_token` to copy. Do not share that URL. 
2. In your `candle-pilot-main` folder run `python -m pip install -r requirements.txt` (or, if `uv` is installed, `uv sync` and then prefix the following commands with `uv run`), then `python credentials.py setup`. At the hidden prompts, paste the **Kite Connect API key** and **API secret**, respectively. The program creates the `CandlePilot.Kite` entry in your Windows Credential Manager. Do **not** enter your Kite account password or TOTP here.
3. Each trading day, run `python credentials.py login`. It opens Kite's official login page, where you log in yourself. Paste the full browser redirect URL into the hidden prompt. The program exchanges its one-time request token and saves the resulting access token in Windows Credential Manager. Run `python credentials.py status` to see stored/missing fields (no secret values displayed).
4. Run `python autopilot.py --config autopilot_config.json` after login, or schedule that command for 10:00 a.m. IST. The scheduled task must run as the **same Windows user** who ran setup/login. If the token has expired, the run stops. It never stores your Kite password or TOTP and does not circumvent Zerodha's required daily login.

Run `python credentials.py delete` to remove Candle Pilot's stored credentials. If you previously pasted any secret into GitHub, chat or an exposed file, revoke/rotate it via Zerodha. Avoid screenshots showing the redirect URL or token. [Kite documents the official login flow and next-day 6 a.m. session expiry](https://kite.trade/docs/connect/v3/user/).

## Kite SDK

All live Kite API calls now use Zerodha’s official [pykiteconnect SDK](https://github.com/zerodha/pykiteconnect) via `kite_sdk.py`; authentication uses `KiteConnect.login_url()` and `generate_session()`. The project declares dependencies in `pyproject.toml` for `uv` and `requirements.txt` for ordinary Python. `KiteTicker` live streaming is not needed for this once-per-day strategy; the agent uses historical daily candles and a quote. The SDK change does not validate the strategy or make live execution safe by itself.
