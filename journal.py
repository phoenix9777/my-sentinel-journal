import os, requests, time, pandas as pd, pandas_ta as ta, json
from datetime import datetime, timedelta
from discord import SyncWebhook, Embed, Color

# KEYS
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GITHUB_USER = "phoenix9777" 
REPO_NAME = "my-sentinel-journal"
COINS = ["BTC", "SOL", "SUI", "FET", "INJ"]

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
        prompt = f"ERSTELLE EINE MAXIMAL AUSFÜHRLICHE SMC-ANALYSE FÜR {symbol}/USD. Preis {d['p']}$, RSI: {d['rsi']:.1f}, Bias: {d['b1d']}. Schreib viel Text, nutze Emojis, Deutsch."
    else:
        prompt = f"Analysiere {symbol} kurz. Preis {d['p']}$. Bias {d['b1d']}. RSI {d['rsi']:.1f}. 3 Sätze Deutsch."

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except: return "KI-Fehler."

def analyze_coin(symbol):
    df_1h = fetch_ohlcv(symbol, 400, "hour")
    df_1d = fetch_ohlcv(symbol, 250, "day")
    if df_1h is None or df_1d is None: return None

    last_p = df_1h['close'].iloc[-1]
    h24, l24 = df_1h['high'].iloc[-24:].max(), df_1h['low'].iloc[-24:].min()
    mid = round((h24 + l24) / 2, 2)
    
    df_1d.ta.ema(length=200, append=True)
    b1d = "Bullish 🟢" if last_p > df_1d['EMA_200'].iloc[-1] else "Bearish 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); rsi = df_4h['RSI_14'].iloc[-1]
    
    data = {"p": last_p, "h24": h24, "l24": l24, "mid": mid, "b1d": b1d, "rsi": rsi, "supp": [], "res": []}
    data["full_insight"] = get_ai_content(symbol, data, mode="web")
    data["short_insight"] = get_ai_content(symbol, data, mode="short")
    return data

def generate_html_report(symbol, d):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KING VOLKAN - {symbol}</title>
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; padding: 15px; }}
            .container {{ max-width: 900px; margin: auto; background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; }}
            h1 {{ color: #ffca28; border-bottom: 2px solid #ffca28; }}
            .insight-box {{ white-space: pre-wrap; background: #0d1117; padding: 20px; border-radius: 8px; border-left: 5px solid #ffca28; }}
            .chart-box {{ height: 500px; margin-top: 20px; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }}
            a {{ color: #58a6ff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="index.html">← Dashboard</a>
            <h1>👑 KING VOLKAN ANALYZER | {symbol}</h1>
            <div class="insight-box">{d['full_insight']}</div>
            <div class="chart-box" id="tv-chart"></div>
        </div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize": true, "symbol": "BINANCE:{symbol}USDT", "interval": "240", "theme": "dark", "container_id": "tv-chart"}});</script>
    </body></html>
    """
    with open(f"{symbol.lower()}.html", "w", encoding="utf-8") as f: f.write(html_template)

def generate_index_page():
    links = "".join([f'<li><a href="{s.lower()}.html">{s} Analyse</a></li>' for s in COINS])
    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>KING VOLKAN DASHBOARD</title>
    <style>body{{background:#0d1117;color:#c9d1d9;font-family:sans-serif;text-align:center;padding:50px;}} .box{{background:#161b22;padding:30px;border-radius:12px;display:inline-block;border:1px solid #30363d;}} a{{color:#58a6ff;font-size:1.5rem;text-decoration:none;}} li{{margin:15px 0;list-style:none;}}</style>
    </head><body><div class="box"><h1>👑 KING VOLKAN TERMINAL</h1><ul>{links}</ul></div></body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    generate_index_page() # ERZEUGT DIE STARTSEITE GEGEN DEN 404 FEHLER
    for s in COINS:
        data = analyze_coin(s)
        if data: 
            generate_html_report(s, data)
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            
            webhook = SyncWebhook.from_url(WEBHOOK_URL)
            embed = Embed(title=f"👑 KING VOLKAN: {s}", color=Color.from_rgb(255, 202, 40), url=web_url)
            embed.add_field(name="💵 Preis", value=f"**{data['p']:,} $**", inline=True)
            embed.add_field(name="📊 Analyse", value=f"[Klicke hier für Deep-Dive]({web_url})", inline=False)
            webhook.send(embed=embed, username="KING VOLKAN ANALYZER")
            time.sleep(2)
