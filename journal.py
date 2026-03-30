import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_binance_data(symbol):
    try:
        # 24h Ticker Daten von Binance
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
        res = requests.get(url, timeout=10)
        data = res.json()
        
        return {
            "p": float(data['lastPrice']),
            "h": float(data['highPrice']),
            "l": float(data['lowPrice']),
            "c": float(data['priceChangePercent'])
        }
    except Exception as e:
        print(f"❌ Binance Fehler bei {symbol}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USDT (Finora AI Style).
    Daten: Preis {s['p']}, High {s['h']}, Low {s['l']}, Change {s['c']}%.
    
    Layout:
    1. 🗓️ **Analyse vom {t}**
    2. 📊 **Allgemeine Einschätzung & SMC:** (Zonen 🟢/🔴, FVG, Sweeps)
    3. ⚡ **Szenarien:** Bullisch 🚀 & Bärisch 🐻.
    4. 🛑 **Empfehlung:** KAUFEN, VERKAUFEN oder ABWARTEN?
    
    Nenne den Preis in EURO. Kurz und knackig!
    """
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=40)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    # Binance nutzt Symbole wie BTC, SOL, SUI
    coins = ["BTC", "SOL", "SUI"]
    for sym in coins:
        print(f"--- Verarbeite {sym} ---")
        stats = get_binance_data(sym)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
                print(f"🚀 {sym} erfolgreich gesendet!")
        
        # Nur 5 Sekunden Pause, Binance ist schnell!
        time.sleep(5)

if __name__ == "__main__":
    send_to_discord()
