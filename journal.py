import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # UTC+2 für Berlin im März 2026
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_live_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true"
        data = requests.get(url, timeout=15).json()
        m = data['market_data']
        return {
            "p": m['current_price']['usd'],
            "h": m['high_24h']['usd'],
            "l": m['low_24h']['usd'],
            "c": m['price_change_percentage_24h']
        }
    except: return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Erstelle eine INSTITUTIONELLE 4H-Analyse für {symbol}/USD für kingley3370.
    DATEN: Preis {s['p']}, 24H Range {s['l']} - {s['h']}, Change {s['c']}%.
    
    STRUKTUR (Finora AI Elite Style):
    1. 🗓️ **Analyse vom {t}**
       Begrüße kingley3370 kurz und direkt.
    
    2. 📊 **Allgemeine Einschätzung:**
       - Lage zum Equilibrium (Mitte von {s['l']} und {s['h']}).
       - Marktdynamik: Nutze 🔴/🟢 für Indikatoren (RSI, MACD, ADX).
    
    3. 🛡️ **SMC & Technische Analyse:**
       - Erwähne Liquiditäts-Sweeps, FVG-Gaps und Orderblocks (OB).
       - Definiere die **Kauf-Zone (Demand)** und **Verkaufs-Zone (Supply)**.
    
    4. 📍 **Key Levels (Support & Resistance):**
       - Liste exakte Linien: 🟢 Support 1-3 | 🔴 Resistance 1-3.
    
    5. ⚡ **Trading-Setups:**
       - Konkretes Szenario für Long & Short.
       - Setze 🎯 Entry, 🛑 Stop-Loss und 💰 Take-Profit.
    
    6. 🎯 **Sentinel Erwartung:**
       - Dein Favorit-Szenario. Disclaimer am Ende.
    
    WICHTIG: Sei extrem detailliert, nutze Markdown und Emojis.
    """
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cid in coins.items():
        stats = get_live_data(cid)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                # Wir senden pro Coin eine eigene Nachricht -> Kein Abbruch mehr!
                payload = {
                    "username": f"Sentinel Elite | {sym}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text
                }
                requests.post(WEBHOOK, json=payload)
                print(f"✅ {sym} gesendet.")
        time.sleep(10) # Schutz vor Discord Rate-Limit

if __name__ == "__main__":
    send_to_discord()
