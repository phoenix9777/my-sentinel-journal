import os
import time
import requests
from datetime import datetime, timedelta

# Secrets abrufen
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # Berechnet die Zeit für Deutschland (UTC+1 oder UTC+2)
    # Da wir März 2026 haben, ist bereits Sommerzeit (UTC+2)
    berlin_time = datetime.utcnow() + timedelta(hours=2)
    return berlin_time.strftime("%d.%m.%Y | %H:%M")

def get_live_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true"
        data = requests.get(url, timeout=15).json()
        market = data['market_data']
        
        return {
            "price": market['current_price']['usd'],
            "high": market['high_24h']['usd'],
            "low": market['low_24h']['usd'],
            "change": market['price_change_percentage_24h'],
            "ath": market['ath']['usd']
        }
    except Exception as e:
        print(f"Datenfehler: {e}")
        return None

def get_crypto_analysis(symbol, stats):
    model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_berlin_time()
    
    # Der ultimative Finora-Prompt
    prompt = f"""
    Du bist 'Sentinel Alpha 3.0', ein High-End Trading-Algorithmus (Finora AI Style).
    Erstelle eine EXTREM DETAILLIERTE 4H-Analyse für {symbol}/USD.
    
    DATEN STAND {timestamp}:
    - Preis: {stats['price']} USD
    - 24H Range: {stats['low']} - {stats['high']}
    - 24H Change: {stats['change']}%
    
    STRUKTUR-VORGABE (Halte dich exakt daran!):
    
    🗓️ **Analyse vom {timestamp}**
    Sei gegrüßt, kingley3370! 🫡 Sentinel Alpha 3.0 ist online. Hier ist deine institutionelle 4H-Analyse.
    
    📊 **Allgemeine Einschätzung:**
    - Aktueller Preis & Lage in der Handelsspanne (Oben/Unten).
    - Berechne das Gleichgewichtsniveau (Equilibrium) aus {stats['low']} und {stats['high']}.
    - Trendbewertung: Nutze Indikatoren-Symbole (z.B. 🔴 RSI bärisch, 🟢 ADX bullisch).
    - Kommentar zu Volatilität und Volumen.
    
    🛡️ **Technische Analyse & Smart Money Concepts:**
    - Analysiere Ausbrüche, Impulsbewegungen und Liquiditäts-Sweeps (Manipulation).
    - Nenne konkrete Zonen: FVG (Fair Value Gaps), Orderblocks (OB), Demand/Supply.
    - Achte auf Market Structure (BOS / CHoCH).
    
    📍 **Kritische Preislevel:**
    - Liste mindestens 5 Widerstände und 3 Unterstützungen mit exakten Werten auf.
    - Nutze 🔴 für Widerstände und 🟢 für Unterstützungen.
    
    ⚡ **Mögliche Trading-Setups:**
    - Erstelle ein detailliertes 'Short-Setup' und ein 'Long-Setup (Reversal)'.
    - Nenne Bedingungen für den Einstieg (z.B. Pin-Bar, Engulfing auf 15min/1h).
    - Definiere 🎯 Entry, 🛑 Stop-Loss und 💰 Take-Profit.
    
    🎯 **Meine Erwartung (Sentinel AI):**
    - Gib deinen klaren Bias ab. Was ist dein Favorit-Szenario?
    - Beende mit dem Disclaimer: "Dies ist keine Anlageberatung... handle mit Bedacht."

    FORMATIERUNG: Nutze Fettdruck, Listen und viele Emojis. Sei ausführlich wie ein Profi-Analyst.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=40)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for symbol, cg_id in coins.items():
        stats = get_live_data(cg_id)
        if stats:
            text = get_crypto_analysis(symbol, stats)
            if text:
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Alpha | {symbol}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text[:1990] # Discord Limit
                })
        time.sleep(15)

if __name__ == "__main__":
    send_to_discord()
