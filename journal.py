import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(symbol):
    try:
        # CryptoCompare API - Stabil, schnell und kein Geoblocking für GitHub
        url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol}&tsyms=USD"
        res = requests.get(url, timeout=20)
        data = res.json()
        
        raw = data['RAW'][symbol]['USD']
        
        return {
            "p": raw['PRICE'],
            "h": raw['HIGH24HOUR'],
            "l": raw['LOW24HOUR'],
            "c": raw['CHANGEPCT24HOUR']
        }
    except Exception as e:
        print(f"❌ Fehler bei {symbol}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    Daten: Preis {s['p']}, High {s['h']}, Low {s['l']}, Change {s['c']}%.
    
    STRUKTUR:
    1. 🗓️ **Analyse vom {t}**
       Begrüße kingley3370.
    2. 📊 **Allgemeine Einschätzung & SMC:** (Zonen 🟢/🔴, FVG, Sweeps)
    3. ⚡ **Szenarien:** Bullisch 🚀 & Bärisch 🐻.
    4. 🛑 **Sentinel Empfehlung:** KAUFEN, VERKAUFEN oder ABWARTEN? + Begründung.
    
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
        stats = get_market_data(sym)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
                print(f"🚀 {sym} erfolgreich gesendet!")
        time.sleep(10)

if __name__ == "__main__":
    send_to_discord()
