import os
import requests
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
from discord import SyncWebhook, Embed, Color

# API KEYS (In GitHub Secrets!)
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CRYPTOCOMPARE_KEY = os.getenv("CRYPTOCOMPARE_KEY")

def get_berlin_time():
    # UTC+2 für Berlin
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def fetch_data(symbol, limit, timeframe):
    """Holt historische OHLCV Daten von CryptoCompare"""
    try:
        url = f"https://min-api.cryptocompare.com/data/v2/histo{timeframe}?fsym={symbol}&tsym=USD&limit={limit}&api_key={CRYPTOCOMPARE_KEY}"
        res = requests.get(url, timeout=20).json()
        df = pd.DataFrame(res['Data']['Data'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except Exception as e:
        print(f"Fehler beim Datenholen ({symbol}, {timeframe}): {e}")
        return None

def analyze_coin(symbol):
    print(f"--- Starte Deep-Analysis für {symbol} ---")
    
    # 1. Daten holen (1H, 4H, 1D)
    df_1h = fetch_data(symbol, 100, "hour") # Für EMA Cross
    df_4h = fetch_data(symbol, 100, "hour") # CryptoCompare hat kein histo4hour im Free Tier, wir resamplen
    df_1d = fetch_data(symbol, 100, "day")  # Für Marktstruktur & Major Levels
    
    if df_1h is None or df_1d is None: return None

    # Resample 1H to 4H (Wichtig für korrekten RSI/MACD)
    df_4h.set_index('time', inplace=True)
    df_4h = df_4h.resample('4H').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volumeto': 'sum'}).dropna().reset_index()

    # --- MTF BIAS BERECHNUNG ---
    
    # Short-term (1H): EMA 20/50 Cross
    df_1h.ta.ema(length=20, append=True)
    df_1h.ta.ema(length=50, append=True)
    ema_20 = df_1h['EMA_20'].iloc[-1]
    ema_50 = df_1h['EMA_50'].iloc[-1]
    bias_1h = "🟩 Bullish (EMA 20 > 50)" if ema_20 > ema_50 else "🟥 Bearish (EMA 20 < 50)"

    # Medium-term (4H): RSI & MACD
    df_4h.ta.rsi(length=14, append=True)
    df_4h.ta.macd(append=True)
    rsi_4h = df_4h['RSI_14'].iloc[-1]
    macd_h = df_4h['MACDh_12_26_9'].iloc[-1] # Histogramm
    
    if rsi_4h > 55 and macd_h > 0: bias_4h = "🟩 Bullish (RSI/MACD Confirm)"
    elif rsi_4h < 45 and macd_h < 0: bias_4h = "🟥 Bearish (RSI/MACD Confirm)"
    else: bias_4h = "🟧 Neutral"

    # Long-term (1D): Marktstruktur (HH/LL)
    # Vereinfachte Logik: Vergleiche aktuelles Close mit EMA 200
    df_1d.ta.ema(length=50, append=True) # Wir nutzen EMA50 daily als Proxy für Struktur
    current_price = df_1d['close'].iloc[-1]
    ema_50_d = df_1d['EMA_50'].iloc[-1]
    bias_1d = "🟩 Bullish (Above Daily EMA 50)" if current_price > ema_50_d else "🟥 Bearish (Below Daily EMA 50)"

    # --- SUPPORT & RESISTANCE (SMC/VOLUMEN) ---
    # Wir suchen nach Swing Highs/Lows im Daily Chart mit hohem Volumen
    
    major_levels = []
    # Finde Swing Lows (Support)
    for i in range(5, len(df_1d) - 5):
        if df_1d['low'].iloc[i] < df_1d['low'].iloc[i-1] and df_1d['low'].iloc[i] < df_1d['low'].iloc[i+1]:
            # Prüfe ob Volumen überdurchschnittlich war (Volumen-Spitze)
            avg_vol = df_1d['volumeto'].iloc[i-5:i+5].mean()
            if df_1d['volumeto'].iloc[i] > avg_vol * 1.3: # 30% über Avg
                major_levels.append(('Support', round(df_1d['low'].iloc[i], 2), df_1d['time'].iloc[i]))

    # Finde Swing Highs (Resistance)
    for i in range(5, len(df_1d) - 5):
        if df_1d['high'].iloc[i] > df_1d['high'].iloc[i-1] and df_1d['high'].iloc[i] > df_1d['high'].iloc[i+1]:
            avg_vol = df_1d['volumeto'].iloc[i-5:i+5].mean()
            if df_1d['volumeto'].iloc[i] > avg_vol * 1.3:
                major_levels.append(('Resistance', round(df_1d['high'].iloc[i], 2), df_1d['time'].iloc[i]))

    # Filter & Sortiere Level nahe am aktuellen Preis
    supports = sorted([l[1] for l in major_levels if l[0] == 'Support' and l[1] < current_price], reverse=True)[:3]
    resistances = sorted([l[1] for l in major_levels if l[ l[0] == 'Resistance' and l[1] > current_price]])[:3]

    # Distanz zum nächsten Support berechnen
    dist_supp = "N/A"
    if supports:
        dist_pct = ((current_price - supports[0]) / current_price) * 100
        dist_supp = f"{supports[0]}$ (-{dist_pct:.1f}%)"

    return {
        "price": current_price,
        "bias_1h": bias_1h, "ema_20": ema_20, "ema_50": ema_50,
        "bias_4h": bias_4h, "rsi": rsi_4h,
        "bias_1d": bias_1d,
        "supports": supports, "resistances": resistances, "dist_supp": dist_supp
    }

def send_embed(symbol, data):
    t = get_berlin_time()
    webhook = SyncWebhook.from_url(WEBHOOK_URL)

    # Bestimme Farbe des Embeds basierend auf Long-Term Bias
    embed_color = Color.green() if "Bullish" in data['bias_1d'] else Color.red()

    embed = Embed(
        title=f"👑 Institutional Report: {symbol.upper()}/USD",
        description=f"Automatisierte Deep-Analysis vom {t} (Berliner Zeit).",
        color=embed_color
    )
    embed.set_author(name="Sentinel Alpha - Tactical Intelligence", icon_url="https://i.imgur.com/xmO3sO7.png") # Beispiel-Icon
    embed.add_field(name="💵 Aktueller Kurs", value=f"**{data['price']:,}$**", inline=False)

    # Timeframe Analysis Fields (Wie gewünscht)
    embed.add_field(name="⏱️ Short-term (1H)", value=f"{data['bias_1h']}\n(EMA 20: {data['ema_20']:.2f} / 50: {data['ema_50']:.2f})", inline=True)
    embed.add_field(name="⏱️ Medium-term (4H)", value=f"{data['bias_4h']}\n(RSI: {data['rsi']:.1f})", inline=True)
    embed.add_field(name="⏱️ Long-term (1D)", value=f"{data['bias_1d']}", inline=True)

    # Support & Resistance Fields (SMC)
    supp_text = "\n".join([f"🟢 Major Support {i+1}: **{val}$**" for i, val in enumerate(data['supports'])]) or "Keine starken Level gefunden."
    res_text = "\n".join([f"🔴 Major Resistance {i+1}: **{val}$**" for i, val in enumerate(data['resistances'])]) or "Keine starken Level gefunden."
    
    embed.add_field(name="🛡️ SMC Support Zonen (Daily High Volume)", value=supp_text, inline=True)
    embed.add_field(name="⚔️ SMC Resistance Zonen (Daily High Volume)", value=res_text, inline=True)
    
    # Risk Metric
    embed.add_field(name="⚠️ Nächster Major Support (Distanz)", value=f"**{data['dist_supp']}**", inline=False)

    embed.set_footer(text=f"Sentinel Alpha v4.2 | Daten: CryptoCompare | Preis in EUR: ca. {round(data['price'] * 0.92, 2)} €")

    webhook.send(embed=embed, username=f"Sentinel Alpha | {symbol.upper()}")

def main():
    if not WEBHOOK_URL or not CRYPTOCOMPARE_KEY:
        print("Fehler: API Keys fehlen in GitHub Secrets.")
        return

    coins = ["BTC", "SOL", "SUI"]
    for sym in coins:
        data = analyze_coin(sym)
        if data:
            send_embed(sym, data)
            time.sleep(5) # Pause zwischen den Coins

if __name__ == "__main__":
    main()
