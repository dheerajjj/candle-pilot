import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import portfolio
import autopilot


class PortfolioTests(unittest.TestCase):
    def test_two_buy_suggestions_respect_actual_cash_and_do_not_order(self):
        now=dt.datetime(2024,3,1,10,tzinfo=autopilot.IST)
        bars=[]
        for i in range(80):
            p=100+i+(5 if i==79 else 0)
            bars.append(dict(date=now.date()-dt.timedelta(days=80-i),open=p-.5,
                             high=p+1,low=p-1,close=p,volume=200 if i==79 else 100))
        source={'cash':lambda:10000,'holdings':lambda:[],
                'market':lambda now:{'up':True,'reason':'Index up'},
                'history':lambda token,now:bars,'quote':lambda symbol:185,
                'news':lambda company,now:{'articles':[{'title':'Routine company update'}],
                                          'flagged':[],'reason':'One current headline'}}
        config={'stocks':[{'symbol':s,'instrument_token':i,'company':s}
                          for i,s in enumerate(('INFY','TCS'))]}
        report=portfolio.recommend(config,now,source)
        self.assertEqual([x['quantity'] for x in report['items']],[10,10])
        self.assertLessEqual(report['proposed'],report['budget'])
        self.assertEqual(report['cash'],10000)

    def test_news_outage_disables_a_buy(self):
        now=dt.datetime(2024,3,1,10,tzinfo=autopilot.IST)
        bars=[]
        for i in range(80):
            p=100+i+(5 if i==79 else 0)
            bars.append(dict(date=now.date()-dt.timedelta(days=80-i),open=p-.5,
                             high=p+1,low=p-1,close=p,volume=200 if i==79 else 100))
        source={'cash':lambda:10000,'holdings':lambda:[],
                'market':lambda now:{'up':True,'reason':'Index up'},
                'history':lambda token,now:bars, 'quote':lambda symbol:185,
                'news':lambda company,now:(_ for _ in ()).throw(TimeoutError('offline'))}
        result=portfolio.recommend({'stocks':[{'symbol':'INFY','instrument_token':1}]},now,source)
        self.assertEqual(result['proposed'],0)
        self.assertEqual(result['items'][0]['action'],'SKIP')


if __name__=='__main__': unittest.main()
