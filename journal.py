import os, requests, time, pandas as pd, pandas_ta as ta, json
from datetime import datetime
from discord import SyncWebhook, Embed, Color

# ==========================================
# KONFIGURATION (Prüfe deine Secrets!)
# ==========================================
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_USER = "phoenix9777" 
REPO_NAME = "my-sentinel-journal"

# TIPP: Zum Testen auf 0.00 setzen, damit er sofort sendet!
MOVE_THRESHOLD = 0.03 
COINS = ["BTC", "SOL", "SUI", "FET", "INJ"]

# ==========================================
# FUNKTIONEN
# ==========================================

def fetch_ohlcv(symbol, limit, timeframe):
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histo{timeframe}?fsym={symbol}&tsym=USD&limit={limit}&api_key={CRYPTOCOMPARE_KEY}"
        res = requests.get(url, timeout=20).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except: return None

def get_ai_content(symbol, d, mode="web"):
    url = "https://api.groq.com/openai/v1/chat/completions"
    if mode == "web":
        prompt = f"DU BIST DER 'KING VOLKAN ANALYZER'. SMC-PROFI. ANALYSIERE {symbol}/USD EXTREM AUSFÜHRLICH (600+ Wörter). Preis: {d['p']}$, RSI: {d['rsi']:.1f}, Trend: {d['b1d']}. Nutze Orderblocks, FVG, Liquidity Sweeps. Sprache: Deutsch."
    else:
        prompt = f"Kurz-Check {symbol}: Preis {d['p']}$, Trend {d['b1d']}. Ein Satz SMC-Tipp Deutsch."

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except: return "KI-Fehler beim King-Check."

def analyze_coin(symbol):
    df_1h = fetch_ohlcv(symbol, 400, "hour")
    df_1d = fetch_ohlcv(symbol, 250, "day")
    if df_1h is None or df_1d is None: return None

    last_p = df_1h['close'].iloc[-1]
    h24, l24 = df_1h['high'].iloc[-24:].max(), df_1h['low'].iloc[-24:].min()
    
    df_1d.ta.ema(length=200, append=True)
    b1d = "Bullish 🟢" if last_p > df_1d['EMA_200'].iloc[-1] else "Bearish 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); rsi = df_4h['RSI_14'].iloc[-1]
    
    avg_v = df_1d['volumeto'].mean()
    supp = sorted([round(r['low'], 2) for _, r in df_1d.iterrows() if (last_p * 0.85 < r['low'] < last_p) and r['volumeto'] > avg_v * 1.2], reverse=True)[:3]
    res_l = sorted([round(r['high'], 2) for _, r in df_1d.iterrows() if (last_p < r['high'] < last_p * 1.15) and r['volumeto'] > avg_v * 1.2])[:3]

    data = {"p": last_p, "h24": h24, "l24": l24, "b1d": b1d, "rsi": rsi, "supp": supp, "res": res_l}
    data["full_insight"] = get_ai_content(symbol, data, mode="web")
    data["short_insight"] = get_ai_content(symbol, data, mode="short")
    return data

def generate_html_report(symbol, d):
    # iPhone & Desktop Optimiertes Design
    html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KING VOLKAN - {symbol}</title>
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; padding: 15px; }}
            .container {{ max-width: 800px; margin: auto; background: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; }}
            h1 {{ color: #ffca28; border-bottom: 2px solid #ffca28; font-size: 1.4rem; }}
            .insight-box {{ white-space: pre-wrap; background: #0d1117; padding: 15px; border-radius: 8px; border-left: 5px solid #ffca28; line-height: 1.6; }}
            .chart-box {{ height: 450px; margin-top: 20px; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }}
            .nav {{ margin-bottom: 15px; }} .nav a {{ color: #58a6ff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav"><a href="index.html">← Dashboard</a></div>
            <h1>👑 KING VOLKAN ANALYZER | {symbol}</h1>
            <p><strong>Status: {d['b1d']}</strong> | Preis: {d['p']:,}$ | RSI: {d['rsi']:.1f}</p>
            <div class="insight-box">{d['full_insight']}</div>
            <div class="chart-box" id="tv-chart"></div>
        </div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize": true, "symbol": "BINANCE:{symbol}USDT", "interval": "240", "theme": "dark", "container_id": "tv-chart"}});</script>
    </body></html>
    """
    with open(f"{symbol.lower()}.html", "w", encoding="utf-8") as f: f.write(html_template)

def generate_index_page():
    # Erstellt die Startseite, damit die 404-Meldung verschwindet
    links = "".join([f'<li><a href="{s.lower()}.html">{s} Analyse</a></li>' for s in COINS])
    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KING VOLKAN TERMINAL</title>
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; display: flex; justify-content: center; padding: 40px 15px; }}
            .menu {{ background: #161b22; padding: 30px; border-radius: 12px; border: 1px solid #30363d; width: 100%; max-width: 400px; text-align: center; }}
            h1 {{ color: #ffca28; }}
            ul {{ list-style: none; padding: 0; }}
            li {{ margin: 20px 0; padding: 15px; background: #0d1117; border-radius: 8px; border: 1px solid #30363d; }}
            a {{ color: #58a6ff; text-decoration: none; font-size: 1.3rem; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="menu">
            <h1>👑 KING VOLKAN</h1>
            <p>Premium Markt-Analysen</p>
            <ul>{links}</ul>
        </div>
    </body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    generate_index_page() # Erstellt IMMER die Startseite
    
    PRICE_FILE = "last_prices.json"
    def get_last_price(s):
        if not os.path.exists(PRICE_FILE): return None
        with open(PRICE_FILE, "r") as f: return json.load(f).get(s)

    def save_price(s, p):
        prices = {}
        if os.path.exists(PRICE_FILE):
            with open(PRICE_FILE, "r") as f: prices = json.load(f)
        prices[s] = p
        with open(PRICE_FILE, "w") as f: json.dump(prices, f)

    for s in COINS:
        data = analyze_coin(s)
        if data:
            current_p = data['p']
            last_p = get_last_price(s)

            if last_p:
                change = abs(current_p - last_p) / last_p
                if change < MOVE_THRESHOLD:
                    print(f"--- {s}: {change:.2%} Bewegung. Kein Update. ---")
                    continue
            
            print(f"!!! {s} Update !!!")
            generate_html_report(s, data)
            save_price(s, current_p)
            
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            
            webhook = SyncWebhook.from_url(WEBHOOK_URL)
            embed = Embed(title=f"👑 KING VOLKAN: {s}", color=Color.from_rgb(255,202,40), url=web_url)
            embed.add_field(name="Preis", value=f"{current_p:,} $", inline=True)
            embed.add_field(name="Trend", value=data['b1d'], inline=True)
            embed.add_field(name="Quick-Insight", value=f"*{data['short_insight']}*", inline=False)
            embed.add_field(name="📊 Report", value=f"[Interaktive Analyse öffnen]({web_url})", inline=False)
            webhook.send(embed=embed, username="KING VOLKAN ANALYZER")
            time.sleep(2)
