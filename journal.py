import os, requests, time, pandas as pd, pandas_ta as ta, json
from datetime import datetime
from discord import SyncWebhook, Embed, Color

# ==========================================
# KONFIGURATION & KEYS
# ==========================================
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_USER = "phoenix9777" 
REPO_NAME = "my-sentinel-journal"

# HIER DEINE SCHWELLE (0.03 = 3%)
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
    
    # AGGRESSIVERER & ABWECHSLUNGSREICHERER PROMPT
    if mode == "web":
        prompt = f"""
        DU BIST DER 'KING VOLKAN ANALYZER'. STIL: AGGRESSIV, PRÄZISE, SENIOR HEDGEFONDS-TRADER.
        ERSTELLE EINE MAXIMAL AUSFÜHRLICHE SMC-ANALYSE FÜR {symbol}/USD.
        
        MARKT-DATEN: 
        Preis: {d['p']}$, 24h Range: {d['l24']}$ - {d['h24']}$ (Mid: {d['mid']}$), RSI: {d['rsi']:.1f}, Bias: {d['b1d']}, ATR: {d['atr']:.4f}.
        
        DEINE AUFGABE:
        Schreibe MINDESTENS 600 Wörter. Nutze Begriffe wie 'Judas Swing', 'Liquidity Sweep', 'Fair Value Gap', 'Orderblock' und 'Internal Structure'.
        WECHSLE JEDES MAL DEINEN FOKUS – sei nicht langweilig!
        
        STRUKTUR:
        🔎 Der King-Check: (Warum bewegt sich der Markt gerade so? Trend-Analyse)
        📈 Liquiditäts-Falle: (Wo liegen die Stops? Wo werden Retailer abgefischt?)
        💡 Das Sniper-Setup: (Exakte Preise für Long/Short Szenarien inkl. FVG-Zonen)
        📚 Live-Beispiel Einstieg: (Detaillierte Szenarien mit Bestätigungsmustern)
        🌌 Volkan's Prophezeiung: (Deine persönliche Prognose & hartes Risikomanagement)

        Schreibe wie ein absoluter Profi. Nutze Emojis. Sprache: Deutsch.
        """
    else:
        prompt = f"Analysiere {symbol} extrem kurz. Preis {d['p']}$. Bias {d['b1d']}. RSI {d['rsi']:.1f}. Nenne das wichtigste SMC-Level heute. 2 Sätze Deutsch."

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.8 # HÖHERE KREATIVITÄT GEGEN LANGWEILE
    }
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
    mid = round((h24 + l24) / 2, 2)
    
    atr_df = df_1h.ta.atr(length=14)
    atr = atr_df.iloc[-1] if atr_df is not None else 0

    df_1d.ta.ema(length=200, append=True)
    b1d = "Bullish (Macro) 🟢" if last_p > df_1d['EMA_200'].iloc[-1] else "Bearish (Macro Trend) 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); rsi = df_4h['RSI_14'].iloc[-1]
    
    avg_v = df_1d['volumeto'].mean()
    supp = sorted([round(r['low'], 2) for _, r in df_1d.iterrows() if (last_p * 0.85 < r['low'] < last_p) and r['volumeto'] > avg_v * 1.2], reverse=True)[:3]
    res_l = sorted([round(r['high'], 2) for _, r in df_1d.iterrows() if (last_p < r['high'] < last_p * 1.15) and r['volumeto'] > avg_v * 1.2])[:3]

    data = {"p": last_p, "h24": h24, "l24": l24, "mid": mid, "b1d": b1d, "rsi": rsi, "atr": atr, "supp": supp, "res": res_l}
    data["full_insight"] = get_ai_content(symbol, data, mode="web")
    data["short_insight"] = get_ai_content(symbol, data, mode="short")
    return data

def generate_html_report(symbol, d):
    html_template = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8"><title>KING VOLKAN ANALYZER - {symbol}</title>
        <style>
            body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; padding: 15px; }}
            .container {{ max-width: 900px; margin: auto; background: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; }}
            h1 {{ color: #ffca28; border-bottom: 2px solid #ffca28; }}
            .insight-box {{ white-space: pre-wrap; background: #0d1117; padding: 20px; border-radius: 8px; border-left: 5px solid #ffca28; }}
            .chart-box {{ height: 600px; margin-top: 20px; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👑 KING VOLKAN ANALYZER | {symbol}/USD</h1>
            <p><strong>Trend: {d['b1d']}</strong> | Preis: {d['p']}$ | RSI: {d['rsi']:.1f}</p>
            <div class="insight-box">{d['full_insight']}</div>
            <div class="chart-box" id="tv-chart"></div>
        </div>
        <script src="https://s3.tradingview.com/tv.js"></script>
        <script>new TradingView.widget({{"autosize": true, "symbol": "BINANCE:{symbol}USDT", "interval": "240", "theme": "dark", "container_id": "tv-chart"}});</script>
    </body></html>
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
    embed.add_field(name="🛡️ Support", value=s_text, inline=True)
    embed.add_field(name="⚔️ Resistance", value=r_text, inline=True)
    embed.add_field(name="🧠 Quick-Insight", value=f"*{d['short_insight']}*", inline=False)
    embed.add_field(name="📊 Report", value=f"[Interaktive Analyse öffnen]({web_url})", inline=False)
    webhook.send(embed=embed, username="KING VOLKAN ANALYZER")

# ==========================================
# PREIS-SPEICHER LOGIK
# ==========================================

PRICE_FILE = "last_prices.json"

def get_last_price(symbol):
    if not os.path.exists(PRICE_FILE): return None
    with open(PRICE_FILE, "r") as f:
        return json.load(f).get(symbol)

def save_current_price(symbol, price):
    prices = {}
    if os.path.exists(PRICE_FILE):
        with open(PRICE_FILE, "r") as f: prices = json.load(f)
    prices[symbol] = price
    with open(PRICE_FILE, "w") as f: json.dump(prices, f)

# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    for s in COINS:
        data = analyze_coin(s)
        if data:
            current_p = data['p']
            last_p = get_last_price(s)

            # 3% FILTER LOGIK
            if last_p:
                change = abs(current_p - last_p) / last_p
                if change < MOVE_THRESHOLD:
                    print(f"--- {s}: Nur {change:.2%} Bewegung. Kein Spam heute. ---")
                    continue
            
            print(f"!!! {s}: {current_p}$ erkannt. Starte Deep-Dive Analyse! !!!")
            generate_html_report(s, data)
            save_current_price(s, current_p)
            
            web_url = f"https://{GITHUB_USER}.github.io/{REPO_NAME}/{s.lower()}.html"
            send_embed(s, data, web_url)
            time.sleep(2)
