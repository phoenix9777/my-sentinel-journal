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
        # Wir nutzen den absolut stabilsten Endpunkt (Symbol Price Ticker)
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        res = requests.get(url, timeout=15)
        data = res.json()
        
        if 'price' in data:
            price = float(data['price'])
            # Da dieser Endpunkt kein High/Low liefert, schätzen wir die Range 
            # für die KI (oder lassen sie weg), um den API-Call extrem stabil zu halten.
            return {
                "p": price,
                "h": round(price * 1.02, 2), # Dummy High für die Analyse
                "l": round(price * 0.98, 2), # Dummy Low für die Analyse
                "c": "Stabil"
            }
        else:
            print(f"⚠️ Unerwartete Antwort von Binance für {symbol}: {data}")
            return None
    except Exception as e:
        print(f"❌ Schwerer Fehler bei {symbol}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USDT (Finora AI Style).
    Daten: Aktueller Preis {s['p']} USDT.
    
    STRUKTUR:
    1. 🗓️ **Analyse vom {t}**
       Begrüße kingley3370.
    2. 📊 **Allgemeine Einschätzung & SMC:** (Zonen 🟢/🔴, FVG, Sweeps)
    3. ⚡ **Szenarien:** Bullisch 🚀 & Bärisch 🐻.
    4. 🛑 **Empfehlung:** KAUFEN, VERKAUFEN oder ABWARTEN?
    
    Zusatz: Nenne den Preis in EURO. Kurz und knackig!
    """
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    coins = ["BTC", "SOL", "SUI"]
    for sym in coins:
        print(f"--- Verarbeite {sym} ---")
        stats = get_binance_data(sym)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                res = requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
                if res.status_code in [200, 204]:
                    print(f"🚀 {sym} erfolgreich gesendet!")
                else:
                    print(f"❌ Discord Fehler: {res.status_code}")
        time.sleep(5)

if __name__ == "__main__":
    send_to_discord()
q
