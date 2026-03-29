import requests
import os
import time
import numpy as np
from datetime import datetime

# Holt die Daten sicher aus den GitHub Secrets
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y | %H:%M")

def calculate_rsi(prices, period=14):
    if len(prices) < period: return 50
    deltas = np.diff(prices)
    up = deltas[deltas > 0].sum() / period
    down = -deltas[deltas < 0].sum() / period
    if down == 0: return 100
    rs = up / down
    return 100. - 100. / (1. + rs)

def get_live_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=4h&limit=100"
        response = requests.get(url)
        data = response.json()
        closes = np.array([float(c[4]) for c in data])
        highs = np.array([float(c[2]) for c in data])
        lows = np.array([float(c[3]) for c in data])
        
        rsi = calculate_rsi(closes)
        return {
            "price": closes[-1], 
            "rsi": round(rsi, 2), 
            "high": np.max(highs[-20:]), 
            "low": np.min(lows[-20:])
        }
    except Exception as e:
        print(f"❌ Fehler beim Binance-Datenabruf ({symbol}): {e}")
        return None

def get_crypto_analysis(coin, stats):
    model = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    prompt = f"Erstelle eine Finora-Style Analyse für {coin} (Preis: {stats['price']}, RSI: {stats['rsi']}) für kingley3370 am {timestamp}. Nutze Emojis und SMC."
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        res_data = response.json()
        if "candidates" not in res_data:
            print(f"⚠️ Gemini API Fehler ({coin}): {res_data}")
            return None
        return res_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Gemini-Verbindungsfehler ({coin}): {e}")
        return None

def send_to_discord():
    if not WEBHOOK:
        print("❌ FEHLER: DISCORD_WEBHOOK Secret wurde nicht gefunden!")
        return

    for coin in ["BTC", "SOL", "SUI"]:
        print(f"🔄 Starte Analyse für {coin}...")
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            if text:
                payload = {
                    "username": f"Sentinel Alpha | {coin}",
                    "content": text[:2000]
                }
                res = requests.post(WEBHOOK, json=payload)
                if res.status_code == 204 or res.status_code == 200:
                    print(f"✅ {coin} erfolgreich an Discord gesendet!")
                else:
                    print(f"❌ Discord Fehler ({coin}): Status {res.status_code} - {res.text}")
            else:
                print(f"⚠️ Keine Analyse für {coin} generiert.")
        time.sleep(5)

if __name__ == "__main__":
    send_to_discord()
