import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import autopilot


class AutopilotTests(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2024,3,1,10,0,tzinfo=autopilot.IST)
        self.config={'mode':'paper','stocks':[{'symbol':'INFY','instrument_token':408065}],
                     'max_order_inr':5000,'max_daily_buy_inr':5000}
        start=self.now.date()-dt.timedelta(days=80)
        self.rows=[]
        for i in range(80):
            p=100+i+(5 if i==79 else 0)
            self.rows.append(dict(date=start+dt.timedelta(days=i),close=p,
                                  high=p+1,low=p-1,volume=200 if i==79 else 100))
        self.broker={'history':lambda token,now:self.rows,'quote':lambda symbol:185,
                     'existing_orders':lambda:[],'holdings':lambda:{},'funds':lambda:100000}
        self.broker['market']=lambda now:{'up':True,'reason':'Index is above prior close and 50-day average.'}
        self.broker['news']=lambda company,now:{'articles':[{'title':'Routine company update'}],
            'flagged':[],'reason':'One recent matching headline; not a sentiment claim.'}

    def test_automatic_paper_buy_and_idempotent_rerun(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'state.json'
            first=autopilot.run(self.config,path,self.now,self.broker)
            self.assertEqual(first[0]['action'],'BUY')
            self.assertGreater(first[0]['quantity'],0)
            self.assertEqual(first[0]['price'],185)
            self.assertIn('20-day high',first[0]['reason'])
            self.assertEqual(autopilot.run(self.config,path,self.now,self.broker)[0]['action'],'SKIP')
            state=json.loads(path.read_text())
            self.assertGreater(state['paper_holdings']['INFY'],0)

    def test_live_requires_explicit_switch_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'state.json'
            config={**self.config,'mode':'live'}
            with patch.dict('os.environ',{'ENABLE_LIVE_TRADING':'NO'}):
                with self.assertRaises(RuntimeError):
                    autopilot.run(config,path,self.now,self.broker)
            with patch.dict('os.environ',{'ENABLE_LIVE_TRADING':'YES'}):
                with patch.object(autopilot.kite_sdk,'place_limit_order',side_effect=TimeoutError('ambiguous')):
                    with self.assertRaises(TimeoutError):
                        autopilot.run(config,path,self.now,self.broker)
                self.assertEqual(autopilot.run(config,path,self.now,self.broker)[0]['action'],'SKIP')

    def test_weekend_stops_before_broker(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):
                autopilot.run(self.config,pathlib.Path(d)/'state.json',
                    self.now+dt.timedelta(days=1),self.broker)

    def test_missing_news_withholds_buy(self):
        with tempfile.TemporaryDirectory() as d:
            broker={**self.broker,'news':lambda company,now:(_ for _ in ()).throw(TimeoutError('offline'))}
            result=autopilot.run(self.config,pathlib.Path(d)/'state.json',self.now,broker)
            self.assertEqual(result[0]['action'],'SKIP')
            self.assertEqual(result[0]['quantity'],0)
            self.assertIn('News unavailable',result[0]['reason'])


if __name__=='__main__': unittest.main()
