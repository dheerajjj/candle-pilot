"""One-click Windows paper-trading launcher for Candle Pilot."""
import datetime as dt
import json
import pathlib
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

import credentials
import kite_sdk
import autopilot

ROOT = pathlib.Path(__file__).resolve().parent
WATCHLIST = ('INFY', 'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK')


def paper_config():
    """Resolve current NSE tokens using Kite instead of asking the user for token IDs."""
    kite = kite_sdk.client()
    instruments = {str(i['tradingsymbol']): int(i['instrument_token'])
                   for i in kite.instruments('NSE') if i.get('exchange') == 'NSE'}
    held = [str(h['tradingsymbol']) for h in kite.holdings() if h.get('exchange') == 'NSE']
    symbols = list(dict.fromkeys(held + list(WATCHLIST)))[:10]
    missing = [s for s in symbols if s not in instruments]
    if missing:
        raise RuntimeError('NSE symbols unavailable in Kite instruments: ' + ', '.join(missing))
    config = dict(mode='paper', stocks=[dict(symbol=s,instrument_token=instruments[s]) for s in symbols],
                  max_order_inr=5000,max_daily_buy_inr=5000)
    return config


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Candle Pilot · Paper mode')
        self.root.geometry('540x240')
        self.root.resizable(False,False)
        tk.Label(self.root,text='Candle Pilot',font=('Segoe UI',18,'bold')).pack(pady=(20,8))
        tk.Label(self.root,text='One-time API setup, then official Kite login each trading day.',wraplength=480).pack()
        self.status = tk.StringVar(value='Ready. Paper mode only; no real orders.')
        tk.Label(self.root,textvariable=self.status,wraplength=480).pack(pady=20)
        self.button = tk.Button(self.root,text='Connect Kite and run paper agent',command=self.start)
        self.button.pack()
        self.root.after(200,self.setup_if_missing)

    def setup_if_missing(self):
        try:
            store = credentials.vault()
            for field,label in [('api_key','Kite Connect API key'),('api_secret','Kite Connect API secret')]:
                if not store.get_password(credentials.SERVICE,field):
                    value = simpledialog.askstring('One-time setup',label+' (from Zerodha developer app):',
                                                   parent=self.root,show='*')
                    if not value or not value.strip() or any(c.isspace() for c in value.strip()):
                        self.status.set('Setup incomplete. Reopen Candle Pilot to try again.')
                        return
                    store.set_password(credentials.SERVICE,field,value.strip())
            self.status.set('API credentials saved in Windows Credential Manager. Ready for Kite login.')
        except Exception as exc:
            messagebox.showerror('Setup error',str(exc),parent=self.root)

    def start(self):
        self.button.config(state='disabled')
        self.status.set('Waiting for official Kite login in your browser…')
        threading.Thread(target=self.worker,daemon=True).start()

    def worker(self):
        try:
            credentials.login_browser()
            self.root.after(0,lambda:self.status.set('Login complete. Checking your paper watchlist…'))
            now = dt.datetime.now(autopilot.IST)
            if now.weekday() >= 5 or not (dt.time(9,20) <= now.time() <= dt.time(14,55)):
                raise RuntimeError('Login succeeded. Run again on a weekday between 09:20 and 14:55 IST to make a paper decision.')
            config = paper_config()
            report = autopilot.run(config,ROOT/'autopilot_state.json',now=now)
            summary = '\n'.join(f"{x['symbol']}: {x['action']}" for x in report)
            self.root.after(0,lambda:messagebox.showinfo('Paper decision',summary,parent=self.root))
            self.root.after(0,lambda:self.status.set('Paper decision recorded. No real orders were sent.'))
        except Exception as exc:
            error=str(exc)
            self.root.after(0,lambda:messagebox.showerror('Candle Pilot',error,parent=self.root))
            self.root.after(0,lambda:self.status.set('No trade placed. '+error))
        finally:
            self.root.after(0,lambda:self.button.config(state='normal'))

    def run(self):
        self.root.mainloop()


if __name__=='__main__':
    App().run()
