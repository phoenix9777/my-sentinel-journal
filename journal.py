import requests
import os
import time
import numpy as np
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y | %H:%M")

def calculate_rsi(prices, period=14):
    if len(prices) <= period: return 50
    deltas = np.diff(prices)
    up = deltas[deltas > 0].sum() / period
    down = -deltas[deltas < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100. - 100. / (1. + rs)

def get_live_data(symbol):
    try:
        # Erhöhte Sicherheit beim Abruf
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=4h&limit=50"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # Prüfung: Haben wir wirklich eine Liste mit Daten bekommen?
        if not isinstance(data, list) or len(data) == 0:
            print(f"⚠️ Keine Daten von Binance für {symbol} erhalten.")
            return None
            
        # Wir extrahieren die Spalten sicher
        closes = []
        highs = []
        lows = []
        
        for candle in data:
            closes.append(float(candle[4]))
            highs.append(float(candle[2]))
            lows.append(float(candle[3]))
            
        closes = np.array(closes)
        
        return {
            "price": closes[-1], 
            "rsi": round(calculate_rsi(closes), 2), 
            "high": max(highs[-20:]), 
            "low": min(lows[-20:])
        }
    except Exception as e:
        print(f"❌ Detail-Fehler bei {symbol}: {e}")
        return None

def get_crypto_analysis(coin, stats):
    # WICHTIG: Wir nutzen jetzt gemini-1.5-flash als stabilen Fallback, falls 2.5 noch zickt
    model = "gemini-1.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    prompt = f"""
    Erstelle eine professionelle Finora-Style Analyse für {coin}/USDT (4H-Chart) am {timestamp}.
    KINGLEY3370 Analyse-Auftrag.
    
    DATEN:
    - Aktueller Preis: {stats['price']} USDT
    - RSI: {stats['rsi']}
    - Letztes Hoch: {stats['high']}
    - Letztes Tief: {stats['low']}
    
    Struktur: 
    1. Begrüßung kingley3370 & Datum
    2. Allgemeine Einschätzung & SMC Tech (FVG, Sweeps, CHoCH)
    3. Kritische Level & Trading Setups (Entry, SL, TP)
    4. Bias & Erwartung
    Nutze viele Emojis und Markdown.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
        res_data = response.json()
        return res_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Gemini Fehler: {e}")
        return None

def send_to_discord():
    if not WEBHOOK:
        print("❌ WEBHOOK SECRET FEHLT!")
        return

    for coin in ["BTC", "SOL", "SUI"]:
        print(f"🔄 Verarbeite {coin}...")
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            if text:
                res = requests.post(WEBHOOK, json={"username": f"Sentinel | {coin}", "content": text[:2000]})
                if res.status_code in [200, 204]:
                    print(f"✅ {coin} gesendet!")
                else:
                    print(f"❌ Discord Fehler: {res.status_code}")
        time.sleep(5)

if __name__ == "__main__":
    send_to_discord()
