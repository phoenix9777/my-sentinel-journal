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

def get_ai_content(symbol, d, mode="web"):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    if mode == "web":
        prompt = f"""
        ERSTELLE EINE ANALYSE IM FINORA-STYLE FÜR {symbol} ({d['p']}$):
        Rohdaten: 24h High: {d['h24']}$, 24h Low: {d['l24']}$, Mid: {d['mid']}$, RSI: {d['rsi']:.1f}, Bias: {d['b1d']}.
        
        STRUKTUR (STRENG EINHALTEN):
        🔎 Allgemeine Einschätzung: (Trend, Equilibrium-Analyse, Indikatoren wie MACD/RSI/ATR erwähnen)
        📈 Wichtige Preislevels: (Nenne Support/Resistance, FVG-Zonen und Liquiditäts-Tiefs/Hochs mit exakten Preisen)
        💡 Trade-Idee & Setup: (Entwirf ein Long- und ein Short-Szenario inkl. Manipulation/Sweep unter {d['l24']}$ oder über {d['h24']}$)
        📚 Beispiel für einen Einstieg: (Szenario 1 & 2 mit Bestätigungsmustern beschreiben)
        🌌 Meine Erwartung (King Volkan AI): (Deine persönliche Prognose & Bias-Wechsel)

        Schreibe extrem ausführlich, nutze Emojis und sei eiskalt professionell auf Deutsch.
        """
    else:
        prompt = f"Kurz-Update {symbol}: Preis {d['p']}$. Bias {d['b1d']}. Nenne das wichtigste Level für einen Liquiditäts-Sweep heute. 2 Sätze Deutsch."

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except: return "KI-Fehler beim Generieren."

def analyze_coin(symbol):
    df_1h = fetch_ohlcv(symbol, 400, "hour")
    df_1d = fetch_ohlcv(symbol, 250, "day")
    if df_1h is None or df_1d is None: return None

    last_p = df_1h['close'].iloc[-1]
    h24, l24 = df_1h['high'].iloc[-24:].max(), df_1h['low'].iloc[-24:].min()
    mid = round((h24 + l24) / 2, 2)
    
    # ATR Fix
    atr_df = df_1h.ta.atr(length=14)
    atr = atr_df.iloc[-1] if atr_df is not None else 0

    df_1d.ta.ema(length=200, append=True)
    b1d = "Bullish (Macro) 🟢" if last_p > df_1d['EMA_200'].iloc[-1] else "Bearish (Macro Trend) 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); rsi = df_4h['RSI_14'].iloc[-1]
    
    data = {"p": last_p, "h24": h24, "l24": l24, "mid": mid, "b1d": b1d, "rsi": rsi, "atr": atr}
    data["full_insight"] = get_ai_content(symbol, data, mode="web")
    data["short_insight"] = get_ai_content(symbol, data, mode="short")
    return data

def generate_html_report(symbol, d):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KING VOLKAN ANALYZER - {symbol}</title>
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; padding: 15px; line-height: 1.5; }}
            .container {{ max-width: 850px; margin: auto; background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; }}
            h1 {{ color: #ffca28; border-bottom: 2px solid #30363d; padding-bottom: 10px; font-size: 1.5rem; }}
            .insight-box {{ white-space: pre-wrap; background: #0d1117; padding: 20px; border-radius: 8px; border-left: 5px solid #ffca28; margin: 20px 0; font-size: 1rem; }}
            .chart-box {{ height: 550px; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👑 KING VOLKAN ANALYZER | {symbol}/USD</h1>
            <p><strong>Status: {d['b1d']}</strong> | Preis: {d['p']}$</p>
            <div class="insight-box">{d['full_insight']}</div>
            <div class="chart-box" id="tv-chart"></div>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            new TradingView.widget({{
                "autosize": true, "symbol": "BINANCE:{symbol}USDT", "interval": "240", "theme": "dark", "style": "1", "locale": "de", "container_id": "tv-chart"
            }});
        </script>
    </body>
    </html>
    """
    with open(f"{symbol.lower()}.html", "w", encoding="utf-8") as f: f.write(html_template)

def send_embed(symbol, d, web_url):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    color = Color.from_rgb(255, 202, 40)
    embed = Embed(title=f"👑 KING VOLKAN ANALYZER: {symbol}", color=color, url=web_url)
    embed.add_field(name="💵 Preis", value=f"**{d['p']:,} $**", inline=True)
    embed.add_field(name="🧠 Quick-Insight", value=f"*{d['short_insight']}*", inline=False)
    embed.add_field(name="📊 Full Deep-Dive", value=f"[Interaktiver Chart & Strategie]({web_url})", inline=False)
    webhook.send(embed=embed, username="KING VOLKAN ANALYZER")

if __name__ == "__main__":
    GITHUB_USER = "phoenix9777" 
    REPO_NAME = "my-sentinel-journal"
    for s in ["BTC", "SOL", "SUI"]:
        data = analyze_coin(s)
        if data: 
            generate_html_report(s, data)
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            send_embed(s, data, web_url)
            time.sleep(2)
