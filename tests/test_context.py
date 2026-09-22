import datetime as dt
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import context


class ContextTests(unittest.TestCase):
    def test_engulfing_uses_complete_bodies(self):
        rows=[{'open':110,'close':100},{'open':99,'close':111}]
        self.assertEqual(context.candle_pattern(rows)['name'],'Bullish engulfing')
        self.assertEqual(context.candle_pattern([{'open':100,'close':110},
            {'open':111,'close':99}])['name'],'Bearish engulfing')

    def test_news_falls_back_after_gdelt_ssl_failure(self):
        now=dt.datetime(2026,9,22,10)
        article={'title':'Company announces expansion','url':'https://example.test','date':'x'}
        with patch.object(context,'_gdelt',side_effect=TimeoutError('SSL handshake timed out')), \
             patch.object(context,'_google_news',return_value=[article]), \
             patch.object(context.time,'sleep'):
            result=context.headlines('Example Company',now)
        self.assertEqual(result['articles'][0]['title'],article['title'])
        self.assertIn('Google News fallback',result['reason'])
