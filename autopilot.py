"""Candle Pilot scheduled daily runner. Requires a valid Kite Connect session."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import pathlib

from agent import signal_details
import kite_sdk

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
STATE = pathlib.Path('autopilot_state.json')


def config_load(path):
    config = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    if config.get('mode') not in ('paper', 'live'):
        raise ValueError('mode must be paper or live')
    if not config.get('stocks') or len(config['stocks']) > 10:
        raise ValueError('Configure 1–10 NSE cash stocks')
    if len({s['symbol'] for s in config['stocks']}) != len(config['stocks']):
        raise ValueError('Duplicate symbols')
    for s in config['stocks']:
        if not s['symbol'].isalnum() or not isinstance(s['instrument_token'], int):
            raise ValueError('Stocks need an NSE symbol and numeric instrument_token')
    if not 0 < config['max_order_inr'] <= 5000 or not 0 < config['max_daily_buy_inr'] <= 5000:
        raise ValueError('Order and daily buy caps must be ≤ ₹5,000')
    return config


def atomic_save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    tmp.replace(path)


def history(token, now):
    # Exclude today's partial candle. Kite timestamps use India local dates.
    end = now.date() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=180)
    raw = kite_sdk.daily_candles(token, start, end)
    rows = [dict(date=dt.date.fromisoformat(str(c['date'])[:10]), high=float(c['high']),
                 low=float(c['low']), close=float(c['close']), volume=float(c['volume'])) for c in raw]
    if len(rows) < 65 or (end - rows[-1]['date']).days > 4:
        raise RuntimeError('Historical candles insufficient or stale; no order placed')
    return rows


def quote(symbol):
    item = kite_sdk.current_quote(symbol)
    last = float(item['last_price'])
    if last <= 0:
        raise RuntimeError('Invalid market quote')
    return last


def existing_orders():
    return kite_sdk.orders()


def holdings():
    return {x['tradingsymbol']: int(x['quantity']) for x in kite_sdk.holdings()}


def funds():
    return kite_sdk.available_cash()


def run(config, state_path=STATE, now=None, broker=None):
    """Exactly one decision per symbol per date; uncertain submissions require manual reconciliation."""
    now = now or dt.datetime.now(IST)
    if now.tzinfo is None:
        raise ValueError('Provide timezone-aware datetime')
    now = now.astimezone(IST)
    if now.weekday() >= 5 or not (dt.time(9, 20) <= now.time() <= dt.time(14, 55)):
        raise RuntimeError('Run only weekdays 09:20–14:55 IST; exchange holidays are checked via quote freshness manually')
    broker = broker or globals()
    state_path = pathlib.Path(state_path)
    state = json.loads(state_path.read_text()) if state_path.exists() else {'paper_holdings': {}, 'paper_cash': 100000, 'attempts': {}}
    state.setdefault('attempts', {}); state.setdefault('paper_holdings', {})
    state.setdefault('paper_cash', 100000)
    if config['mode'] == 'live' and os.getenv('ENABLE_LIVE_TRADING') != 'YES':
        raise RuntimeError('Live mode requires ENABLE_LIVE_TRADING=YES')
    prior = broker['existing_orders']() if config['mode'] == 'live' else []
    held = broker['holdings']() if config['mode'] == 'live' else state['paper_holdings']
    available = broker['funds']() if config['mode'] == 'live' else state['paper_cash']
    spent_today = sum(x.get('notional',0) for x in state['attempts'].values()
                      if x.get('day') == str(now.date()) and x.get('side') == 'BUY')
    output = []
    for stock in config['stocks']:
        symbol = stock['symbol']
        rows = broker['history'](stock['instrument_token'], now)
        details = signal_details(rows, len(rows)-1)
        action = details['signal']
        reason = details['reason']
        prior_close = rows[-1]['close']
        key = f'{now.date()}:{symbol}'
        if key in state['attempts']:
            output.append({'symbol':symbol,'action':'SKIP','quantity':0,'price':None,'reason':'A paper action was already recorded for this stock today.'})
            continue
        qty_held = int(held.get(symbol,0))
        if action == 'HOLD' or action == 'BUY' and qty_held or action == 'SELL' and not qty_held:
            if action == 'BUY' and qty_held:
                reason = f'Buy signal, but already holding {qty_held} paper shares. '+reason
            elif action == 'SELL' and not qty_held:
                reason = 'Sell signal, but no paper shares to sell. '+reason
            output.append({'symbol':symbol,'action':'HOLD','signal':action,'quantity':0,'price':prior_close,'price_type':'previous close','reason':reason})
            continue
        price = broker['quote'](symbol)
        if abs(price/rows[-1]['close']-1) > .12:
            output.append({'symbol':symbol,'action':'SKIP','quantity':0,'price':price,'price_type':'current quote','reason':'Current quote moved more than 12% from the last completed close. '+reason})
            continue
        if action == 'BUY':
            budget = min(config['max_order_inr'],config['max_daily_buy_inr']-spent_today,available)
            qty = min(10,math.floor(budget/(price*1.01)))
        else:
            qty = min(10,qty_held)
        if qty < 1:
            output.append({'symbol':symbol,'action':'SKIP','quantity':0,'price':price,'price_type':'current quote','reason':'Insufficient paper budget or holdings. '+reason})
            continue
        tag = 'CP'+hashlib.sha256(key.encode()).hexdigest()[:18]
        if config['mode'] == 'live' and any(o.get('tag') == tag for o in prior):
            output.append({'symbol':symbol,'action':'SKIP','quantity':0,'price':price,'price_type':'current quote','reason':'Matching order already exists in Kite. '+reason})
            continue
        # Before any order POST, persist an intent. On timeouts, never auto retry.
        state['attempts'][key] = {'day':str(now.date()),'side':action,'quantity':qty,
                                  'notional':round(qty*price,2),'status':'intent_recorded'}
        atomic_save(state_path,state)
        if config['mode'] == 'paper':
            if action == 'BUY':
                state['paper_cash'] -= qty*price*1.0015
                state['paper_holdings'][symbol] = qty_held+qty
                spent_today += qty*price
            else:
                state['paper_cash'] += qty*price*.9985
                state['paper_holdings'][symbol] = qty_held-qty
            state['attempts'][key]['status'] = 'paper_filled'
            atomic_save(state_path,state)
            output.append({'symbol':symbol,'action':action,'quantity':qty,'paper_price':price,'price':price,'price_type':'simulated fill','reason':reason})
        else:
            limit = round(price*(1.005 if action == 'BUY' else .995),2)
            if action == 'BUY' and limit*qty > min(config['max_order_inr'],config['max_daily_buy_inr']-spent_today,available):
                state['attempts'][key]['status'] = 'limit_exceeded'
                atomic_save(state_path,state)
                output.append({'symbol':symbol,'action':'SKIP','quantity':0,'price':price,'price_type':'current quote','reason':'Limit price exceeds configured budget. '+reason})
                continue
            order_id = str(kite_sdk.place_limit_order(symbol, action, qty, limit, tag=tag))
            state['attempts'][key].update(status='submitted_unverified',order_id=order_id)
            atomic_save(state_path,state)
            output.append({'symbol':symbol,'action':action,'quantity':qty,'order_id':order_id,
                           'price':limit,'price_type':'submitted limit','reason':reason,
                           'note':'Check Kite order status and fills; no automatic retry'})
            if action == 'BUY':
                spent_today += qty*limit
    return output


def main():
    parser=argparse.ArgumentParser(description='Scheduled Candle Pilot daily run')
    parser.add_argument('--config',default='autopilot_config.json')
    parser.add_argument('--state',default='autopilot_state.json')
    args=parser.parse_args()
    print(json.dumps(run(config_load(args.config),args.state),indent=2))


if __name__=='__main__':
    main()
