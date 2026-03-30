import os, requests, time, pandas as pd, pandas_ta as ta
from datetime import datetime, timedelta
from discord import SyncWebhook, Embed, Color

# KEYS
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def fetch_data(symbol, limit, timeframe):
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histo{timeframe}?fsym={symbol}&tsym=USD&limit={limit}&api_key={CRYPTOCOMPARE_KEY}"
        res = requests.get(url, timeout=20).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except: return None

def get_ai_summary(symbol, d):
    """Lässt Groq eine kurze, knackige Zusammenfassung schreiben"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    prompt = f"""
    Analysiere {symbol} basierend auf diesen Daten:
    - Bias: 1h {d['b1']}, 4h {d['b4']}, 1d {d['b1d']}
    - RSI (4h): {d['rsi']:.1f}
    - Nächste Support-Zone: {d['supp'][0] if d['supp'] else 'N/A'}$
    - Nächste Resistance: {d['res'][0] if d['res'] else 'N/A'}$

    Schreibe 2-3 Sätze als 'Sentinel Insight'. Sei direkt, professionell und bewerte das Risiko. 
    Kein 'Hier ist die Analyse', fang direkt an.
    """
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
    try:
        res = requests.post(url, json=payload, headers=headers).json()
        return res['choices'][0]['message']['content']
    except: return "Analyse aktuell nicht verfügbar."

def analyze_coin(symbol):
    df_1h = fetch_data(symbol, 150, "hour")
    df_1d = fetch_data(symbol, 150, "day")
    if df_1h is None or df_1d is None: return None

    # TA Berechnungen
    df_1h.ta.ema(length=20, append=True); df_1h.ta.ema(length=50, append=True)
    ema20, ema50 = df_1h['EMA_20'].iloc[-1], df_1h['EMA_50'].iloc[-1]
    b1 = "Bullish 🟢" if ema20 > ema50 else "Bearish 🔴"

    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True); df_4h.ta.macd(append=True)
    rsi = df_4h['RSI_14'].iloc[-1]; macd = df_4h['MACDh_12_26_9'].iloc[-1]
    b4 = "Bullish 🟢" if rsi > 50 and macd > 0 else "Bearish 🔴" if rsi < 50 and macd < 0 else "Neutral 🟠"

    last_p = df_1d['close'].iloc[-1]
    b1d = "Bullish (HH) 🟢" if last_p > df_1d['close'].iloc[-2] else "Bearish (LL) 🔴"

    # SMC Level
    avg_v = df_1d['volumeto'].mean()
    supp = sorted([r['low'] for _, r in df_1d.iterrows() if r['low'] < last_p and r['volumeto'] > avg_v * 1.1], reverse=True)[:3]
    res_l = sorted([r['high'] for _, r in df_1d.iterrows() if r['high'] > last_p and r['volumeto'] > avg_v * 1.1])[:3]

    data = {"p": last_p, "b1": b1, "b4": b4, "b1d": b1d, "supp": supp, "res": res_l, "rsi": rsi}
    data["insight"] = get_ai_summary(symbol, data)
    return data

def send_embed(symbol, d):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    color = Color.green() if "🟢" in d['b1d'] else Color.red()
    embed = Embed(title=f"👑 Institutional Report: {symbol}/USD", color=color)
    embed.add_field(name="💵 Aktueller Preis", value=f"**{d['p']:,} $**", inline=False)
    embed.add_field(name="⏱️ Timeframe Bias", value=f"**1h:** {d['b1']}\n**4h:** {d['b4']}\n**1d:** {d['b1d']}", inline=False)
    
    s_t = "\n".join([f"🟢 Support: **{s:,}$**" for s in d['supp']])
    r_t = "\n".join([f"🔴 Resistance: **{r:,}$**" for r in d['res']])
    embed.add_field(name="🛡️ SMC Support", value=s_t or "Suche...", inline=True)
    embed.add_field(name="⚔️ SMC Resistance", value=r_t or "Suche...", inline=True)
    
    # HIER IST DEIN TEXT
    embed.add_field(name="🧠 Sentinel Insight", value=f"*{d['insight']}*", inline=False)
    
    webhook.send(embed=embed, username="Sentinel Alpha")

if __name__ == "__main__":
    for s in ["BTC", "SOL", "SUI"]:
        data = analyze_coin(s)
        if data: send_embed(s, data)
        time.sleep(2)
