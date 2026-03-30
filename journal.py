import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # UTC+2 Sommerzeit 2026
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(coin_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Einfacherer API-Call: Nur aktuelle Marktdaten, keine Historie
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        res = requests.get(url, headers=headers, timeout=30)
        
        if res.status_code != 200:
            print(f"❌ CoinGecko Fehler bei {coin_id}: Status {res.status_code}")
            return None
            
        data = res.json()
        m = data['market_data']
        
        return {
            "p": m['current_price']['usd'],
            "h": m['high_24h']['usd'],
            "l": m['low_24h']['usd'],
            "c": m['price_change_percentage_24h']
        }
    except Exception as e:
        print(f"❌ Fehler bei {coin_id}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    Daten: Preis {s['p']}, High {s['h']}, Low {s['l']}, Change {s['c']}%.
    
    Layout:
    1. 🗓️ **Analyse vom {t}**
    2. 📊 **Allgemeine Einschätzung & SMC:** (Zonen 🟢/🔴, FVG, Sweeps)
    3. ⚡ **Szenarien:** Bullisch 🚀 & Bärisch 🐻.
    4. 🛑 **Empfehlung:** KAUFEN, VERKAUFEN oder ABWARTEN?
    
    Nenne den Preis in EURO. Kurz und knackig!
    """
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cid in coins.items():
        print(f"--- Verarbeite {sym} ---")
        stats = get_market_data(cid)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
                print(f"🚀 {sym} gesendet!")
        
        print("Warte 45 Sekunden...")
        time.sleep(45) # Maximale Sicherheit gegen Rate-Limits

if __name__ == "__main__":
    send_to_discord()
