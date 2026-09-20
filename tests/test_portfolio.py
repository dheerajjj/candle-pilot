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
                'intraday':lambda token,now,price:{'up':True,'reason':'Completed 5-minute candles support quote'},
                'news':lambda company,now:{'articles':[{'title':'Routine company update'}],
                                          'flagged':[],'reason':'One current headline'}}
        config={'stocks':[{'symbol':s,'instrument_token':i,'company':s}
                          for i,s in enumerate(('INFY','TCS'))]}
        config['stocks'][0]['company']='Infosys Limited'
        report=portfolio.recommend(config,now,source)
        self.assertEqual([x['quantity'] for x in report['items']],[10,10])
        self.assertLessEqual(report['proposed'],report['budget'])
        self.assertEqual(report['cash'],10000)
        self.assertEqual(report['items'][0]['company'],'Infosys Limited')

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
                'intraday':lambda token,now,price:{'up':True,'reason':'Intraday clear'},
                'news':lambda company,now:(_ for _ in ()).throw(TimeoutError('offline'))}
        result=portfolio.recommend({'stocks':[{'symbol':'INFY','instrument_token':1}]},now,source)
        self.assertEqual(result['proposed'],0)
        self.assertEqual(result['items'][0]['action'],'SKIP')

    def test_missing_intraday_candles_withhold_buy(self):
        now=dt.datetime(2024,3,1,10,tzinfo=autopilot.IST)
        bars=[]
        for i in range(80):
            p=100+i+(5 if i==79 else 0)
            bars.append(dict(date=now.date()-dt.timedelta(days=80-i),open=p-.5,
                high=p+1,low=p-1,close=p,volume=200 if i==79 else 100))
        source={'cash':lambda:10000,'holdings':lambda:[],
                'market':lambda now:{'up':True,'reason':'Index up'},
                'history':lambda token,now:bars,'quote':lambda symbol:185,
                'intraday':lambda token,now,price:(_ for _ in ()).throw(ValueError('stale')),
                'news':lambda company,now:self.fail('Do not fetch news after intraday failure')}
        result=portfolio.recommend({'stocks':[{'symbol':'INFY','instrument_token':1}]},now,source)
        self.assertEqual(result['items'][0]['action'],'SKIP')
        self.assertEqual(result['proposed'],0)

    def test_existing_holding_shows_sell_review_with_actual_quantity(self):
        now=dt.datetime(2024,3,1,10,tzinfo=autopilot.IST)
        bars=[dict(date=now.date()-dt.timedelta(days=80-i),open=202-i,
                   high=203-i,low=200-i,close=201-i,volume=100) for i in range(80)]
        source={'cash':lambda:10000,
                'holdings':lambda:[{'exchange':'NSE','tradingsymbol':'INFY','quantity':7}],
                'market':lambda now:{'up':False,'reason':'Index below average'},
                'history':lambda token,now:bars,'quote':lambda symbol:122,
                'news':lambda company,now:self.fail('News is unnecessary for an exit review')}
        report=portfolio.recommend({'stocks':[{'symbol':'INFY','instrument_token':1}]},now,source)
        self.assertEqual(report['items'][0]['action'],'SELL')
        self.assertEqual(report['items'][0]['quantity'],7)
        self.assertEqual(report['proposed'],0)


if __name__=='__main__': unittest.main()
