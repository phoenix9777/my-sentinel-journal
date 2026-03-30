import os, requests, time, pandas as pd, pandas_ta as ta
from datetime import datetime, timedelta
from discord import SyncWebhook, Embed, Color

# KEYS
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def fetch_ohlcv(symbol, limit, timeframe):
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histo{timeframe}?fsym={symbol}&tsym=USD&limit={limit}&api_key={CRYPTOCOMPARE_KEY}"
        res = requests.get(url, timeout=20).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except: return None

def generate_html_report(symbol, d, web_url):
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sentinel Intelligence - {symbol}</title>
        <style>
            body {{ background: #0d1117; color: white; font-family: -apple-system, sans-serif; padding: 20px; }}
            .container {{ max-width: 1000px; margin: auto; background: #161b22; padding: 30px; border-radius: 15px; border: 1px solid #30363d; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; padding-bottom: 20px; }}
            .status {{ padding: 10px 20px; border-radius: 8px; font-weight: bold; }}
            .bullish {{ background: #238636; }} .bearish {{ background: #da3633; }}
            .chart-box {{ margin-top: 30px; height: 600px; border-radius: 10px; overflow: hidden; border: 1px solid #30363d; }}
            .insight {{ background: #0d1117; padding: 20px; border-radius: 10px; border-left: 4px solid #58a6ff; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{symbol}/USD Analysis</h1>
                <div class="status {'bullish' if '🟢' in d['b1d'] else 'bearish'}">{d['b1d']}</div>
            </div>
            <div class="insight">
                <h3>🧠 Sentinel Insight</h3>
                <p>{d['insight']}</p>
            </div>
            <div class="chart-box" id="tv-chart"></div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            new TradingView.widget({{
                "autosize": true, "symbol": "BINANCE:{symbol}USDT", "interval": "240",
                "timezone": "Europe/Berlin", "theme": "dark", "style": "1", "locale": "de",
                "enable_publishing": false, "allow_symbol_change": true, "container_id": "tv-chart"
            }});
        </script>
    </body>
    </html>
    """
    filename = f"{symbol.lower()}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    return filename

def get_pro_insight(symbol, d):
    url = "https://api.groq.com/openai/v1/chat/completions"
    prompt = f"Analysiere {symbol} ({d['p']}$): 1h:{d['b1']}, 4h:{d['b4']}, 1d:{d['b1d']}. RSI:{d['rsi']:.1f}. Sei professionell und kritisch. 3 Sätze Deutsch."
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except: return "Analyse-Brain aktuell offline."

def analyze_coin(symbol):
    df_1h = fetch_ohlcv(symbol, 400, "hour")
    df_1d = fetch_ohlcv(symbol, 250, "day")
    if df_1h is None or df_1d is None: return None

    df_1d.ta.ema(length=50, append=True); df_1d.ta.ema(length=200, append=True)
    last_p = df_1d['close'].iloc[-1]
    ema50_d, ema200_d = df_1d['EMA_50'].iloc[-1], df_1d['EMA_200'].iloc[-1]
    b1d = "Bullish (Macro) 🟢" if last_p > ema200_d else "Bearish (Macro) 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); df_4h.ta.macd(append=True)
    rsi, macd = df_4h['RSI_14'].iloc[-1], df_4h['MACDh_12_26_9'].iloc[-1]
    b4 = "Bullish 🟢" if rsi > 55 and macd > 0 else "Bearish 🔴" if rsi < 45 else "Neutral 🟠"

    df_1h.ta.ema(length=20, append=True); df_1h.ta.ema(length=50, append=True)
    b1 = "Bullish 🟢" if df_1h['EMA_20'].iloc[-1] > df_1h['EMA_50'].iloc[-1] else "Bearish 🔴"

    avg_v = df_1d['volumeto'].mean()
    supp = sorted([r['low'] for _, r in df_1d.iterrows() if (last_p * 0.88 < r['low'] < last_p) and r['volumeto'] > avg_v * 1.3], reverse=True)[:3]
    res_l = sorted([r['high'] for _, r in df_1d.iterrows() if (last_p < r['high'] < last_p * 1.12) and r['volumeto'] > avg_v * 1.3])[:3]

    data = {"p": last_p, "b1": b1, "b4": b4, "b1d": b1d, "supp": supp, "res": res_l, "rsi": rsi}
    data["insight"] = get_pro_insight(symbol, data)
    return data

def send_embed(symbol, d, web_url):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    color = Color.green() if "🟢" in d['b1d'] else Color.red()
    embed = Embed(title=f"👑 Institutional Report: {symbol}/USD", color=color, url=web_url)
    embed.add_field(name="💵 Preis", value=f"**{d['p']:,} $**", inline=True)
    embed.add_field(name="⏱️ Bias", value=f"1h: {d['b1']}\n4h: {d['b4']}\n1d: {d['b1d']}", inline=True)
    embed.add_field(name="🔗 Web-Analyse", value=f"[Interaktiver Chart & Deep Dive]({web_url})", inline=False)
    embed.add_field(name="🧠 Insight", value=f"*{d['insight']}*", inline=False)
    webhook.send(embed=embed, username="Sentinel Elite")

if __name__ == "__main__":
    # USER INFO: Passe 'deinname' und 'repo' an
    GITHUB_USER = "kingley3370" 
    REPO_NAME = "my-sentinel-journal"
    
    for s in ["BTC", "SOL", "SUI"]:
        data = analyze_coin(s)
        if data: 
            generate_html_report(s, data, "")
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            send_embed(s, data, web_url)
            time.sleep(2)
