"""Read-only context for paper decisions; missing inputs fail closed for new buys."""
import datetime as dt
import json
import urllib.parse
import urllib.request

RISK_WORDS = ('fraud', 'probe', 'investigation', 'default', 'bankruptcy',
              'insolvency', 'downgrade', 'penalty', 'lawsuit', 'resign')


def market(now):
    import kite_sdk
    quote = kite_sdk.client().quote('NSE:NIFTY 50')['NSE:NIFTY 50']
    token = int(quote['instrument_token'])
    prior = float(quote['ohlc']['close'])
    current = float(quote['last_price'])
    if prior <= 0 or current <= 0:
        raise ValueError('Invalid NIFTY 50 quote')
    bars = kite_sdk.daily_candles(token, now.date()-dt.timedelta(days=100), now.date()-dt.timedelta(days=1))
    closes = [float(b['close']) for b in bars if str(b['date'])[:10] < str(now.date())]
    if len(closes) < 50 or (now.date()-dt.date.fromisoformat(str(bars[-1]['date'])[:10])).days > 4:
        raise ValueError('NIFTY 50 history missing or stale')
    avg50 = sum(closes[-50:])/50
    return {'up':current >= prior and current >= avg50,
            'reason':f'NIFTY 50 ₹{current:,.2f}; previous close ₹{prior:,.2f}; 50-day average ₹{avg50:,.2f}.'}


def headlines(company, now):
    """Search recent public headlines; never infer article contents from a title."""
    if not company or len(company) > 100:
        raise ValueError('Company name required for news lookup')
    query = urllib.parse.urlencode({'query':'"'+company.replace('"','')+'"',
                                    'mode':'artlist','format':'json','timespan':'2d',
                                    'sort':'datedesc','maxrecords':'10'})
    req = urllib.request.Request('https://api.gdeltproject.org/api/v2/doc/doc?'+query,
                                 headers={'User-Agent':'CandlePilot/0.3 personal-research'})
    with urllib.request.urlopen(req,timeout=8) as response:
        data = json.load(response)
    articles = data.get('articles',[])
    if not isinstance(articles,list):
        raise ValueError('Unexpected news response')
    relevant = []
    for item in articles:
        title = str(item.get('title','')).strip()
        seen = str(item.get('seendate',''))
        if not title or not seen or dt.datetime.strptime(seen[:15],'%Y%m%dT%H%M%S').date() < now.date()-dt.timedelta(days=2):
            continue
        relevant.append({'title':title[:180], 'url':str(item.get('url',''))[:500], 'date':seen})
    flagged = [x for x in relevant if any(word in x['title'].lower() for word in RISK_WORDS)]
    return {'articles':relevant[:5], 'flagged':flagged[:3],
            'reason':('Headline needs human review: '+flagged[0]['title'] if flagged else
                      f'{len(relevant)} recent matching headline(s); headlines are not verified sentiment.')}


def candle_pattern(rows):
    """A modest two-candle heuristic, not a predictive candlestick model."""
    if len(rows) < 2 or 'open' not in rows[-1] or 'open' not in rows[-2]:
        return {'name':'Unavailable','bullish':False,'reason':'Open prices unavailable for candle pattern.'}
    a,b=rows[-2],rows[-1]
    ao,ac,bo,bc=(float(a[k]) for a,k in ((a,'open'),(a,'close'),(b,'open'),(b,'close')))
    if ac < ao and bc > bo and bo <= ac and bc >= ao:
        return {'name':'Bullish engulfing','bullish':True,'reason':'Last completed green body covered the previous red body.'}
    if ac > ao and bc < bo and bo >= ac and bc <= ao:
        return {'name':'Bearish engulfing','bullish':False,'reason':'Last completed red body covered the previous green body.'}
    return {'name':'No engulfing pattern','bullish':False,'reason':'No two-candle engulfing pattern in completed daily candles.'}
