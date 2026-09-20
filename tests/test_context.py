import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import context


class ContextTests(unittest.TestCase):
    def test_engulfing_uses_complete_bodies(self):
        rows=[{'open':110,'close':100},{'open':99,'close':111}]
        self.assertEqual(context.candle_pattern(rows)['name'],'Bullish engulfing')
        self.assertEqual(context.candle_pattern([{'open':100,'close':110},
            {'open':111,'close':99}])['name'],'Bearish engulfing')
