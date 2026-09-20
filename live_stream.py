"""Single read-only KiteTicker stream for visible desktop prices."""
import math
import queue

from credentials import get_value


class LivePrices:
    def __init__(self, tokens, ticker_factory=None):
        self.tokens=sorted({int(t) for t in tokens})
        self.events=queue.Queue(maxsize=300)
        self.ticker=None
        self.ticker_factory=ticker_factory
        self.closed=False

    def _offer(self, event):
        if self.closed:
            return
        try:
            self.events.put_nowait(event)
        except queue.Full:
            try:
                self.events.get_nowait()
                self.events.put_nowait(event)
            except queue.Empty:
                pass

    def start(self):
        if not self.tokens:
            return
        if self.ticker_factory is None:
            from kiteconnect import KiteTicker
            self.ticker_factory=KiteTicker
        key=get_value('api_key')
        token=get_value('access_token')
        if not key or not token:
            raise RuntimeError('Kite login is required for live quotes')
        ws=self.ticker_factory(key,token)
        self.ticker=ws

        def connected(socket,response):
            socket.subscribe(self.tokens)
            socket.set_mode(socket.MODE_LTP,self.tokens)
            self._offer(('status','Live prices connected'))

        def ticks(socket,items):
            for item in items:
                try:
                    instrument=int(item['instrument_token'])
                    price=float(item['last_price'])
                except (KeyError,TypeError,ValueError):
                    continue
                if instrument in self.tokens and math.isfinite(price) and price>0:
                    self._offer(('tick',instrument,price))

        ws.on_connect=connected
        ws.on_ticks=ticks
        ws.on_close=lambda socket,code,reason:self._offer(('status','Live prices disconnected; displayed quotes may be stale'))
        ws.on_error=lambda socket,code,reason:self._offer(('status','Live price connection error; rerun analysis to reconnect'))
        ws.on_reconnect=lambda socket,count:self._offer(('status','Reconnecting live prices…'))
        ws.on_noreconnect=lambda socket:self._offer(('status','Live prices unavailable; rerun analysis later'))
        ws.connect(threaded=True)

    def stop(self):
        self.closed=True
        if self.ticker is not None:
            self.ticker.close()
