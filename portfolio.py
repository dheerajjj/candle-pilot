"""Read-only, budgeted paper suggestions. Never calls an order endpoint."""
import datetime as dt
import math
import statistics

import autopilot
import context
import kite_sdk
from agent import signal_details


def recommend(config, now=None, source=None):
    now = now or dt.datetime.now(autopilot.IST)
    now = now.astimezone(autopilot.IST)
    if now.weekday() >= 5 or not (dt.time(9,20) <= now.time() <= dt.time(14,55)):
        raise ValueError('Run on a weekday during market hours, 09:20–14:55 IST')
    source = source or {'cash':kite_sdk.available_cash,'holdings':kite_sdk.holdings,
        'market':context.market,'history':autopilot.history,'quote':autopilot.quote,'news':context.headlines}
    cash = float(source['cash']())
    if not math.isfinite(cash) or cash < 0:
        raise ValueError('Kite available funds unavailable; no recommendations made')
    held = {x['tradingsymbol']:int(x['quantity']) for x in source['holdings']() if x.get('exchange')=='NSE'}
    market = source['market'](now)
    if 'up' not in market or 'reason' not in market:
        raise ValueError('Market data unavailable; no recommendations made')
    rows_out = []
    candidates = []
    for stock in config['stocks']:
        symbol = stock['symbol']
        try:
            bars = source['history'](stock['instrument_token'],now)
            detail = signal_details(bars,len(bars)-1)
            candle = context.candle_pattern(bars)
            price = float(source['quote'](symbol))
            if not math.isfinite(price) or price <= 0:
                raise ValueError('Invalid quote')
            eligible = (not held.get(symbol,0) and detail['signal']=='BUY' and market['up']
                        and candle['name']!='Bearish engulfing' and abs(price/bars[-1]['close']-1)<=.12)
            news = (source['news'](stock.get('company',symbol),now) if eligible else
                    {'articles':[],'reason':'Not requested because a technical, market, or holdings check did not clear.'})
            why = (f'{detail["reason"]} Candle: {candle["name"]}. '
                   f'Market: {market["reason"]} News: {news["reason"]}')
            card = {'symbol':symbol,'action':'HOLD','quantity':0,'price':price,
                    'price_type':'current quote','reason':why,'headlines':news.get('articles',[])[:1]}
            if held.get(symbol,0)>0:
                card['reason']='Already held in Kite; no additional buy suggested. '+why
            elif detail['signal']!='BUY':
                card['reason']='Buy conditions did not clear. '+why
            elif not market['up'] or candle['name']=='Bearish engulfing':
                card['action']='SKIP'
                card['reason']='Buy withheld by market or candle check. '+why
            elif abs(price/bars[-1]['close']-1)>.12:
                card['action']='SKIP'
                card['reason']='Current price moved more than 12% from last close. '+why
            elif not news.get('articles') or news.get('flagged'):
                card['action']='SKIP'
                card['reason']='Buy withheld by missing news or headline review flag. '+why
            else:
                recent=bars[-1]
                prior_high=max(x['high'] for x in bars[-21:-1])
                avg_volume=statistics.mean(x['volume'] for x in bars[-21:-1])
                score=(recent['close']/prior_high-1)+(recent['volume']/avg_volume-1)*.02
                candidates.append((score,card))
                continue
            rows_out.append(card)
        except Exception as exc:
            rows_out.append({'symbol':symbol,'action':'SKIP','quantity':0,'price':None,
                             'reason':'Data or news unavailable; no buy suggested: '+str(exc)})
    # Keep half the account cash untouched, cap total at ₹5k and each name at ₹2.5k.
    limit=min(cash*.5,5000.0)
    remaining=limit
    for _,card in sorted(candidates,key=lambda item:item[0],reverse=True):
        price=card['price']
        budget=min(2500.0,remaining)
        qty=min(10,math.floor(budget/(price*1.01)))
        if qty:
            card['action']='BUY'
            card['quantity']=qty
            card['reason']=f'Proposed {qty} shares within ₹2,500 per stock and total ₹{limit:,.2f} budget. '+card['reason']
            remaining-=qty*price*1.01
        else:
            card['action']='SKIP'
            card['reason']='Not enough remaining recommendation budget for one share. '+card['reason']
        rows_out.append(card)
    rows_out.sort(key=lambda item:(item['action']!='BUY', item['symbol']))
    return {'cash':cash,'budget':limit,'proposed':sum(r['quantity']*r['price'] for r in rows_out if r['action']=='BUY'),
            'items':rows_out}
