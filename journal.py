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
        ERSTELLE EINE MAXIMAL AUSFÜHRLICHE SMC-ANALYSE FÜR {symbol}/USD.
        Daten: Preis {d['p']}$, 24h Range: {d['l24']}$ - {d['h24']}$ (Mid: {d['mid']}$), RSI: {d['rsi']:.1f}, Bias: {d['b1d']}.
        
        HALTE DICH STRENG AN DIESE STRUKTUR UND SCHREIBE VIEL TEXT:
        🔎 Allgemeine Einschätzung: (Detaillierte Analyse von Trend, Equilibrium und Indikatoren wie MACD/RSI/ATR)
        📈 Wichtige Preislevels: (Exakte Preise für Support, Resistance, FVG-Zonen und Liquiditäts-Pools)
        💡 Trade-Idee & Setup: (Entwirf ein Long- und ein Short-Szenario inkl. Manipulation/Sweep unter {d['l24']}$ oder über {d['h24']}$)
        📚 Beispiel für einen Einstieg: (Detaillierte Szenarien 1 & 2 mit Bestätigungsmustern)
        🌌 Meine Erwartung (King Volkan AI): (Deine persönliche Prognose & Risiko-Einschätzung)

        Schreibe wie ein Senior Analyst für einen Hedgefonds. Nutze Emojis. Deutsch.
        """
    else:
        prompt = f"Analysiere {symbol} kurz für Discord. Preis {d['p']}$. Bias {d['b1d']}. RSI {d['rsi']:.1f}. Nenne kurz das wichtigste SMC-Level heute. 3 Sätze Deutsch."

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
    
    atr_df = df_1h.ta.atr(length=14)
    atr = atr_df.iloc[-1] if atr_df is not None else 0

    df_1d.ta.ema(length=200, append=True)
    b1d = "Bullish (Macro) 🟢" if last_p > df_1d['EMA_200'].iloc[-1] else "Bearish (Macro Trend) 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); rsi = df_4h['RSI_14'].iloc[-1]
    
    avg_v = df_1d['volumeto'].mean()
    supp = sorted([round(r['low'], 2) for _, r in df_1d.iterrows() if (last_p * 0.88 < r['low'] < last_p) and r['volumeto'] > avg_v * 1.3], reverse=True)[:3]
    res_l = sorted([round(r['high'], 2) for _, r in df_1d.iterrows() if (last_p < r['high'] < last_p * 1.12) and r['volumeto'] > avg_v * 1.3])[:3]

    data = {"p": last_p, "h24": h24, "l24": l24, "mid": mid, "b1d": b1d, "rsi": rsi, "atr": atr, "supp": supp, "res": res_l}
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
            body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; padding: 15px; line-height: 1.6; }}
            .container {{ max-width: 900px; margin: auto; background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; }}
            h1 {{ color: #ffca28; border-bottom: 2px solid #ffca28; padding-bottom: 10px; }}
            .insight-box {{ white-space: pre-wrap; background: #0d1117; padding: 20px; border-radius: 8px; border-left: 5px solid #ffca28; margin-top: 20px; }}
            .chart-box {{ height: 600px; margin-top: 20px; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }}
            a {{ color: #58a6ff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="index.html">← Zurück zum Dashboard</a>
            <h1>👑 KING VOLKAN ANALYZER | {symbol}/USD</h1>
            <p><strong>Macro-Trend: {d['b1d']}</strong> | Live-Preis: {d['p']}$</p>
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
    embed.add_field(name="📉 RSI", value=f"{d['rsi']:.1f}", inline=True)
    embed.add_field(name="🚦 Trend", value=f"{d['b1d']}", inline=True)
    
    s_text = ", ".join([f"{s}$" for s in d['supp']]) or "Suche..."
    r_text = ", ".join([f"{r}$" for r in d['res']]) or "Suche..."
    embed.add_field(name="🛡️ Support-Level", value=s_text, inline=True)
    embed.add_field(name="⚔️ Resistance-Level", value=r_text, inline=True)
    
    embed.add_field(name="🧠 Volkan's Quick-Insight", value=f"*{d['short_insight']}*", inline=False)
    embed.add_field(name="📊 Deep-Dive Report", value=f"[Klicke hier für interaktive Analyse]({web_url})", inline=False)
    
    webhook.send(embed=embed, username="KING VOLKAN ANALYZER")

def generate_index_page(coins):
    links = "".join([f'<li><a href="{s.lower()}.html">{s} Analyse</a></li>' for s in coins])
    html = f"""
    <html><body style='background:#0d1117;color:white;text-align:center;font-family:sans-serif;'>
    <h1>👑 KING VOLKAN TERMINAL</h1><ul>{links}</ul></body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    GITHUB_USER = "phoenix9777" 
    REPO_NAME = "my-sentinel-journal"
    COINS = ["BTC", "SOL", "SUI", "FET", "INJ"]
    
    generate_index_page(COINS) # Erzeugt Dashboard gegen 404 Fehler

    for s in COINS:
        data = analyze_coin(s)
        if data: 
            generate_html_report(s, data)
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            send_embed(s, data, web_url)
            time.sleep(2)
