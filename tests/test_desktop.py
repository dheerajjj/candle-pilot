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
    def test_watchlist_resolved_from_kite_in_paper_mode(self):
        with patch.object(desktop.kite_sdk,'client',return_value=FakeClient()):
            config=desktop.paper_config()
        self.assertEqual(config['mode'],'paper')
        self.assertEqual(len(config['stocks']),len(desktop.WATCHLIST))
        self.assertEqual(config['stocks'][0]['instrument_token'],100)
        self.assertLessEqual(config['max_order_inr'],5000)


if __name__=='__main__': unittest.main()
