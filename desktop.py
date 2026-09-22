"""One-click Windows paper-trading launcher for Candle Pilot."""
import datetime as dt
import json
import pathlib
import queue
import time
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

import credentials
import kite_sdk
import autopilot
import portfolio
import screener
import live_stream

ROOT = pathlib.Path(__file__).resolve().parent
WATCHLIST = ('INFY', 'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK')
COLORS = {'BUY':'#087a56','SELL':'#b44739','HOLD':'#3e5a83','WATCH':'#9a6700','SKIP':'#73588c'}


def decision_text(item):
    """Keep a missing price distinct from a real zero-priced trade."""
    price = item.get('price', item.get('paper_price'))
    price_label = f'₹{price:,.2f} ({item.get("price_type", "quote")})' if price is not None else 'Unavailable'
    qty_label = ('You own' if item.get('owned') else 'Suggested quantity')
    cost = item.get('estimated_cost')
    cost_label = f'   •   Estimated cost: ₹{cost:,.2f}' if cost is not None else ''
    return f'{qty_label}: {item.get("quantity", 0)}   •   Price: {price_label}{cost_label}', item.get('reason', 'No reason available.')


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
        window.geometry('900x720')
        window.configure(bg='#f3f6fb')
        window.transient(self.root)
        window.focus_set()
        tk.Label(window,text='Your holdings and new ideas',font=('Segoe UI',20,'bold'),
                 bg='#f3f6fb',fg='#172b4d').pack(anchor='w',padx=22,pady=(18,2))
        tk.Label(window,text=f'AVAILABLE ₹{report["cash"]:,.2f}     SUGGESTED ₹{report["proposed"]:,.2f}     KEPT ASIDE ₹{report.get("reserve",0):,.2f}',
                 font=('Segoe UI',11,'bold'),bg='#f3f6fb',fg='#087a56').pack(anchor='w',padx=23,pady=(4,2))
        buy_message=(f'{report.get("buy_count",0)} qualified BUY idea(s) are sized from your current available balance.'
                     if report.get('buy_count') else
                     'No stock cleared every safety check now. Funds remain unallocated; WATCH is not a buy instruction.')
        tk.Label(window,text=buy_message,font=('Segoe UI',10,'bold'),bg='#f3f6fb',
                 fg='#9a6700' if not report.get('buy_count') else '#087a56').pack(anchor='w',padx=23,pady=(2,2))
        funds=report.get('funds',{})
        tk.Label(window,text=(f'Opening balance: ₹{funds.get("opening_balance",0):,.2f}  •  Raw cash: ₹{funds.get("raw_cash",0):,.2f}  •  '
                              f'Utilised debits: ₹{funds.get("utilised_debits",0):,.2f}  •  Collateral: ₹{funds.get("collateral",0):,.2f}'),
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23,pady=(2,2))
        tk.Label(window,text=f'NSE holdings value: ₹{report.get("holdings_value",0):,.2f}  •  Holdings P&L: ₹{report.get("holdings_pnl",0):,.2f}',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23,pady=(0,2))
        screen=report.get('screen',{})
        tk.Label(window,text=f'NSE equities: {screen.get("universe",0):,}  •  Quoted: {screen.get("quoted",0):,}  •  Holdings: {screen.get("held_count",0)}  •  New candidates: {screen.get("new_count",0)}',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23,pady=(2,2))
        tk.Label(window,text='Daily + completed 5-minute candles · NIFTY 50 · recent headlines',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23)
        tk.Label(window,text='Research suggestions only. Headlines can be inaccurate; no real orders are placed.',
                 font=('Segoe UI',10),bg='#f3f6fb',fg='#52647c').pack(anchor='w',padx=23,pady=(2,12))
        stream_status=tk.StringVar(value='Connecting live Kite prices…')
        tk.Label(window,textvariable=stream_status,font=('Segoe UI',10),bg='#f3f6fb',
                 fg='#52647c',wraplength=700).pack(anchor='w',padx=23,pady=(0,8))
        filter_bar=tk.Frame(window,bg='#f3f6fb')
        filter_bar.pack(fill='x',padx=22,pady=(0,8))
        canvas = tk.Canvas(window,bg='#f3f6fb',highlightthickness=0)
        scrollbar = tk.Scrollbar(window,command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right',fill='y',pady=(0,18))
        canvas.pack(side='left',fill='both',expand=True,padx=(22,0),pady=(0,18))
        cards = tk.Frame(canvas,bg='#f3f6fb')
        canvas.create_window((0,0),window=cards,anchor='nw',width=838)
        cards.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        labels={}
        initial={item['symbol']:item.get('price') for item in report['items']}
        last_tick={}
        live_price={}
        def section(title, subtitle):
            tk.Label(cards,text=title,font=('Segoe UI',15,'bold'),bg='#f3f6fb',fg='#172b4d',
                     anchor='w').pack(fill='x',pady=(8,0))
            tk.Label(cards,text=subtitle,font=('Segoe UI',9),bg='#f3f6fb',fg='#52647c',
                     anchor='w').pack(fill='x',pady=(0,7))

        def add_card(item):
            card = tk.Frame(cards,bg='white',highlightbackground='#dce3ed',highlightthickness=1)
            card.pack(fill='x',pady=(0,10))
            header = tk.Frame(card,bg='white')
            header.pack(fill='x',padx=16,pady=(12,3))
            tk.Label(header,text=item['symbol'],font=('Segoe UI',13,'bold'),
                     bg='white',fg='#172b4d').pack(side='left')
            tk.Label(header,text=item['action'],font=('Segoe UI',11,'bold'),
                     bg='white',fg=COLORS.get(item['action'],'#52647c')).pack(side='right')
            if item.get('company') and item['company']!=item['symbol']:
                tk.Label(card,text=item['company'],font=('Segoe UI',10),bg='white',fg='#52647c',
                         anchor='w',wraplength=800).pack(fill='x',padx=16,pady=(0,3))
            detail, reason = decision_text(item)
            tk.Label(card,text=detail,font=('Segoe UI',10,'bold'),bg='white',fg='#253b5a',
                     anchor='w').pack(fill='x',padx=16,pady=(0,3))
            tk.Label(card,text='DECISION  '+reason,font=('Segoe UI',10),bg='white',fg='#52647c',
                     justify='left',anchor='w',wraplength=800).pack(fill='x',padx=16,pady=(0,7))
            tk.Label(card,text='NEWS  '+item.get('news_status','Unavailable'),font=('Segoe UI',9),
                     bg='#f7f9fc',fg='#52647c',justify='left',anchor='w',wraplength=800
                     ).pack(fill='x',padx=16,pady=(0,5))
            for headline in item.get('headlines',[])[:2]:
                tk.Label(card,text='• '+headline['title'],font=('Segoe UI',9),bg='white',fg='#334e68',
                         justify='left',anchor='w',wraplength=800).pack(fill='x',padx=20,pady=(0,3))
            current=live_price.get(item['symbol'])
            live_label=tk.StringVar(value=(f'LIVE ₹{current:,.2f}' if current is not None
                                           else 'Live price: waiting for tick…'))
            tk.Label(card,textvariable=live_label,font=('Segoe UI',10),bg='white',fg='#087a56',
                     anchor='w').pack(fill='x',padx=16,pady=(0,10))
            labels[item['symbol']]=live_label

        buttons={}
        def render(action='ALL'):
            for child in cards.winfo_children():
                child.destroy()
            labels.clear()
            for name,button in buttons.items():
                selected=name==action
                button.configure(bg=COLORS.get(name,'#172b4d') if selected else 'white',
                                 fg='white' if selected else COLORS.get(name,'#172b4d'))
            if action=='ALL':
                section('Your Kite holdings','Only positive-quantity Kite holdings. HOLD and SELL belong here.')
                owned=report.get('holding_items',[])
                if owned:
                    for item in owned:
                        add_card(item)
                else:
                    tk.Label(cards,text='No positive-quantity NSE holdings returned by Kite.',bg='white',
                             fg='#52647c',anchor='w').pack(fill='x',pady=(0,10),ipadx=14,ipady=12)
                section('New market opportunities','BUY shows quantity and cost. WATCH means observe only.')
                for item in report.get('idea_items',[]):
                    add_card(item)
            else:
                explanations={'BUY':'Qualified new opportunities with funds-based quantities.',
                              'SELL':'Owned shares whose exit rule triggered; review before acting.',
                              'HOLD':'Shares you currently own that do not trigger the exit rule.',
                              'WATCH':'New shares to monitor; these are not buy instructions.'}
                selected=[item for item in report['items'] if item['action']==action]
                section(action,explanations[action])
                if selected:
                    for item in selected:
                        add_card(item)
                else:
                    tk.Label(cards,text=f'No {action} decisions in this analysis.',font=('Segoe UI',11),
                             bg='white',fg='#52647c',anchor='w').pack(fill='x',ipadx=16,ipady=18)
            canvas.yview_moveto(0)

        counts={name:sum(item['action']==name for item in report['items'])
                for name in ('BUY','SELL','HOLD','WATCH')}
        for name in ('ALL','BUY','SELL','HOLD','WATCH'):
            count=len(report['items']) if name=='ALL' else counts[name]
            button=tk.Button(filter_bar,text=f'{name}  {count}',font=('Segoe UI',10,'bold'),
                             relief='flat',bd=0,padx=16,pady=8,
                             command=lambda value=name:render(value))
            button.pack(side='left',padx=(0,7))
            buttons[name]=button
        render('BUY' if counts['BUY'] else 'ALL')
        token_to_symbol={int(stock['instrument_token']):stock['symbol']
                         for stock in screen.get('stocks',[])
                         if stock['symbol'] in {item['symbol'] for item in report['items']}}
        stream=live_stream.LivePrices(token_to_symbol)
        def close_window():
            stream.stop()
            window.destroy()
        window.protocol('WM_DELETE_WINDOW',close_window)
        window.bind('<Destroy>',lambda event:stream.stop() if event.widget is window else None)
        try:
            stream.start()
        except Exception as exc:
            stream_status.set('Live prices unavailable: '+str(exc))
            return

        def refresh_ticks():
            if not window.winfo_exists():
                return
            try:
                while True:
                    event=stream.events.get_nowait()
                    if event[0]=='status':
                        stream_status.set(event[1])
                    elif event[0]=='tick' and event[1] in token_to_symbol:
                        symbol=token_to_symbol[event[1]]
                        price=event[2]
                        baseline=initial.get(symbol)
                        changed=baseline is not None and baseline>0 and abs(price/baseline-1)>.01
                        if symbol in labels:
                            labels[symbol].set(f'LIVE ₹{price:,.2f}'+('  •  Moved >1%: rerun analysis' if changed else ''))
                        last_tick[symbol]=time.monotonic()
                        live_price[symbol]=price
            except queue.Empty:
                pass
            for symbol,seen in last_tick.items():
                if symbol in labels and time.monotonic()-seen>60:
                    labels[symbol].set(f'Last received price: ₹{live_price[symbol]:,.2f}  •  No tick for 60 s; may be stale')
            window.after(500,refresh_ticks)
        window.after(500,refresh_ticks)

    def run(self):
        self.root.mainloop()


if __name__=='__main__':
    App().run()
