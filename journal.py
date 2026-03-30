import os, requests, time, pandas as pd, pandas_ta as ta
from datetime import datetime, timedelta
from discord import SyncWebhook, Embed, Color

# API KEYS
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

def get_pro_insight(symbol, d):
    url = "https://api.groq.com/openai/v1/chat/completions"
    prompt = f"""
    ROLE: Institutional Crypto Researcher. 
    DATA: {symbol} at {d['p']}$. Bias: 1h:{d['b1']}, 4h:{d['b4']}, Daily:{d['b1d']}. RSI:{d['rsi']:.1f}.
    SMC: Supp:{d['supp'][0] if d['supp'] else 'N/A'}$ | Res:{d['res'][0] if d['res'] else 'N/A'}$.

    TASK: Be realistic. If Daily is Bearish but 4h is Bullish, warn about a 'Bear Market Rally'. 
    If all are Bullish, check if RSI is overbought (>70). 
    Write 3 cold, professional sentences in German. Start directly.
    """
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

    # --- DAILY: Die Markt-Wahrheit ---
    df_1d.ta.ema(length=50, append=True)
    df_1d.ta.ema(length=200, append=True)
    last_p = df_1d['close'].iloc[-1]
    ema50_d, ema200_d = df_1d['EMA_50'].iloc[-1], df_1d['EMA_200'].iloc[-1]
    
    if last_p > ema50_d and last_p > ema200_d: b1d = "Bullish (Macro) 🟢"
    elif last_p < ema200_d: b1d = "Bearish (Macro Trend) 🔴"
    else: b1d = "Neutral/Range 🟠"

    # --- 4h: Das Momentum ---
    df_4h = df_1h.set_index('time').resample('4h').agg({'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'}).dropna().reset_index()
    df_4h.ta.rsi(length=14, append=True)
    df_4h.ta.macd(append=True)
    rsi, macd = df_4h['RSI_14'].iloc[-1], df_4h['MACDh_12_26_9'].iloc[-1]
    
    if rsi > 55 and macd > 0: b4 = "Bullish Momentum 🟢"
    elif rsi < 45 and macd < 0: b4 = "Bearish Pressure 🔴"
    else: b4 = "Choppy/Side-Trend 🟠"

    # --- 1h: Der Einstieg (Short-term) ---
    df_1h.ta.ema(length=20, append=True)
    df_1h.ta.ema(length=50, append=True)
    ema20_h, ema50_h = df_1h['EMA_20'].iloc[-1], df_1h['EMA_50'].iloc[-1]
    b1 = "Bullish 🟢" if (ema20_h > ema50_h and last_p > ema20_h) else "Bearish 🔴"

    # --- SMC ZONEN (Nur signifikante lokale Level) ---
    avg_v = df_1d['volumeto'].mean()
    supp = sorted([r['low'] for _, r in df_1d.iterrows() if (last_p * 0.88 < r['low'] < last_p) and r['volumeto'] > avg_v * 1.3], reverse=True)[:3]
    res_l = sorted([r['high'] for _, r in df_1d.iterrows() if (last_p < r['high'] < last_p * 1.12) and r['volumeto'] > avg_v * 1.3])[:3]

    data = {"p": last_p, "b1": b1, "b4": b4, "b1d": b1d, "supp": supp, "res": res_l, "rsi": rsi}
    data["insight"] = get_pro_insight(symbol, data)
    return data

def send_embed(symbol, d):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    # Farbe richtet sich nach dem Daily Trend (der wichtigsten Metrik)
    color = Color.green() if "🟢" in d['b1d'] else Color.red() if "🔴" in d['b1d'] else Color.orange()
    
    embed = Embed(title=f"👑 Institutional Report: {symbol}/USD", color=color)
    embed.add_field(name="💵 Marktwert", value=f"**{d['p']:,} $**", inline=False)
    
    # MTF Bias Grid
    bias_text = f"**Daily:** {d['b1d']}\n**4h Chart:** {d['b4']}\n**1h Chart:** {d['b1']}"
    embed.add_field(name="⏱️ Multi-Timeframe Bias", value=bias_text, inline=False)
    
    # S/R Zonen
    s_text = "\n".join([f"🟢 Support: **{s:,}$**" for s in d['supp']]) or "Kein lokaler Support"
    r_text = "\n".join([f"🔴 Resistance: **{r:,}$**" for r in d['res']]) or "Keine lokale Res"
    embed.add_field(name="🛡️ Demand (Käufer)", value=s_text, inline=True)
    embed.add_field(name="⚔️ Supply (Verkäufer)", value=r_t, inline=True)
    
    # KI Analyse
    embed.add_field(name="🧠 Sentinel Insight", value=f"*{d['insight']}*", inline=False)
    
    embed.set_footer(text=f"Sentinel Alpha | MTF System | 180°C Trend-Logic")
    webhook.send(embed=embed, username=f"Sentinel Elite | {symbol}")

if __name__ == "__main__":
    for s in ["BTC", "SOL", "SUI"]:
        data = analyze_coin(s)
        if data: 
            send_embed(s, data)
            time.sleep(2)
