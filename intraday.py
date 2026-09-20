"""Completed five-minute candles supplement daily buy analysis."""
import datetime as dt
import math

import kite_sdk

IST = dt.timezone(dt.timedelta(hours=5,minutes=30))


def assess(token, now, quote):
    now=now.astimezone(IST)
    start=dt.datetime.combine(now.date(),dt.time(9,15),tzinfo=IST)
    raw=kite_sdk.five_minute_candles(token,start,now)
    completed=[]
    for bar in raw:
        stamp=bar['date']
        if isinstance(stamp,str):
            stamp=dt.datetime.fromisoformat(stamp)
        if stamp.tzinfo is None:
            raise ValueError('Intraday candle timestamp has no time zone')
        stamp=stamp.astimezone(IST)
        # Kite candle timestamps mark their START. Allow 30 s for completion.
        if stamp.date()!=now.date() or stamp<start or stamp+dt.timedelta(minutes=5,seconds=30)>now:
            continue
        completed.append((stamp,float(bar['close']),float(bar['high']),float(bar['low']),float(bar['volume'])))
    completed.sort(key=lambda x:x[0])
    if len(completed)<2 or now-completed[-1][0]>dt.timedelta(minutes=21):
        raise ValueError('Two recent completed 5-minute candles unavailable')
    last=completed[-1]
    price=float(quote)
    volume=sum(x[4] for x in completed)
    if not math.isfinite(price) or price<=0 or volume<=0:
        raise ValueError('Invalid intraday price or volume')
    typical=sum(((x[2]+x[3]+x[1])/3)*x[4] for x in completed)/volume
    up=price>=last[1]*.99 and price>=typical*.995 and last[1]>=completed[-2][1]*.98
    reason=(f'Completed 5-minute candles through {last[0].strftime("%H:%M")} IST: '
            f'current quote ₹{price:,.2f}, latest close ₹{last[1]:,.2f}, '
            f'volume-weighted typical price ₹{typical:,.2f}.')
    return {'up':up,'reason':reason}
