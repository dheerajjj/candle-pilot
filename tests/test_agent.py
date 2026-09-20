import datetime as dt
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import agent


def rows(n=100):
    start = dt.date(2024,1,1)
    return [dict(date=start+dt.timedelta(days=i),close=100+i,high=101+i,low=99+i,
                 volume=200 if i == 60 else 100) for i in range(n)]


class AgentTests(unittest.TestCase):
    def test_signal_does_not_see_future(self):
        first = rows(70)
        baseline = agent.signal(first,60)
        first[61]['close'] = 100000
        self.assertEqual(baseline,agent.signal(first,60))

    def test_breakout_following_day_fill(self):
        data = rows(70)
        data[60]['close'] += 5
        data[60]['high'] += 5
        self.assertEqual(agent.signal(data,60),'BUY')
        result = agent.simulate(data)
        self.assertEqual(result['trades'][0]['date'],str(data[61]['date']))
        self.assertEqual(result['trades'][0]['side'],'BUY')

    def test_no_same_bar_execution(self):
        result = agent.simulate(rows())
        self.assertTrue(all(t['date'] > str(rows()[60]['date']) for t in result['trades']))
        self.assertGreaterEqual(result['final_equity'],0)

    def test_paper_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp)/'portfolio.json'
            first = agent.paper_step(rows(65),{},'TEST',path)
            second = agent.paper_step(rows(65),{},'TEST',path)
            self.assertEqual(second['status'],'already_processed')
            self.assertEqual(first['cash'],second['cash'])

    def test_live_disabled_and_order_cap(self):
        with patch.dict('os.environ',{'ENABLE_LIVE_TRADING':'NO'}):
            with self.assertRaises(RuntimeError):
                agent.live_order('TEST','BUY',1,100,'BUY:TEST:1:100')
        with patch.dict('os.environ',{'ENABLE_LIVE_TRADING':'YES'}):
            with self.assertRaises(ValueError):
                agent.live_order('TEST','BUY',20,100,'BUY:TEST:20:100')

    def test_bad_candles_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file = pathlib.Path(temp)/'bad.csv'
            file.write_text('date,high,low,close,volume\n2024-01-01,2,1,3,100\n')
            with self.assertRaises(ValueError):
                agent.load_candles(file)


if __name__ == '__main__':
    unittest.main()
