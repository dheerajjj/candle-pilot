"""Personal equity research and paper trading CLI. Python 3.11+, stdlib only."""
import argparse
import csv
import datetime as dt
import json
import math
import os
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parent


def load_candles(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            day = dt.date.fromisoformat(r['date'][:10])
            close, high, low, volume = (float(r[k]) for k in ('close', 'high', 'low', 'volume'))
            if not (0 < low <= close <= high and volume >= 0):
                raise ValueError(f'Invalid OHLCV on {day}')
            rows.append(dict(date=day, close=close, high=high, low=low, volume=volume))
    if len(rows) < 65 or any(a['date'] >= b['date'] for a, b in zip(rows, rows[1:])):
        raise ValueError('Need at least 65 strictly ascending daily candles')
    return rows


def load_news(path):
    if not path:
        return {}
    result = {}
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            day = dt.date.fromisoformat(r['date'][:10])
            score = float(r['score'])
            if not -1 <= score <= 1:
                raise ValueError('News score must be between -1 and 1')
            result.setdefault(day, []).append(score)
    return {d: statistics.mean(scores) for d, scores in result.items()}


def signal(rows, index, news=None):
    """Past-only close/volume trend signal. News veto uses only today's dated score."""
    return signal_details(rows, index, news)['signal']


def signal_details(rows, index, news=None):
    """The signal and the precise rule that produced it, using completed candles."""
    if index < 60:
        return {'signal':'HOLD','reason':'Fewer than 61 completed daily candles; waiting for enough history.'}
    window = rows[index-59:index+1]
    p = window[-1]['close']
    sma20 = statistics.mean(x['close'] for x in window[-20:])
    sma60 = statistics.mean(x['close'] for x in window)
    prev_high = max(x['high'] for x in window[-21:-1])
    vol20 = statistics.mean(x['volume'] for x in window[-21:-1])
    news_score = (news or {}).get(window[-1]['date'], 0)
    if news_score < -0.5:
        return {'signal':'SELL','reason':f'Provided news score {news_score:.2f} is below -0.50.'}
    if p < sma20 or sma20 < sma60:
        return {'signal':'SELL','reason':f'Trend weakened: prior close ₹{p:,.2f}, 20-day average ₹{sma20:,.2f}, 60-day average ₹{sma60:,.2f}.'}
    if p > prev_high and window[-1]['volume'] > 1.2 * vol20 and news_score >= -0.2:
        return {'signal':'BUY','reason':f'Prior close ₹{p:,.2f} broke the previous 20-day high ₹{prev_high:,.2f}; volume was {window[-1]["volume"]/vol20:.1f}× its 20-day average.'}
    return {'signal':'HOLD','reason':f'No breakout or trend exit: prior close ₹{p:,.2f}; 20-day average ₹{sma20:,.2f}; 60-day average ₹{sma60:,.2f}.'}


def costs(notional, brokerage=0.0005, slippage=0.001):
    """Configurable approximation per side; verify actual Indian charges separately."""
    return notional * (brokerage + slippage)


def simulate(rows, news=None, initial=100000, allocation=0.1, fee=0.0005, slippage=0.001):
    """Decision on day t close, execution at next day's open approximation: next day's close.
    Daily inputs have no open field. A conservative next-close model avoids same-bar fills.
    """
    cash, units, entry, trades, equity = float(initial), 0, None, [], []
    if not (initial > 0 and 0 < allocation <= 1 and fee >= 0 and slippage >= 0):
        raise ValueError('Invalid initial capital, allocation, or costs')
    for i, row in enumerate(rows):
        if i >= 61:
            action = signal(rows, i-1, news)
            price = row['close']
            if action == 'SELL' and units:
                proceeds = units * price
                cash += proceeds - costs(proceeds, fee, slippage)
                trades.append(dict(date=str(row['date']), side='SELL', units=units, price=price, net_cash=round(proceeds-costs(proceeds, fee, slippage),2)))
                units, entry = 0, None
            elif action == 'BUY' and units == 0:
                budget = min(cash, (cash + units * price) * allocation)
                qty = math.floor(budget / (price * (1 + fee + slippage)))
                if qty:
                    spent = qty * price
                    cash -= spent + costs(spent, fee, slippage)
                    units, entry = qty, price
                    trades.append(dict(date=str(row['date']), side='BUY', units=qty, price=price, net_cash=round(-spent-costs(spent,fee,slippage),2)))
        equity.append(dict(date=str(row['date']), equity=round(cash + units*row['close'],2)))
    peak, maxdd = 0, 0
    for point in equity:
        peak = max(peak, point['equity'])
        maxdd = min(maxdd, point['equity']/peak-1)
    result = equity[-1]['equity']
    return dict(start=str(rows[0]['date']), end=str(rows[-1]['date']), initial=initial, final_equity=result,
                return_pct=round((result/initial-1)*100,2), max_drawdown_pct=round(maxdd*100,2),
                buy_hold_pct=round((rows[-1]['close']/rows[0]['close']-1)*100,2),
                trades=trades, equity_curve=equity, open_units=units)



def fetch_kite(symbol, token, start, end, output):
    """Fetch daily historical candles by instrument token, not ticker string."""
    import kite_sdk
    candles = kite_sdk.daily_candles(token, start, end)
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date','open','high','low','close','volume'])
        for c in candles:
            writer.writerow([str(c['date'])[:10], c['open'], c['high'], c['low'], c['close'], c['volume']])
    return len(candles)


def propose(rows, news, symbol, state_path):
    action = signal(rows, len(rows)-1, news)
    state = json.loads(pathlib.Path(state_path).read_text()) if pathlib.Path(state_path).exists() else {}
    held = int(state.get(symbol, 0))
    if action == 'BUY' and held or action == 'SELL' and not held:
        action = 'HOLD'
    return dict(symbol=symbol, asof=str(rows[-1]['date']), action=action, last_close=rows[-1]['close'], held_units=held,
                news_score=news.get(rows[-1]['date'],0), warning='Signal is research, not a prediction or guaranteed return')


def paper_step(rows, news, symbol, state_path, initial=100000, allocation=.1):
    """One paper update per dated candle; signal is queued for next session close."""
    path = pathlib.Path(state_path)
    state = json.loads(path.read_text()) if path.exists() else dict(cash=initial, holdings={}, pending={}, last_date={}, journal=[])
    state.setdefault('holdings', {}); state.setdefault('pending', {}); state.setdefault('last_date', {}); state.setdefault('journal', [])
    today = str(rows[-1]['date'])
    if state['last_date'].get(symbol) == today:
        return dict(status='already_processed', date=today, cash=state['cash'], holdings=state['holdings'])
    price = rows[-1]['close']
    pending = state['pending'].pop(symbol, None)
    held = int(state['holdings'].get(symbol, 0))
    if pending == 'SELL' and held:
        gross = held * price
        state['cash'] += gross - costs(gross)
        state['holdings'][symbol] = 0
        state['journal'].append(dict(date=today,symbol=symbol,side='SELL',units=held,price=price))
    elif pending == 'BUY' and not held:
        budget = min(state['cash'], initial*allocation)
        qty = math.floor(budget / (price*1.0015))
        if qty:
            gross = qty*price
            state['cash'] -= gross+costs(gross)
            state['holdings'][symbol] = qty
            state['journal'].append(dict(date=today,symbol=symbol,side='BUY',units=qty,price=price))
    action = signal(rows,len(rows)-1,news)
    held = int(state['holdings'].get(symbol,0))
    if action == 'BUY' and not held or action == 'SELL' and held:
        state['pending'][symbol] = action
    state['last_date'][symbol] = today
    path.parent.mkdir(parents=True,exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(state,indent=2)); temp.replace(path)
    return dict(date=today,signal=action,pending_next_session=state['pending'].get(symbol),
                cash=round(state['cash'],2),holdings=state['holdings'],last_trade=state['journal'][-1] if state['journal'] else None)


def live_order(symbol, side, quantity, limit_price, confirmation):
    """Explicit opt-in; limit-only, cash equity, quantity cap, order-status verification."""
    if os.getenv('ENABLE_LIVE_TRADING') != 'YES':
        raise RuntimeError('Live trading disabled. Set ENABLE_LIVE_TRADING=YES explicitly')
    if side not in ('BUY','SELL') or not (0 < quantity <= 10) or limit_price <= 0 or quantity*limit_price > 5000:
        raise ValueError('Allowed: BUY/SELL, 1–10 shares, max ₹5,000 notional')
    if confirmation != f'{side}:{symbol}:{quantity}:{limit_price}':
        raise ValueError('Confirmation must match SIDE:SYMBOL:QTY:LIMIT_PRICE exactly')
    if not symbol.isascii() or not symbol.replace('-','').isalnum():
        raise ValueError('Invalid symbol')
    import kite_sdk
    order_id = str(kite_sdk.place_limit_order(symbol, side, quantity, limit_price))
    history = kite_sdk.order_history(order_id)
    return dict(order_id=order_id, order_history=history, note='Inspect latest order status; submission alone is not execution')


def main():
    parser = argparse.ArgumentParser(description='Equity research, backtest, and guarded Kite orders')
    subs = parser.add_subparsers(dest='command',required=True)
    for name in ('backtest','signal','paper'):
        p = subs.add_parser(name)
        p.add_argument('--csv',required=True)
        p.add_argument('--news')
        if name == 'paper':
            p.add_argument('--symbol',required=True)
            p.add_argument('--state',default=str(ROOT/'paper.json'))
            p.add_argument('--initial',type=float,default=100000)
            p.add_argument('--allocation',type=float,default=.1)
        elif name == 'backtest':
            p.add_argument('--initial',type=float,default=100000)
            p.add_argument('--allocation',type=float,default=.1)
            p.add_argument('--output')
        else:
            p.add_argument('--symbol',required=True)
            p.add_argument('--state',default=str(ROOT/'positions.json'))
    p = subs.add_parser('fetch')
    for arg in ('symbol','instrument-token','start','end','output'):
        p.add_argument('--'+arg,required=True)
    p = subs.add_parser('order')
    p.add_argument('--symbol',required=True); p.add_argument('--side',required=True)
    p.add_argument('--quantity',type=int,required=True); p.add_argument('--limit-price',type=float,required=True)
    p.add_argument('--confirm',required=True)
    a = parser.parse_args()
    if a.command == 'fetch':
        value = dict(symbol=a.symbol, count=fetch_kite(a.symbol,a.instrument_token,a.start,a.end,a.output))
    elif a.command == 'order':
        value = live_order(a.symbol,a.side,a.quantity,a.limit_price,a.confirm)
    else:
        rows, news = load_candles(a.csv), load_news(a.news)
        if a.command == 'paper':
            value = paper_step(rows,news,a.symbol,a.state,a.initial,a.allocation)
        elif a.command == 'signal':
            value = propose(rows,news,a.symbol,a.state)
        else:
            value = simulate(rows,news,a.initial,a.allocation)
            if a.output:
                pathlib.Path(a.output).write_text(json.dumps(value,indent=2))
                value = {k:v for k,v in value.items() if k not in ('trades','equity_curve')}
    print(json.dumps(value,indent=2))


if __name__ == '__main__':
    main()
