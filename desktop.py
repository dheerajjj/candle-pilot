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
import portfolio
import screener

ROOT = pathlib.Path(__file__).resolve().parent
WATCHLIST = ('INFY', 'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK')
COLORS = {'BUY':'#087a56','SELL':'#b44739','HOLD':'#3e5a83','SKIP':'#73588c'}


def decision_text(item):
    """Keep a missing price distinct from a real zero-priced trade."""
    price = item.get('price', item.get('paper_price'))
    price_label = f'₹{price:,.2f} ({item.get("price_type", "quote")})' if price is not None else 'Unavailable'
    return f'Quantity: {item.get("quantity", 0)}   •   Price: {price_label}', item.get('reason', 'No reason available.')


def paper_config():
    result=screener.shortlist()
    return dict(mode='paper', **result, max_order_inr=5000,max_daily_buy_inr=5000)


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
        self.button = tk.Button(self.root,text='Connect Kite and see suggestions',command=self.start)
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
            self.root.after(0,lambda:self.status.set('Login complete. Screening NSE equities; this may take a minute…'))
            now = dt.datetime.now(autopilot.IST)
            if now.weekday() >= 5 or not (dt.time(9,20) <= now.time() <= dt.time(14,55)):
                raise RuntimeError('Login succeeded. Run again on a weekday between 09:20 and 14:55 IST to make a paper decision.')
            config = paper_config()
            report = portfolio.recommend(config,now=now)
            report['screen']=config
            self.root.after(0,lambda:self.show_report(report))
            self.root.after(0,lambda:self.status.set('Suggestions ready. No real orders were sent.'))
        except Exception as exc:
            error=str(exc)
            self.root.after(0,lambda:messagebox.showerror('Candle Pilot',error,parent=self.root))
            self.root.after(0,lambda:self.status.set('No trade placed. '+error))
        finally:
            self.root.after(0,lambda:self.button.config(state='normal'))

    def show_report(self, report):
        window = tk.Toplevel(self.root)
        window.title('Candle Pilot · Budgeted suggestions')
        window.geometry('780x650')
        window.configure(bg='#f3f6fb')
        window.transient(self.root)
        window.focus_set()
        tk.Label(window,text='Today’s buy suggestions',font=('Segoe UI',20,'bold'),
                 bg='#f3f6fb',fg='#172b4d').pack(anchor='w',padx=22,pady=(18,2))
        tk.Label(window,text=f'Kite available cash: ₹{report["cash"]:,.2f}    •    Suggested spend: ₹{report["proposed"]:,.2f}    •    Budget cap: ₹{report["budget"]:,.2f}',
                 font=('Segoe UI',11,'bold'),bg='#f3f6fb',fg='#087a56').pack(anchor='w',padx=23,pady=(4,2))
        screen=report.get('screen',{})
        tk.Label(window,text=f'NSE equities: {screen.get("universe",0):,}  •  Quoted: {screen.get("quoted",0):,}  •  Holdings: {screen.get("held_count",0)}  •  New candidates: {screen.get("new_count",0)}',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23,pady=(2,2))
        tk.Label(window,text='Daily candles · moving averages · breakout · volume · NIFTY 50 · recent headlines',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23)
        tk.Label(window,text='Research suggestions only. Headlines can be inaccurate; no real orders are placed.',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23,pady=(2,12))
        canvas = tk.Canvas(window,bg='#f3f6fb',highlightthickness=0)
        scrollbar = tk.Scrollbar(window,command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y',pady=(0,18))
        canvas.pack(side='left',fill='both',expand=True,padx=(22,0),pady=(0,18))
        cards = tk.Frame(canvas,bg='#f3f6fb')
        canvas.create_window((0,0),window=cards,anchor='nw',width=728)
        cards.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        for item in report['items']:
            card = tk.Frame(cards,bg='white',highlightbackground='#dce3ed',highlightthickness=1)
            card.pack(fill='x',pady=(0,10))
            header = tk.Frame(card,bg='white')
            header.pack(fill='x',padx=16,pady=(12,3))
            tk.Label(header,text=item['symbol'],font=('Segoe UI',13,'bold'),
                     bg='white',fg='#172b4d').pack(side='left')
            tk.Label(header,text=item['action'],font=('Segoe UI',11,'bold'),
                     bg='white',fg=COLORS.get(item['action'],'#52647c')).pack(side='right')
            detail, reason = decision_text(item)
            tk.Label(card,text=detail,font=('Segoe UI',10),bg='white',fg='#253b5a',
                     anchor='w').pack(fill='x',padx=16,pady=(0,3))
            tk.Label(card,text='Why: '+reason,font=('Segoe UI',10),bg='white',fg='#52647c',
                     justify='left',anchor='w',wraplength=690).pack(fill='x',padx=16,pady=(0,13))
            if item.get('headlines'):
                tk.Label(card,text='Recent headline: '+item['headlines'][0]['title'],font=('Segoe UI',9),
                         bg='white',fg='#52647c',justify='left',anchor='w',wraplength=690).pack(fill='x',padx=16,pady=(0,12))

    def run(self):
        self.root.mainloop()


if __name__=='__main__':
    App().run()
