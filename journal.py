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
            "c": m['price_change_percentage_24h'],
            "ath": m['ath']['usd']
        }
    except: return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Erstelle eine ELITE 4H-Analyse für {symbol}/USD für kingley3370 (Finora AI Style).
    DATEN: Preis {s['p']} USD, 24H Range {s['l']} - {s['h']}, Change {s['c']}%, Allzeithoch {s['ath']}.
    
    STRUKTUR (Halte dich exakt an dieses Layout):
    
    🗓️ **Analyse vom {t}**
    Begrüße kingley3370 kurz. {symbol} Analyse ist bereit.
    
    📊 **Aktueller Zustand:**
    - Beschreibe kurz die Lage (z.B. pendelt um Marke X, Momentum verlangsamt/beschleunigt).
    
    📍 **Schlüsselwiderstände:**
    - Liste 2-3 Zonen mit 🔴 auf (z.B. {s['h']} USD - Erkläre kurz die Bedeutung).
    
    📍 **Schlüsselunterstützungen:**
    - Liste 2-3 Zonen mit 🟢 auf (z.B. {s['l']} USD - Erkläre kurz die Bedeutung).
    
    ⚡ **Szenarien (Der Plan):**
    - **Bullisch 🚀**: Beschreibe die Bedingung für eine Rallye (z.B. Bruch von Widerstand X) und das Ziel (z.B. Richtung ATH {s['ath']}).
    - **Bärisch 🐻**: Beschreibe das Risiko (z.B. Rückfall unter Support Y) und das Ziel bei Abverkauf.
    
    🛡️ **SMC & Indikatoren:**
    - Kurze Analyse zu RSI und MACD (🔴/🟢). Erwähne FVG oder Liquiditäts-Sweeps.
    
    🎯 **Sentinel Erwartung:**
    - Dein Favorit für die nächsten 4-12 Stunden. Disclaimer am Ende.
    
    WICHTIG: Sei präzise mit Zahlen, nutze Markdown und Emojis. Trenne die Sektionen sauber.
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
                payload = {
                    "username": f"Sentinel Elite | {sym}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text
                }
                requests.post(WEBHOOK, json=payload)
                print(f"✅ {sym} gesendet.")
        time.sleep(12)

if __name__ == "__main__":
    send_to_discord()
