import os
import requests
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timedelta
from discord import SyncWebhook, Embed, Color

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def fetch_data(symbol, limit, timeframe):
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histo{timeframe}?fsym={symbol}&tsym=USD&limit={limit}&api_key={CRYPTOCOMPARE_KEY}"
        res = requests.get(url, timeout=20).json()
        if 'Data' not in res or 'Data' not in res['Data']: return None
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except: return None

def analyze_coin(symbol):
    print(f"--- Starte Deep-Analysis für {symbol} ---")
    df_1h = fetch_data(symbol, 150, "hour")
    df_1d = fetch_data(symbol, 150, "day")
    if df_1h is None or df_1d is None or df_1h.empty: return None

    # --- 1h ANALYSIS ---
    df_1h.ta.ema(length=20, append=True)
    df_1h.ta.ema(length=50, append=True)
    ema20, ema50 = df_1h['EMA_20'].iloc[-1], df_1h['EMA_50'].iloc[-1]
    bias_1h = "🟩 Bullish" if ema20 > ema50 else "🟥 Bearish"

    # --- 4h ANALYSIS (FIX: Kleines 'h'!) ---
    df_4h = df_1h.set_index('time').resample('4h').agg({
        'open':'first','high':'max','low':'min','close':'last','volumeto':'sum'
    }).dropna().reset_index()
    
    df_4h.ta.rsi(length=14, append=True)
    df_4h.ta.macd(append=True)
    rsi = df_4h['RSI_14'].iloc[-1]
    macd = df_4h['MACDh_12_26_9'].iloc[-1]
    bias_4h = "🟩 Bullish" if rsi > 50 and macd > 0 else "🟥 Bearish" if rsi < 50 and macd < 0 else "🟧 Neutral"

    # --- 1d ANALYSIS ---
    last_close = df_1d['close'].iloc[-1]
    prev_close = df_1d['close'].iloc[-2]
    bias_1d = "🟩 Bullish (HH)" if last_close > prev_close else "🟥 Bearish (LL)"

    # --- SMC LEVELS ---
    avg_vol = df_1d['volumeto'].mean()
    supports = sorted([r['low'] for _, r in df_1d.iterrows() if r['low'] < last_close and r['volumeto'] > avg_vol * 1.2], reverse=True)[:3]
    resistances = sorted([r['high'] for _, r in df_1d.iterrows() if r['high'] > last_close and r['volumeto'] > avg_vol * 1.2])[:3]

    return {
        "p": last_close, "b1": bias_1h, "b4": bias_4h, "b1d": bias_1d,
        "supp": supports, "res": resistances
    }

def send_embed(symbol, d):
    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    color = Color.green() if "Bullish" in d['b1d'] else Color.red()
    
    embed = Embed(title=f"👑 Institutional Report: {symbol}/USD", color=color)
    embed.add_field(name="💵 Aktueller Preis", value=f"**{d['p']:,} $**", inline=False)
    
    embed.add_field(name="🟢 Short-term (1h)", value=d['b1'], inline=True)
    embed.add_field(name="🟡 Medium-term (4h)", value=d['b4'], inline=True)
    embed.add_field(name="🔴 Long-term (1d)", value=d['b1d'], inline=True)

    s_text = "\n".join([f"🟢 Support: **{s:,}$**" for s in d['supp']])
    r_text = "\n".join([f"🔴 Resistance: **{r:,}$**" for r in d['res']])
    embed.add_field(name="🛡️ SMC Support", value=s_text or "Suche...", inline=True)
    embed.add_field(name="⚔️ SMC Resistance", value=r_text or "Suche...", inline=True)

    webhook.send(embed=embed, username="Sentinel Alpha")

def main():
    if not WEBHOOK_URL or not CRYPTOCOMPARE_KEY:
        print("Fehler: API Keys fehlen.")
        return
    for s in ["BTC", "SOL", "SUI"]:
        data = analyze_coin(s)
        if data: send_embed(s, data)
        time.sleep(2)

if __name__ == "__main__":
    main()
