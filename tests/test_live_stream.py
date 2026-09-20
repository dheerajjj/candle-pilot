import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import live_stream


class FakeTicker:
    MODE_LTP='ltp'
    def __init__(self,key,token):
        self.key=key
        self.token=token
        self.closed=False
    def connect(self,threaded):
        assert threaded is True
        self.on_connect(self,None)
    def subscribe(self,tokens): self.subscriptions=tokens
    def set_mode(self,mode,tokens): self.mode=(mode,tokens)
    def close(self): self.closed=True


class StreamTests(unittest.TestCase):
    def test_subscribe_and_deliver_only_valid_subscribed_ticks(self):
        with patch.object(live_stream,'get_value',side_effect=['key','access']):
            stream=live_stream.LivePrices([42,42],ticker_factory=FakeTicker)
            stream.start()
        ticker=stream.ticker
        self.assertEqual(ticker.subscriptions,[42])
        ticker.on_ticks(ticker,[{'instrument_token':42,'last_price':125.5},
                                {'instrument_token':99,'last_price':140},
                                {'instrument_token':42,'last_price':float('nan')}])
        self.assertEqual(stream.events.get_nowait(),('status','Live prices connected'))
        self.assertEqual(stream.events.get_nowait(),('tick',42,125.5))
        self.assertTrue(stream.events.empty())
        stream.stop()
        self.assertTrue(ticker.closed)
