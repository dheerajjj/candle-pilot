# Candle Pilot — Personal Kite stock research agent

## Version 0.7: live prices while the results window is open

After the user logs in and a read-only recommendation report appears, Candle Pilot now opens **one** official KiteTicker WebSocket connection in a separate thread and subscribes to the report's instrument tokens in LTP mode. Each card shows the last received live price. The connection closes when the results window closes. The UI indicates disconnections, reconnects, prices that moved over 1% from the analyzed quote, and any symbol with no new tick for 60 seconds. No tick means no recent trade update; it does not necessarily mean the socket failed.

The BUY/SELL/HOLD suggestion, quantity, reason, cash and suggested spend remain the **snapshot from the original analysis**. A moving live price does not automatically refresh the underlying historical candle/news analysis or alter a proposed quantity. Close the results window and run the analysis again before acting on a changed price. The completed 5-minute candle check remains required for new BUY ideas; WebSocket LTP ticks supply live prices, **not completed candles**. If WebSocket access is unavailable, the result cards still show the original quote and explain that the live stream could not start. The desktop app never places orders. [Official Zerodha WebSocket docs](https://kite.trade/docs/connect/v3/websocket/) and [threaded SDK example](https://github.com/zerodha/pykiteconnect/blob/master/examples/threaded_ticker.py).

## Version 0.6: intraday confirmation

For a potential new BUY, the desktop app requests Kite's **5minute** historical candles from today's 09:15 IST open. It ignores incomplete intervals and requires at least two completed, recent candles. It checks the current quote against the last completed close and a volume-weighted typical price, and rejects a sharp drop in the latest completed close. Missing, stale, or invalid intraday candles withhold the BUY; the result card explains why. This is an additional heuristic, not a tested prediction. Before roughly 09:30:30 IST, two completed candles may not yet be available, so no new BUY will clear this guard. Held-stock SELL/HOLD reviews do not depend on this intraday BUY check.

The app requests a current quote and completed 5-minute historical candles while generating its read-only report. Version 0.7 additionally streams live prices while the results window stays open, but does not automatically regenerate signals from each tick. [Kite historical candles](https://kite.trade/docs/connect/v3/historical/) and [KiteTicker streaming](https://kite.trade/docs/connect/v3/agent-setup/#4-stream-live-market-data).

## Version 0.5.2: company names on result cards

Each desktop suggestion now displays the NSE ticker and Kite instrument company name, including for held stocks and stocks skipped because data is unavailable. For example, `INFY` is shown together with the name returned for that instrument by Kite. No live order is sent.

## Version 0.5.1: review existing holdings

The desktop display includes held NSE equities alongside new buy candidates. If the completed daily-candle exit rule triggers for a holding, the card says **SELL** and shows the quantity currently reported by Kite, its current quote, and the exact rule. SELL is a **review prompt**, not an order or a guarantee that selling is right. Other holdings show HOLD with a reason. Suggested BUY quantities are budgeted separately and are never funded by hypothetical sales. No Kite orders are submitted by the desktop app.

## Version 0.5: NSE equity discovery and existing holdings

The desktop run loads Kite's NSE equity instrument list and requests quote snapshots in batches of 400. It screens the available cash equities for approximate daily turnover (price × volume of at least ₹2 crore), share price ₹50–₹2,475, and intraday move within ±8%. It then performs deeper historical/market/candlestick/news checks on **up to 12** high-turnover new names, as well as **up to 10** existing NSE equity holdings. It displays counts for the instrument universe, returned quotes, holdings, and new candidates. A new stock need not be on a preset watchlist. Holdings are shown for review but do not receive another BUY suggestion.

This covers NSE cash equities returned by Kite on that run; it does **not** deeply research every listed stock, cover BSE-only names, or identify the objectively best investment. Turnover shortlisting favors actively traded names and can miss good smaller companies. Missing quote batches abort the screen; if over half of individual quotes are missing, the screen aborts. Quote snapshots and public headlines can be stale or incomplete. No trades are placed. [Kite instrument list and quote limits](https://kite.trade/docs/connect/v3/market-quotes/).

## Version 0.4: available-funds-based suggestions

The desktop screen now **reads your Kite equity funds** and displays a proposed basket with the share quantity and indicative current price per name. It uses the conservative minimum of Kite's reported net, live balance and cash, never total holdings value. The recommendation budget is the lesser of half the available funds or ₹5,000; each name is limited to ₹2,500 and ten shares. For example, with ₹10,000 available it may suggest two qualifying stocks with quantities fitting within a total ₹5,000 budget, keeping at least ₹5,000 untouched. If no stock clears all checks, it suggests no buy. Existing Kite holdings do not get duplicate buy suggestions. An estimate is not a reserved balance, and prices can change before an order is placed.

This is **read-only**. The desktop launcher does not update your Kite portfolio or place orders, and its screen is rebuilt on each run rather than recording a simulated fill. Suggestions cover shortlisted stocks only and do not measure personal suitability, tax impact, or expected return. Always inspect the actual Kite order preview and account balance before any manual purchase. [Zerodha funds and margins reference](https://kite.trade/docs/connect/v3/user/#funds-and-margins).

## Version 0.3: market, candles and headline context

The **desktop paper agent** checks the NIFTY 50 quote against its previous close and 50 completed daily closes, detects bullish/bearish two-candle engulfing patterns, and searches GDELT's public news index for matching company headlines from the last two days. It shows the results alongside its stock's 20/60-day trend, breakout and volume explanation. A new BUY is withheld if the market condition fails, news is unreachable or has no recent matching headlines, a high-risk word appears in a headline, or a bearish engulfing pattern appears. Headline word matching can be wrong (including negation, old reports and similar company names); it is a conservative review flag, **not verified sentiment or fundamental analysis**. News is read at runtime and is unsuitable for historical backtests without timestamped archives. An outage may result in no BUY suggestions.

The separate command-line paper runner remains capped at ten shares and by its configured ₹5,000 per-order and daily-buy limits. The desktop flow now shows read-only budgeted suggestions on shortlisted NSE shares; it does not guarantee returns. The extra headline context applies to paper/research decisions only; do not turn on experimental live execution based on it. The feed is public and may be delayed, incomplete, or rate-limited. [Kite market data reference](https://kite.trade/docs/connect/v3/market-quotes/); [GDELT DOC API reference](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/).

## Version 0.2: readable paper results

After a weekday login, the desktop window shows one card per stock with its paper action, quantity, price and the rule that caused the decision. BUY/SELL prices are simulated fills at the current quote. HOLD displays the last completed daily close as a reference; SKIP may have no price if the quote was not fetched. Quantity zero means no transaction. These are rule explanations, not confidence scores or predictions.

The base signal examines around 60 completed daily candles: 20/60-day moving averages, a 20-day high breakout and volume against the prior 20 days. A current quote is used for paper fills and a large-move guard. The desktop context checks only one broad index, one simple candlestick pattern family, and recent headline titles. It does not forecast future returns or place real orders. Independent, point-in-time validation is required before relying on these filters.

Python 3.11+; uses Zerodha’s official `kiteconnect` SDK and Windows Credential Manager through `keyring`. Install dependencies using `uv sync` or `python -m pip install -r requirements.txt`. Research and paper trading work with CSV data; Kite access needs your own official Kite Connect app and daily authenticated access token. This is a starter strategy, **not a proven profitable system**. No forecast or return guarantee is possible.

## One-click Windows setup (recommended)

1. In your [Kite Connect developer app](https://developers.kite.trade/), register the redirect URL **`http://127.0.0.1:8787/callback`** exactly. This is required by Zerodha once for the local browser login. Keep the app's API key and API secret handy. Do not put them into the code or send them in chat.
2. On Windows, double-click **`CandlePilot.cmd`** in the latest repository download. It installs missing Python dependencies automatically. At first launch, enter your **Kite Connect API key** and **Kite Connect API secret** into the two hidden prompts. They are saved in your Windows Credential Manager. Do not enter your Kite password or TOTP into the app.
3. On each trading morning, double-click `CandlePilot.cmd` and press **Connect Kite and see suggestions**. Complete the official Zerodha browser login; the local callback finishes without copying tokens. The read-only run screens available NSE cash equities, researches selected new names and your existing NSE equity holdings, reads available funds, and shows its suggestions. Run between **09:20 and 14:55 IST** on trading weekdays.

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
