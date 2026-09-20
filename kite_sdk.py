"""Official pykiteconnect integration. Credentials come from Windows Credential Manager."""
from credentials import get_value


def client():
    from kiteconnect import KiteConnect
    key, token = get_value('api_key'), get_value('access_token')
    if not key or not token:
        raise RuntimeError('Run python credentials.py setup and python credentials.py login first')
    kite = KiteConnect(api_key=key)
    kite.set_access_token(token)
    return kite


def daily_candles(instrument_token, start, end):
    return client().historical_data(int(instrument_token), start, end, 'day')


def five_minute_candles(instrument_token, start, end):
    return client().historical_data(int(instrument_token), start, end, '5minute')


def current_quote(symbol):
    return client().quote('NSE:'+symbol)['NSE:'+symbol]


def orders():
    return client().orders()


def order_history(order_id):
    return client().order_history(str(order_id))


def holdings():
    return client().holdings()


def available_cash():
    data = client().margins('equity')
    # Raw cash can exceed spendable cash when other margins have been used.
    return max(0.0,min(float(data['net']),float(data['available']['live_balance']),
                       float(data['available']['cash'])))


def place_limit_order(symbol, side, quantity, price, tag=None):
    kite = client()
    params = dict(variety=kite.VARIETY_REGULAR, exchange=kite.EXCHANGE_NSE,
                  tradingsymbol=symbol, transaction_type=side, quantity=quantity,
                  product=kite.PRODUCT_CNC, order_type=kite.ORDER_TYPE_LIMIT,
                  price=price, validity=kite.VALIDITY_DAY)
    if tag is not None:
        params['tag'] = tag
    return kite.place_order(**params)
