import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import desktop


class FakeClient:
    def instruments(self,exchange):
        assert exchange=='NSE'
        return [{'exchange':'NSE','tradingsymbol':symbol,'instrument_token':i+100}
                for i,symbol in enumerate(desktop.WATCHLIST)]
    def holdings(self): return []


class DesktopTests(unittest.TestCase):
    def test_decision_text_distinguishes_simulated_fill_from_previous_close(self):
        detail,reason=desktop.decision_text({'action':'BUY','quantity':2,'price':150.25,
            'price_type':'simulated fill','reason':'Breakout'})
        self.assertIn('2',detail)
        self.assertIn('150.25 (simulated fill)',detail)
        self.assertEqual(reason,'Breakout')
        detail,_=desktop.decision_text({'action':'HOLD','quantity':0,'price':100,
            'price_type':'previous close'})
        self.assertIn('previous close',detail)

    def test_full_market_shortlist_used_for_desktop(self):
        sample={'stocks':[{'symbol':'OTHER','instrument_token':100,'company':'Other Co'}],
                'universe':2000,'quoted':1900,'eligible':100,'deep_count':1}
        with patch.object(desktop.screener,'shortlist',return_value=sample):
            config=desktop.paper_config()
        self.assertEqual(config['mode'],'paper')
        self.assertEqual(config['universe'],2000)
        self.assertEqual(len(config['stocks']),1)
        self.assertEqual(config['stocks'][0]['instrument_token'],100)
        self.assertLessEqual(config['max_order_inr'],5000)


if __name__=='__main__': unittest.main()
