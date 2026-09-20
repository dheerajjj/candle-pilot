import pathlib
import sys
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import kite_sdk


class FakeKite:
    VARIETY_REGULAR='regular'; EXCHANGE_NSE='NSE'; PRODUCT_CNC='CNC'
    ORDER_TYPE_LIMIT='LIMIT'; VALIDITY_DAY='DAY'
    def __init__(self,api_key): self.key=api_key
    def set_access_token(self,value): self.token=value
    def historical_data(self,*args): return [{'date':'2026-09-18','close':100,'open':99,'high':101,'low':98,'volume':100}]
    def quote(self,keys): return {'NSE:INFY':{'last_price':101}}
    def holdings(self): return [{'tradingsymbol':'INFY','quantity':1}]
    def orders(self): return []
    def margins(self,segment): return {'available':{'cash':1000}}
    def place_order(self,**kwargs):
        assert kwargs['order_type']=='LIMIT' and kwargs['product']=='CNC'
        return 'order_123'
    def order_history(self,order_id): return [{'order_id':order_id,'status':'OPEN'}]


class AdapterTests(unittest.TestCase):
    def test_sdk_queries_and_limit_order(self):
        with patch.dict(sys.modules,{'kiteconnect':types.SimpleNamespace(KiteConnect=FakeKite)}), \
             patch('kite_sdk.get_value',side_effect=['api','token']*7):
            self.assertEqual(kite_sdk.daily_candles(408065,'2026-01-01','2026-09-18')[0]['close'],100)
            self.assertEqual(kite_sdk.current_quote('INFY')['last_price'],101)
            self.assertEqual(kite_sdk.holdings()[0]['quantity'],1)
            self.assertEqual(kite_sdk.orders(),[])
            self.assertEqual(kite_sdk.available_cash(),1000)
            self.assertEqual(kite_sdk.place_limit_order('INFY','BUY',1,100,tag='CPtest'),'order_123')
            self.assertEqual(kite_sdk.order_history('order_123')[0]['status'],'OPEN')


if __name__=='__main__': unittest.main()
