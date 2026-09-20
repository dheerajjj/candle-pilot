import datetime as dt
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import intraday


class IntradayTests(unittest.TestCase):
    def test_incomplete_candle_is_not_used(self):
        now=dt.datetime(2024,3,1,10,1,tzinfo=intraday.IST)
        def candle(hour,minute,close):
            return {'date':dt.datetime(2024,3,1,hour,minute,tzinfo=intraday.IST),
                    'high':close+1,'low':close-1,'close':close,'volume':100}
        bars=[candle(9,45,100),candle(9,50,101),candle(10,0,40)]
        with patch.object(intraday.kite_sdk,'five_minute_candles',return_value=bars):
            result=intraday.assess(1,now,101)
        self.assertTrue(result['up'])
        self.assertIn('09:50',result['reason'])

    def test_stale_candles_fail_closed(self):
        now=dt.datetime(2024,3,1,11,0,tzinfo=intraday.IST)
        bars=[{'date':dt.datetime(2024,3,1,9,m,tzinfo=intraday.IST),
               'high':101,'low':99,'close':100,'volume':100} for m in (15,20)]
        with patch.object(intraday.kite_sdk,'five_minute_candles',return_value=bars):
            with self.assertRaises(ValueError):
                intraday.assess(1,now,100)
