"""Discover NSE cash equities and shortlist liquid names for deeper checks."""
import math
import time

import kite_sdk

MAX_QUOTES = 400
MAX_DEEP_RESEARCH = 12


def shortlist(kite=None, pause=time.sleep):
    kite = kite or kite_sdk.client()
    instruments = [i for i in kite.instruments('NSE')
                   if i.get('exchange')=='NSE' and i.get('segment')=='NSE'
                   and i.get('instrument_type')=='EQ' and i.get('tradingsymbol')
                   and i.get('name') and int(i.get('instrument_token',0))>0]
    if not instruments:
        raise RuntimeError('No NSE equity instruments returned; screening stopped')
    instruments = list({str(i['tradingsymbol']):i for i in instruments}.values())
    by_symbol={i['tradingsymbol']:i for i in instruments}
    held_symbols=[h['tradingsymbol'] for h in kite.holdings()
                  if h.get('exchange')=='NSE' and int(h.get('quantity') or 0)>0]
    held_items=[by_symbol[s] for s in dict.fromkeys(held_symbols) if s in by_symbol]
    quote_map={}
    for start in range(0,len(instruments),MAX_QUOTES):
        if start:
            pause(1.1)
        symbols=['NSE:'+i['tradingsymbol'] for i in instruments[start:start+MAX_QUOTES]]
        quote_map.update(kite.quote(symbols))
    liquid=[]
    for item in instruments:
        quote=quote_map.get('NSE:'+item['tradingsymbol'])
        if not quote:
            continue
        price=float(quote.get('last_price') or 0)
        volume=float(quote.get('volume') or 0)
        close=float((quote.get('ohlc') or {}).get('close') or 0)
        if not all(math.isfinite(x) for x in (price,volume,close)) or close<=0:
            continue
        change=price/close-1
        # Cash shares affordable within the per-stock cap; exclude thin and extreme quotes.
        if 50<=price<=2475 and volume*price>=20_000_000 and -.08<=change<=.08:
            liquid.append((volume*price,item))
    if len(quote_map)<len(instruments)*.5:
        raise RuntimeError('Most NSE quotes unavailable; refusing an incomplete market screen')
    liquid.sort(key=lambda pair:pair[0],reverse=True)
    held_set={i['tradingsymbol'] for i in held_items}
    new_items=[item for _,item in liquid if item['tradingsymbol'] not in held_set][:MAX_DEEP_RESEARCH]
    stocks=[{'symbol':item['tradingsymbol'],'instrument_token':int(item['instrument_token']),
             'company':item['name'],'owned':item['tradingsymbol'] in held_set}
            for item in held_items+new_items]
    if not stocks:
        raise RuntimeError('No stocks passed liquidity and price screen today')
    return {'stocks':stocks,'universe':len(instruments),'quoted':len(quote_map),
            'eligible':len(liquid),'held_count':len(held_items),
            'new_count':len(new_items),'deep_count':len(stocks)}
