"""Read-only, budgeted paper suggestions. Never calls an order endpoint."""
import datetime as dt
import math
import statistics

import autopilot
import context
import kite_sdk
import intraday
from agent import signal_details


def recommend(config, now=None, source=None):
    now = now or dt.datetime.now(autopilot.IST)
    now = now.astimezone(autopilot.IST)
    if now.weekday() >= 5 or not (dt.time(9,20) <= now.time() <= dt.time(14,55)):
        raise ValueError('Run on a weekday during market hours, 09:20–14:55 IST')
    source = source or {'funds':kite_sdk.funds_details,'holdings':kite_sdk.holdings,
        'market':context.market,'history':autopilot.history,'quote':autopilot.quote,
        'news':context.headlines,'intraday':intraday.assess}
    if 'funds' in source:
        funds = dict(source['funds']())
        cash = float(funds['available'])
    else:
        cash = float(source['cash']())
        funds = {'available':cash,'net':cash,'raw_cash':cash,'opening_balance':cash,
                 'intraday_payin':0.0,'collateral':0.0,'utilised_debits':0.0}
    if not math.isfinite(cash) or cash < 0:
        raise ValueError('Kite available funds unavailable; no recommendations made')
    holding_rows = source['holdings']()
    held = {x['tradingsymbol']:int(x.get('quantity') or 0) for x in holding_rows
            if x.get('exchange')=='NSE' and int(x.get('quantity') or 0)>0}
    holdings_value = sum(float(x.get('last_price') or x.get('average_price') or 0)*int(x.get('quantity') or 0)
                         for x in holding_rows if x.get('exchange')=='NSE')
    holdings_pnl = sum(float(x.get('pnl') or 0) for x in holding_rows if x.get('exchange')=='NSE')
    market = source['market'](now)
    if 'up' not in market or 'reason' not in market:
        raise ValueError('Market data unavailable; no recommendations made')
    rows_out = []
    candidates = []
    for stock in config['stocks']:
        symbol = stock['symbol']
        owned = held.get(symbol,0)>0
        try:
            bars = source['history'](stock['instrument_token'],now)
            detail = signal_details(bars,len(bars)-1)
            candle = context.candle_pattern(bars)
            price = float(source['quote'](symbol))
            if not math.isfinite(price) or price <= 0:
                raise ValueError('Invalid quote')
            try:
                news = source['news'](stock.get('company',symbol),now)
            except Exception as exc:
                news = {'articles':[],'flagged':[],
                        'reason':'News unavailable: '+str(exc),'unavailable':True}
            eligible = (not owned and detail['signal']=='BUY' and market['up']
                        and candle['name']!='Bearish engulfing' and abs(price/bars[-1]['close']-1)<=.12
                        and bool(news.get('articles')) and not news.get('flagged')
                        and not news.get('unavailable'))
            minutes=(source['intraday'](stock['instrument_token'],now,price) if eligible else
                     {'up':False,'reason':'Not required because earlier buy checks did not all clear.'})
            why = (f'{detail["reason"]} Candle: {candle["name"]}. '
                   f'Market: {market["reason"]} Intraday: {minutes["reason"]} News: {news["reason"]}')
            card = {'symbol':symbol,'company':stock.get('company',symbol),
                    'action':'HOLD' if owned else 'WATCH','owned':owned,
                    'quantity':held.get(symbol,0) if owned else 0,'price':price,
                    'price_type':'current quote','reason':why,
                    'technical':detail['reason'],'candle':candle['name'],
                    'market':market['reason'],'intraday':minutes['reason'],
                    'news_status':news['reason'],'headlines':news.get('articles',[])[:2]}
            if owned:
                if detail['signal']=='SELL':
                    card['action']='SELL'
                    card['quantity']=held[symbol]
                    card['reason']=f'Exit rule triggered for {held[symbol]} held share(s); review in Kite before acting. '+why
                else:
                    card['reason']=f'You own {held[symbol]} share(s). Hold/review; no additional buy suggested. '+why
            elif detail['signal']!='BUY':
                card['reason']='Watch only—buy conditions did not clear. '+why
            elif not market['up'] or candle['name']=='Bearish engulfing':
                card['reason']='Watch only—market or candle confirmation did not clear. '+why
            elif abs(price/bars[-1]['close']-1)>.12:
                card['reason']='Watch only—price moved more than 12% from last close. '+why
            elif not news.get('articles') or news.get('flagged') or news.get('unavailable'):
                card['reason']='Watch only—news confirmation is missing or needs review. '+why
            elif not minutes['up']:
                card['reason']='Watch only—completed 5-minute candle confirmation did not clear. '+why
            else:
                recent=bars[-1]
                prior_high=max(x['high'] for x in bars[-21:-1])
                avg_volume=statistics.mean(x['volume'] for x in bars[-21:-1])
                score=(recent['close']/prior_high-1)+(recent['volume']/avg_volume-1)*.02
                candidates.append((score,card))
                continue
            rows_out.append(card)
        except Exception as exc:
            rows_out.append({'symbol':symbol,'company':stock.get('company',symbol),
                             'action':'HOLD' if owned else 'WATCH','owned':owned,
                             'quantity':held.get(symbol,0) if owned else 0,'price':None,
                             'news_status':'Unavailable','headlines':[],
                             'reason':'Data unavailable; no buy suggested: '+str(exc)})
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
            card['estimated_cost']=qty*price
            card['reason']=f'Buy idea: {qty} share(s), sized from the ₹{cash:,.2f} available balance. '+card['reason']
            remaining-=qty*price*1.01
        else:
            card['action']='WATCH'
            card['reason']='Watch only—not enough remaining recommendation budget for one share. '+card['reason']
        rows_out.append(card)
    rows_out.sort(key=lambda item:(0 if item.get('owned') else 1,
                                  {'SELL':0,'HOLD':1,'BUY':0,'WATCH':1}.get(item['action'],2),item['symbol']))
    return {'cash':cash,'funds':funds,'holdings_value':holdings_value,'holdings_pnl':holdings_pnl,
            'budget':limit,'proposed':sum(r['quantity']*r['price'] for r in rows_out if r['action']=='BUY'),
            'reserve':cash-limit,'buy_count':sum(r['action']=='BUY' for r in rows_out),
            'holding_items':[r for r in rows_out if r.get('owned')],
            'idea_items':[r for r in rows_out if not r.get('owned')],
            'items':rows_out}
