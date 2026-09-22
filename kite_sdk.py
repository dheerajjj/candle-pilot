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


def funds_details():
    """Return normalized equity funds without confusing raw cash with current balance."""
    data = client().margins('equity')
    available = data.get('available') or {}
    utilised = data.get('utilised') or {}
    number = lambda value: float(value or 0)
    # Kite documents live_balance as the current available balance. available.cash
    # is the raw cash balance and must not be used as a lower bound: it can differ
    # from live_balance after debits, pay-ins, or other account adjustments.
    return {
        'enabled': bool(data.get('enabled', True)),
        'available': max(0.0, number(available.get('live_balance'))),
        'net': number(data.get('net')),
        'raw_cash': number(available.get('cash')),
        'opening_balance': number(available.get('opening_balance')),
        'intraday_payin': number(available.get('intraday_payin')),
        'collateral': number(available.get('collateral')),
        'utilised_debits': number(utilised.get('debits')),
    }


def available_cash():
    return funds_details()['available']


def place_limit_order(symbol, side, quantity, price, tag=None):
    kite = client()
    params = dict(variety=kite.VARIETY_REGULAR, exchange=kite.EXCHANGE_NSE,
                  tradingsymbol=symbol, transaction_type=side, quantity=quantity,
                  product=kite.PRODUCT_CNC, order_type=kite.ORDER_TYPE_LIMIT,
                  price=price, validity=kite.VALIDITY_DAY)
    if tag is not None:
        params['tag'] = tag
    return kite.place_order(**params)
