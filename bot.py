import requests, time, html, datetime, pytz, random, json, os, threading
from flask import Flask

# ========== CREDENTIALS ==========
BOT_TOKEN = "8839565223:AAFW3u0H7GHPrzJMZAgaowPwKwOns0d2wXM"
CHAT_ID = "7020214660"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
STATE_FILE = "state.json"

# ========== KEEP ALIVE SERVER ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running 24/7"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# ========== SELF PING (EVERY 4 MIN) ==========
def self_ping():
    while True:
        time.sleep(240)
        try:
            requests.get("http://localhost:8080/", timeout=5)
        except:
            pass

# ========== EXCHANGE CONFIGS ==========
EXCHANGES = {
    "Binance": {"url":"https://fapi.binance.com/fapi/v1/premiumIndex","rk":"lastFundingRate","nk":"nextFundingTime","sk":"symbol"},
    "Bybit": {"url":"https://api.bybit.com/v5/market/tickers?category=linear","rk":"fundingRate","nk":"nextFundingTimestamp","sk":"symbol"},
    "OKX": {"url":"https://www.okx.com/api/v5/market/tickers?instType=SWAP","rk":"fundingRate","nk":"nextFundingTime","sk":"instId"},
    "Bitget": {"url":"https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES","rk":"fundingRate","nk":"nextFundingTime","sk":"symbol"},
}

TICKER_URLS = {
    "Binance": "https://fapi.binance.com/fapi/v1/ticker/24hr",
    "Bybit": "https://api.bybit.com/v5/market/tickers?category=linear",
    "OKX": "https://www.okx.com/api/v5/market/tickers?instType=SWAP",
    "Bitget": "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES",
}

REFRESH, COOLDOWN = 300, 1800
IST = pytz.timezone("Asia/Kolkata")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: return json.load(f)
        except: pass
    return {"s":{},"hl":0,"wl":"","st":time.time(),"at":{},"seen":[],"prices":{},"volumes":{},"changes":{},"alert_times":{},"wd":{"as":0,"liq":0,"fb":0,"fu":0,"lo":0,"so":0,"ic":0,"ie":0,"pa":0,"nl":0,"top":[],"peak":0},"history":[]}

def save_state():
    try:
        cutoff = time.time() - 604800
        state["history"] = [h for h in state.get("history",[]) if h.get("time",0) > cutoff]
        if len(state.get("history",[])) > 100: state["history"] = state["history"][-100:]
        with open(STATE_FILE+".tmp","w") as f: json.dump(state,f)
        os.replace(STATE_FILE+".tmp", STATE_FILE)
    except: pass

state = load_state()

def cs(r, e):
    r = r.strip().upper()
    if e == "OKX": r = r.replace("-USDT-SWAP","USDT")
    elif e == "Bitget": r = r.replace("_UMCBL","").replace("-USDT","USDT")
    r = r.replace("-USDT","USDT").replace("_USDT","USDT")
    return r if r.endswith("USDT") else r + "USDT"

def ge(s):
    m = {"BTC":"₿","ETH":"Ξ","SOL":"◎","XRP":"✕","DOGE":"🐕","LTC":"Ł","ADA":"₳","AVAX":"🔺","DOT":"●","LINK":"🔗","UNI":"🦄","MATIC":"🟣","SHIB":"🐕","ATOM":"⚛️","FIL":"🕸️","TRX":"⬡","ETC":"⟠","AAVE":"👻","ALGO":"🔆","NEAR":"🌙","FTM":"👻","SAND":"🏖️","MANA":"🌐","GALA":"🎮","RUNE":"ᚱ"}
    return m.get(s.replace("USDT",""),"💱")

def stg(t):
    for c in [t[i:i+3800] for i in range(0,len(t),3800)] if len(t)>4000 else [t]:
        for _ in range(3):
            try:
                r = requests.post(f"{BASE_URL}/sendMessage", json={"chat_id":CHAT_ID,"text":c,"parse_mode":"HTML","disable_web_page_preview":True}, timeout=10).json()
                if r.get("ok"): break
                if r.get("error_code")==429: time.sleep(10)
            except: time.sleep(2)

def fd(u): return requests.get(u, headers={"User-Agent":"Mozilla/5.0"}, timeout=10).json()

def ih(s):
    if s <= 0: return 0
    h = s / 3600
    if h < 1.5: return 1
    if h < 3: return 2
    if h < 6: return 4
    if h < 10: return 8
    if h < 18: return 12
    return 24

def ft(ts):
    if not ts or ts == 0: return "Pending"
    return datetime.datetime.fromtimestamp(ts,IST).strftime("%H:%M IST")

def fmt_settle(ts, nw):
    if not ts or ts <= nw: return "Pending"
    diff = ts - nw
    h, m = int(diff//3600), int((diff%3600)//60)
    return f"{h}h {m}m"

def can(at):
    nw = time.time()
    if nw - state.setdefault("at",{}).get(at,0) >= COOLDOWN:
        state["at"][at] = nw
        return True
    return False

def sig_stars(a, at, n):
    if at == "liq":
        if a > 0.003: return "⭐⭐⭐⭐⭐"
        if a > 0.001: return "⭐⭐⭐⭐"
        return "⭐⭐⭐"
    if at in ("fb","fu"):
        if abs(a) > 0.0003 or n >= 3: return "⭐⭐⭐⭐"
        return "⭐⭐⭐"
    if at in ("lo","so"):
        if a > 0.0005: return "⭐⭐⭐⭐⭐"
        if a > 0.0001: return "⭐⭐⭐⭐"
        return "⭐⭐⭐"
    if at == "pa":
        if a > 0.001 and n == 4: return "⭐⭐⭐⭐⭐"
        return "⭐⭐⭐⭐"
    if at in ("ic","ie"): return "⭐⭐⭐⭐" if n >= 3 else "⭐⭐⭐"
    if at == "nl": return "⭐⭐"
    return "⭐⭐⭐"

def calc_sl_tp(price, at, an):
    if price == 0: return 0, 0, 0
    if at in ("liq","so"): sl, tp = price*1.015, price*0.97
    elif at == "lo": sl, tp = price*0.985, price*1.03
    elif at == "fb": sl, tp = price*1.01, price*0.98
    elif at == "fu": sl, tp = price*0.99, price*1.02
    else: sl, tp = price*0.98, price*1.04
    rr = round(abs(tp-price)/abs(sl-price), 1) if abs(sl-price) > 0 else 2.0
    return round(sl,4), round(tp,4), rr

def update_prices():
    prices, volumes, changes = {}, {}, {}
    try:
        for ex, url in TICKER_URLS.items():
            try:
                if ex == "Binance":
                    for i in fd(url):
                        s = cs(i["symbol"], ex)
                        if s.endswith("USDT"):
                            prices[s] = float(i.get("lastPrice",0))
                            volumes[s] = float(i.get("quoteVolume",0))
                            changes[s] = float(i.get("priceChangePercent",0))
                elif ex == "Bybit":
                    for i in fd(url)["result"]["list"]:
                        s = cs(i["symbol"], ex)
                        if s.endswith("USDT"):
                            prices[s] = float(i.get("lastPrice",0))
                            volumes[s] = float(i.get("turnover24h",0))
                            changes[s] = float(i.get("price24hPcnt",0))*100
                elif ex == "OKX":
                    for i in fd(url)["data"]:
                        if i.get("instId","").endswith("-USDT-SWAP"):
                            s = cs(i["instId"], ex)
                            prices[s] = float(i.get("last",0))
                            volumes[s] = float(i.get("volCcy24h",0))
                            changes[s] = float(i.get("change24h",0))*100 if i.get("change24h") else 0
                elif ex == "Bitget":
                    for i in fd(url)["data"]:
                        s = cs(i.get("symbol",""), ex)
                        if s.endswith("USDT"):
                            prices[s] = float(i.get("lastPr",0))
                            volumes[s] = float(i.get("usdtVolume",0))
                            changes[s] = float(i.get("change24h",0))*100 if i.get("change24h") else 0
            except: pass
    except: pass
    state["prices"] = prices
    state["volumes"] = volumes
    state["changes"] = changes
    if volumes:
        max_vol = max(volumes.values()) if volumes else 0
        if max_vol > state["wd"].get("peak",0): state["wd"]["peak"] = max_vol

def gd():
    ad = {}
    for ex, c in EXCHANGES.items():
        try:
            if ex == "OKX":
                for i in fd(c["url"])["data"]:
                    if not i.get("instId","").endswith("-USDT-SWAP"): continue
                    s = cs(i["instId"],ex)
                    ad.setdefault(s,{})[ex] = {"r":float(i.get(c["rk"],0)),"n":int(i.get(c["nk"],"0"))/1000 if i.get(c["nk"]) else 0}
            elif ex == "Bitget":
                for i in fd(c["url"])["data"]:
                    s = cs(i.get(c["sk"],""),ex)
                    if not s.endswith("USDT"): continue
                    ad.setdefault(s,{})[ex] = {"r":float(i.get(c["rk"],0)),"n":int(i.get(c["nk"],"0"))/1000 if i.get(c["nk"]) else 0}
            elif ex == "Binance":
                for i in fd(c["url"]):
                    s = cs(i[c["sk"]],ex)
                    if not s.endswith("USDT"): continue
                    ad.setdefault(s,{})[ex] = {"r":float(i[c["rk"]]),"n":int(i[c["nk"]])/1000}
            elif ex == "Bybit":
                for i in fd(c["url"])["result"]["list"]:
                    s = cs(i[c["sk"]],ex)
                    ad.setdefault(s,{})[ex] = {"r":float(i[c["rk"]]),"n":int(i.get(c["nk"],0))/1000 if i.get(c["nk"]) else 0}
        except: pass
    return ad

def da(cur):
    ss = state.setdefault("s",{})
    seen = state.setdefault("seen",[])
    prices = state.get("prices",{})
    volumes = state.get("volumes",{})
    changes = state.get("changes",{})
    nw = time.time()
    groups = {"liq":[],"fb":[],"fu":[],"lo":[],"so":[],"ic":[],"ie":[],"pa":[],"nl":[]}

    for sym, ed in cur.items():
        if sym not in ss: ss[sym] = {"ex":{}}
        sst = ss[sym]
        sf, em = html.escape(sym), ge(sym)
        price = prices.get(sym, 0)
        vol = volumes.get(sym, 0)
        chg = changes.get(sym, 0)
        liq, fbd, fud, lod, sod, icd, ied = [], [], [], [], [], [], []

        for en, ei in ed.items():
            es = sst["ex"].setdefault(en,{"lr":0,"ln":0})
            r, nf, pr, pn = ei["r"], ei["n"], es["lr"], es["ln"]
            if abs(r) > 0.001: liq.append((en, r, nf))
            if pr != 0:
                if pr > 0 and r < 0 and abs(pr-r) >= 0.0001: fbd.append((en, pr, r, nf))
                elif pr < 0 and r > 0 and abs(r-pr) >= 0.0001: fud.append((en, pr, r, nf))
            if r < -0.0001: lod.append((en, pr, r, nf))
            if r > 0.0001: sod.append((en, pr, r, nf))
            if nf > nw and pn > 0:
                ci, pi = nf - nw, pn - (nw - REFRESH)
                if pi > 0:
                    ph, ch = ih(pi), ih(ci)
                    if ch < ph: icd.append((en, ph, ch, nf))
                    elif ch > ph: ied.append((en, ph, ch, nf))
            es["lr"], es["ln"] = r, nf

        def mk(at, dl):
            if not dl: return None, 0.0
            en_list = [x[0] for x in dl]
            n = len(en_list)
            es_str = ", ".join(en_list)
            nts = [x[3] for x in dl if x[3] > nw] if len(dl[0]) == 4 else [ed[e]["n"] for e in en_list if ed[e]["n"] > nw]
            nf = min(nts) if nts else 0
            settle = fmt_settle(nf, nw)
            if len(dl[0]) >= 3:
                an = sum(x[2] for x in dl)/len(dl)
                ap = sum(x[1] for x in dl)/len(dl) if at not in ("liq",) else None
            else:
                an = sum(x[1] for x in dl)/len(dl)
                ap = None
            a = abs(an)
            sl, tp, rr = calc_sl_tp(price, at, an)
            stars = sig_stars(a, at, n)
            
            if at == "liq":
                sev = "🚨 CRITICAL" if a>0.003 else ("🔴 EXTREME" if a>0.001 else "🟠 HIGH")
                dr = "🔴 SHORT" if an>0 else "🟢 LONG"
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ {sev} | 📊 {dr} | 🔥 {stars}\n📉 Rate: {an*100:.4f}% | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 Entry: ${price*0.995:,.2f}-${price*1.005:,.2f} | 🛑 SL: ${sl:,.2f} | ✅ TP: ${tp:,.2f} | R:R 1:{rr}\n⏳ {settle}", an
            elif at == "fb":
                sev = "🔴 EXTREME" if abs(ap-an)>0.0003 or n>=3 else ("🟠 HIGH" if abs(ap-an)>0.0001 else "🟡 MEDIUM")
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ {sev} | 📊 🔴 SHORT | 🔥 {stars}\n📉 {ap*100:.4f}% → {an*100:.4f}% | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 Entry: ${price*0.995:,.2f}-${price*1.005:,.2f} | 🛑 SL: ${sl:,.2f} | ✅ TP: ${tp:,.2f} | R:R 1:{rr}\n⏳ {settle}", 0.0
            elif at == "fu":
                sev = "🔴 EXTREME" if abs(an-ap)>0.0003 or n>=3 else ("🟠 HIGH" if abs(an-ap)>0.0001 else "🟡 MEDIUM")
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ {sev} | 📊 🟢 LONG | 🔥 {stars}\n📈 {ap*100:.4f}% → {an*100:.4f}% | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 Entry: ${price*0.995:,.2f}-${price*1.005:,.2f} | 🛑 SL: ${sl:,.2f} | ✅ TP: ${tp:,.2f} | R:R 1:{rr}\n⏳ {settle}", an
            elif at == "lo":
                sev = "🔴 EXTREME" if a>0.0005 else ("🟠 HIGH" if a>0.0001 else "🟡 MEDIUM")
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ {sev} | 📊 🟢 LONG | 🔥 {stars}\n📈 {ap*100:.2f}% → {an*100:.2f}% (SQUEEZE) | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 Entry: ${price*0.995:,.2f}-${price*1.005:,.2f} | 🛑 SL: ${sl:,.2f} | ✅ TP: ${tp:,.2f} | R:R 1:{rr}\n⏳ {settle}", an
            elif at == "so":
                sev = "🔴 EXTREME" if a>0.0005 else ("🟠 HIGH" if a>0.0001 else "🟡 MEDIUM")
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ {sev} | 📊 🔴 SHORT | 🔥 {stars}\n📉 {ap*100:.2f}% → {an*100:.2f}% (SQUEEZE) | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 Entry: ${price*0.995:,.2f}-${price*1.005:,.2f} | 🛑 SL: ${sl:,.2f} | ✅ TP: ${tp:,.2f} | R:R 1:{rr}\n⏳ {settle}", an
            elif at == "ic":
                ph, ch = dl[0][1], dl[0][2]
                return f"🪙 {em} {sf} | {en_list[0]} | 💰 ${price:,.2f}\n⚠️ 🟠 HIGH | 📊 NEUTRAL | 🔥 ⭐⭐⭐⭐\n⏱️ {ph}h → {ch}h (Reduced) | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 REDUCE LEVERAGE | ⏳ {settle}", 0.0
            elif at == "ie":
                ph, ch = dl[0][1], dl[0][2]
                return f"🪙 {em} {sf} | {en_list[0]} | 💰 ${price:,.2f}\n⚠️ 🟡 MEDIUM | 📊 NEUTRAL | 🔥 ⭐⭐⭐\n⏱️ {ph}h → {ch}h (Increased) | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 MAINTAIN POSITIONS | ⏳ {settle}", 0.0
            elif at == "pa":
                sev = "🚨 CRITICAL" if a>0.001 and n==4 else "💎 EXTREME"
                dr = "🟢 LONG" if an>0 else "🔴 SHORT"
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ {sev} | 📊 {dr} | 🔥 {stars}\n📊 Avg: {an*100:.4f}% | 📈 24h: {chg:+.2f}% | Vol: ${vol/1e6:.0f}M\n🎯 STRONG {'BUY' if an>0 else 'SELL'} | ⏳ {settle}", 0.0
            elif at == "nl":
                return f"🪙 {em} {sf} | {es_str} | 💰 ${price:,.2f}\n⚠️ 🔴 EXTREME | 📊 NO BIAS | 🔥 ⭐⭐\n🚨 HIGH VOLATILITY | 🎯 MONITOR ONLY | ⏳ Pending", 0.0
            return None, 0.0

        if liq: groups["liq"].append(mk("liq", liq))
        if fbd: groups["fb"].append(mk("fb", fbd))
        if fud: groups["fu"].append(mk("fu", fud))
        if lod: groups["lo"].append(mk("lo", lod))
        if sod: groups["so"].append(mk("so", sod))
        if icd: groups["ic"].append(mk("ic", icd))
        if ied: groups["ie"].append(mk("ie", ied))
        if len(ed) >= 3:
            rs = [e["r"] for e in ed.values()]
            if all(s==(1 if rs[0]>0 else -1) for s in [1 if r>0 else -1 for r in rs]) and abs(sum(rs)/len(rs)) > 0.0005:
                groups["pa"].append(mk("pa", [(list(ed.keys()), sum(rs)/len(rs), 0)]))
        if sym not in seen:
            seen.append(sym)
            groups["nl"].append(mk("nl", []))

    groups["lo"] = [x for x in groups["lo"] if x[0]]
    groups["so"] = [x for x in groups["so"] if x[0]]
    groups["lo"].sort(key=lambda x: x[1])
    groups["so"].sort(key=lambda x: x[1], reverse=True)

    titles = {"liq":("🚨 LIQUIDATION CASCADE","HIGH"),"fb":("🔴 FLIP TO BEARISH","HIGH"),"fu":("🟢 FLIP TO BULLISH","HIGH"),"lo":("🟢 LONG OPPORTUNITY","MEDIUM"),"so":("🔴 SHORT OPPORTUNITY","MEDIUM"),"ic":("⚠️ INTERVAL COMPRESS","MEDIUM"),"ie":("🔵 INTERVAL EXPAND","LOW"),"pa":("💎 PREMIUM ALPHA","HIGH"),"nl":("🆕 NEW LISTING","HIGH")}

    msgs = []
    for at, items in groups.items():
        valid = [(x[0], x[1]) for x in items if x[0]]
        if not valid or not can(at): continue
        title, priority = titles[at]
        lines = [x[0] for x in valid]
        header = f"╔══════════════════════════════════╗\n║  {title}  ║\n║  🔔 PRIORITY: {priority}               ║\n╚══════════════════════════════════╝\n"
        body = "\n" + "─"*34 + "\n".join(lines)
        footer = f"\n{'─'*34}\n🔄 {ft(nw)} → {ft(nw+REFRESH)} | 📋 {at.upper()}-{datetime.datetime.fromtimestamp(nw,IST).strftime('%d%m')}"
        msgs.append(header + body + footer)
        wd = state.setdefault("wd",{})
        wd["as"] = wd.get("as",0) + len(lines)
        wd[at] = wd.get(at,0) + len(lines)
        for ln in lines: state.setdefault("history",[]).append({"time":nw,"type":at,"sym":sf})

    sym_counts = {}
    for h in state.get("history",[]): sym_counts[h["sym"]] = sym_counts.get(h["sym"],0) + 1
    state["wd"]["top"] = [{"sym":s,"count":c} for s,c in sorted(sym_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    if int(time.time()) % 300 < 5: save_state()
    return msgs

def hb():
    nw = time.time()
    if nw - state.get("hl",0) > 1800:
        state["hl"] = nw
        stg(f"╔══════════════════════════════════╗\n║  💓 SYSTEM HEARTBEAT 💓          ║\n╚══════════════════════════════════╝\n\n👑 Bot: Samrat Singh\n🕐 Time: {ft(nw)}\n📊 Monitoring: {len(state['s'])} Symbols\n✅ Status: ALL SYSTEMS NOMINAL\n🏛️ Binance, Bybit, OKX, Bitget\n⏱️ Refresh: 5 min\n🔄 Next: {ft(nw+REFRESH)}")
        save_state()

def wr():
    nw = time.time()
    dt = datetime.datetime.fromtimestamp(nw, IST)
    if dt.weekday()==6 and dt.hour==9 and dt.minute<5:
        wk = dt.strftime("%Y-W%V")
        if state.get("wl") != wk:
            state["wl"] = wk
            wd = state.get("wd",{})
            top = wd.get("top",[])
            top_str = "\n".join([f"{i+1}. {ge(t['sym'])} {t['sym']} - {t['count']} alerts" for i,t in enumerate(top)]) if top else "No data"
            stg(f"╔══════════════════════════════════╗\n║  📊 WEEKLY REPORT 📊             ║\n╚══════════════════════════════════╝\n\n👑 Bot: Samrat Singh\n📅 {dt.strftime('%d-%b %Y')}\n⏱️ Uptime: {int((nw-state['st'])/86400)} Days\n📊 Symbols: {len(state['s'])}\n📨 Total Alerts: {wd.get('as',0)}\n\n📋 BY TYPE:\n🚨 Liquidation: {wd.get('liq',0)}\n🔴 Flip Bearish: {wd.get('fb',0)}\n🟢 Flip Bullish: {wd.get('fu',0)}\n🟢 Long Opp: {wd.get('lo',0)}\n🔴 Short Opp: {wd.get('so',0)}\n⚠️ Interval Comp: {wd.get('ic',0)}\n🔵 Interval Exp: {wd.get('ie',0)}\n💎 Premium Alpha: {wd.get('pa',0)}\n🆕 New Listing: {wd.get('nl',0)}\n\n🏆 TOP SYMBOLS:\n{top_str}\n\n📊 Peak 24h Vol: ${wd.get('peak',0)/1e9:.1f}B\n✅ Status: ALL SYSTEMS NOMINAL")
            state["wd"] = {"as":0,"liq":0,"fb":0,"fu":0,"lo":0,"so":0,"ic":0,"ie":0,"pa":0,"nl":0,"top":[],"peak":0}
            save_state()

# ========== MAIN ==========
threading.Thread(target=run_flask, daemon=True).start()
threading.Thread(target=self_ping, daemon=True).start()

update_prices()
stg("╔══════════════════════════════════╗\n║  🟢 SYSTEM ONLINE 🟢              ║\n╚══════════════════════════════════╝\n\n👑 Bot: Samrat Singh\n🏛️ Binance, Bybit, OKX, Bitget\n⏱️ 5 min | 🔰 10 Alert Types\n💾 Data: Saved | 📨 Grouped Alerts\n📊 Weekly: Sunday 9 AM\n🔄 Auto-Refresh: Active\n✅ ALL SYSTEMS NOMINAL")

while True:
    try:
        update_prices()
        for a in da(gd()): stg(a)
        hb(); wr()
    except Exception as e: print(f"Error: {e}")
    time.sleep(REFRESH)
