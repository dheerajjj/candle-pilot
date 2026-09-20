import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import screener


class FakeKite:
    def instruments(self,exchange):
        return [dict(exchange='NSE',segment='NSE',instrument_type='EQ',
                     tradingsymbol='NEWCO',name='New Company',instrument_token=42),
                dict(exchange='NSE',segment='NSE',instrument_type='ETF',
                     tradingsymbol='FUND',name='Fund',instrument_token=43)]
    def quote(self,keys):
        assert keys==['NSE:NEWCO']
        return {'NSE:NEWCO':{'last_price':100,'volume':250000,'ohlc':{'close':99}}}
    def holdings(self): return []


class ScreenerTests(unittest.TestCase):
    def test_discovers_new_nse_stock_without_watchlist(self):
        result=screener.shortlist(kite=FakeKite(),pause=lambda _:None)
        self.assertEqual(result['universe'],1)
        self.assertEqual(result['stocks'][0]['symbol'],'NEWCO')

    def test_includes_existing_holding(self):
        class HeldKite(FakeKite):
            def holdings(self): return [{'exchange':'NSE','tradingsymbol':'NEWCO','quantity':4}]
        result=screener.shortlist(kite=HeldKite(),pause=lambda _:None)
        self.assertEqual(result['held_count'],1)
        self.assertEqual(result['new_count'],0)
        self.assertEqual([s['symbol'] for s in result['stocks']],['NEWCO'])


if __name__=='__main__': unittest.main()
