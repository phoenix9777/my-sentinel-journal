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
        # KI sieht jetzt die MTF-Zusammenfassung für den Deep-Dive
        prompt = f"""
        ERSTELLE EINE MAXIMAL AUSFÜHRLICHE SMC-ANALYSE FÜR {symbol}/USD.
        Daten: Preis {d['p']}$, 24h Range: {d['l24']}$ - {d['h24']}$ (Mid: {d['mid']}$), RSI: {d['rsi']:.1f}, Bias: {d['b1d']}.
        Multi-Timeframe Status: {d.get('mtf_summary', 'Nicht verfügbar')}
        
        HALTE DICH STRENG AN DIESE STRUKTUR UND SCHREIBE VIEL TEXT:
        🔎 Allgemeine Einschätzung: (Detaillierte Analyse von Trend, Equilibrium und Indikatoren)
        📈 Wichtige Preislevels: (Exakte Preise für Support, Resistance, FVG-Zonen)
        💡 Trade-Idee & Setup: (Long/Short Szenario inkl. Manipulation/Sweep unter {d['l24']}$ oder über {d['h24']}$)
        📚 Beispiel für einen Einstieg: (Detaillierte Szenarien 1 & 2)
        🌌 Meine Erwartung (King Volkan AI): (Deine persönliche Prognose)

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
    # MTF-Daten sammeln
    tfs = {"1h": ("hour", 100), "4h": ("hour", 400), "1d": ("day", 250)}
    mtf_results = {}
    
    for label, (api_tf, limit) in tfs.items():
        df = fetch_ohlcv(symbol, limit, api_tf)
        if df is not None:
            # Spezielle 4h-Aggregierung für CryptoCompare
            if label == "4h":
                df = df.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
            
            lp = df['close'].iloc[-1]
            df.ta.rsi(length=14, append=True)
            df.ta.ema(length=200, append=True)
            
            mtf_results[label] = {
                "p": lp,
                "rsi": round(df['RSI_14'].iloc[-1], 1),
                "trend": "Bullish 🟢" if lp > df['EMA_200'].iloc[-1] else "Bearish 🔴"
            }

    # Basisdaten für die Analyse (4H als Standard)
    main_df = fetch_ohlcv(symbol, 400, "hour")
    if main_df is None or "1d" not in mtf_results: return None

    last_p = main_df['close'].iloc[-1]
    h24, l24 = main_df['high'].iloc[-24:].max(), main_df['low'].iloc[-24:].min()
    mid = round((h24 + l24) / 2, 2)
    
    # Support/Res Logik
    avg_v = fetch_ohlcv(symbol, 250, "day")['volumeto'].mean()
    supp = sorted([round(r['low'], 2) for _, r in fetch_ohlcv(symbol, 250, "day").iterrows() if (last_p * 0.88 < r['low'] < last_p) and r['volumeto'] > avg_v * 1.3], reverse=True)[:3]
    res_l = sorted([round(r['high'], 2) for _, r in fetch_ohlcv(symbol, 250, "day").iterrows() if (last_p < r['high'] < last_p * 1.12) and r['volumeto'] > avg_v * 1.3])[:3]

    mtf_summary = f"1H: {mtf_results['1h']['trend']} (RSI {mtf_results['1h']['rsi']}), 4H: {mtf_results['4h']['trend']} (RSI {mtf_results['4h']['rsi']}), 1D: {mtf_results['1d']['trend']} (RSI {mtf_results['1d']['rsi']})"

    data = {
        "p": last_p, "h24": h24, "l24": l24, "mid": mid, "b1d": mtf_results['1d']['trend'], 
        "rsi": mtf_results['4h']['rsi'], "supp": supp, "res": res_l, 
        "mtf": mtf_results, "mtf_summary": mtf_summary
    }
    
    data["full_insight"] = get_ai_content(symbol, data, mode="web")
    data["short_insight"] = get_ai_content(symbol, data, mode="short")
    return data

def generate_html_report(symbol, d):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KING VOLKAN TERMINAL - {symbol}</title>
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; padding: 15px; }}
            .container {{ max-width: 1000px; margin: auto; background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; }}
            h1 {{ color: #ffca28; border-bottom: 2px solid #ffca28; padding-bottom: 10px; }}
            .tf-stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 20px 0; }}
            .stat-card {{ background: #0d1117; padding: 15px; border-radius: 8px; border: 1px solid #30363d; text-align: center; }}
            .insight-box {{ white-space: pre-wrap; background: #0d1117; padding: 20px; border-radius: 8px; border-left: 5px solid #ffca28; margin-top: 20px; }}
            .chart-controls {{ margin: 20px 0 10px 0; text-align: right; }}
            .btn {{ background: #30363d; color: white; border: none; padding: 10px 18px; border-radius: 5px; cursor: pointer; margin-left: 5px; font-weight: bold; }}
            .btn:hover {{ background: #ffca28; color: black; }}
            .chart-box {{ height: 600px; border-radius: 8px; overflow: hidden; border: 1px solid #30363d; }}
            a {{ color: #58a6ff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <a href="index.html">← Zurück zum Dashboard</a>
            <h1>👑 KING VOLKAN TERMINAL | {symbol}/USD</h1>
            
            <div class="tf-stats">
                <div class="stat-card"><strong>1H</strong><br>{d['mtf']['1h']['trend']}<br>RSI: {d['mtf']['1h']['rsi']}</div>
                <div class="stat-card"><strong>4H</strong><br>{d['mtf']['4h']['trend']}<br>RSI: {d['mtf']['4h']['rsi']}</div>
                <div class="stat-card"><strong>1D</strong><br>{d['mtf']['1d']['trend']}<br>RSI: {d['mtf']['1d']['rsi']}</div>
            </div>

            <p><strong>Aktueller Preis: {d['p']:,} $</strong></p>
            <div class="insight-box">{d['full_insight']}</div>

            <div class="chart-controls">
                <button class="btn" onclick="changeChart('60')">1H Chart</button>
                <button class="btn" onclick="changeChart('240')">4H Chart</button>
                <button class="btn" onclick="changeChart('D')">1D Chart</button>
            </div>
            
            <div class="chart-box" id="tv-chart"></div>
        </div>

        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            let currentSymbol = "BINANCE:{symbol}USDT";
            function renderChart(interval) {{
                new TradingView.widget({{
                    "autosize": true, "symbol": currentSymbol, "interval": interval,
                    "timezone": "Europe/Berlin", "theme": "dark", "style": "1",
                    "locale": "de", "container_id": "tv-chart"
                }});
            }}
            function changeChart(tf) {{ renderChart(tf); }}
            renderChart('240');
        </script>
    </body></html>
    """
    with open(f"{symbol.lower()}.html", "w", encoding="utf-8") as f: f.write(html_template)

def send_embed(symbol, d, web_url):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    color = Color.from_rgb(255, 202, 40)
    embed = Embed(title=f"👑 KING VOLKAN ANALYZER: {symbol}", color=color, url=web_url)
    
    embed.add_field(name="💵 Preis", value=f"**{d['p']:,} $**", inline=True)
    embed.add_field(name="📉 RSI (4H)", value=f"{d['rsi']:.1f}", inline=True)
    embed.add_field(name="🚦 Macro", value=f"{d['b1d']}", inline=True)
    
    s_text = ", ".join([f"{s}$" for s in d['supp']]) or "Suche..."
    r_text = ", ".join([f"{r}$" for r in d['res']]) or "Suche..."
    embed.add_field(name="🛡️ Support", value=s_text, inline=True)
    embed.add_field(name="⚔️ Resistance", value=r_text, inline=True)
    
    embed.add_field(name="🧠 Volkan's Quick-Insight", value=f"*{d['short_insight']}*", inline=False)
    embed.add_field(name="📊 Deep-Dive & MTF-Terminal", value=f"[Klicke hier für das 1H/4H/1D Terminal]({web_url})", inline=False)
    
    webhook.send(embed=embed, username="KING VOLKAN ANALYZER")

def generate_index_page(coins):
    links = "".join([f'<li><a href="{s.lower()}.html" style="color:#ffca28; font-size:20px; text-decoration:none;">{s} Terminal</a></li>' for s in coins])
    html = f"""
    <html><body style='background:#0d1117;color:white;text-align:center;font-family:sans-serif; padding-top:50px;'>
    <h1 style="color:#ffca28; font-size:40px;">👑 KING VOLKAN TERMINAL</h1>
    <ul style="list-style:none; padding:0;">{links}</ul></body></html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    GITHUB_USER = "phoenix9777" 
    REPO_NAME = "my-sentinel-journal"
    COINS = ["BTC", "SOL", "SUI", "FET", "INJ"]
    
    generate_index_page(COINS)

    for s in COINS:
        data = analyze_coin(s)
        if data: 
            generate_html_report(s, data)
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            send_embed(s, data, web_url)
            time.sleep(2)
