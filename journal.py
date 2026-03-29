import requests
import os
import time
import numpy as np
from datetime import datetime

# Holt die Daten sicher aus den GitHub Secrets
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_current_time():
    # Erstellt einen Zeitstempel im Format: 30.03.2026 | 13:30
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
        data = requests.get(url).json()
        closes = np.array([float(c[4]) for c in data])
        highs = np.array([float(c[2]) for c in data])
        lows = np.array([float(c[3]) for c in data])
        
        rsi = calculate_rsi(closes)
        current_price = closes[-1]
        last_high = np.max(highs[-20:])
        last_low = np.min(lows[-20:])
        
        return {
            "price": current_price, 
            "rsi": round(rsi, 2), 
            "high": last_high, 
            "low": last_low
        }
    except Exception as e:
        print(f"Daten-Fehler: {e}")
        return None

def get_crypto_analysis(coin, stats):
    model = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    prompt = f"""
    Du bist 'Sentinel Alpha 3.0' (Powered by Finora AI Logic).
    Erstelle eine hochprofessionelle Marktanalyse für {coin}/USDT im 4H-Chart für kingley3370.
    ZEITSTEMPEL: {timestamp}
    
    AKTUELLE DATEN:
    - Preis: {stats['price']} USDT
    - RSI: {stats['rsi']}
    - Letztes lokales Hoch: {stats['high']}
    - Letztes lokales Tief: {stats['low']}
    
    STRUKTUR & TONFALL (Exakt wie Finora AI):
    1. '### 📅 Analyse vom {timestamp}'
       - Begrüßung: 'Hallo kingley3370, hier ist dein Sentinel Check für {coin}!'
    
    2. '### 📊 Allgemeine Einschätzung:'
       - Analysiere den Preis im Verhältnis zur Spanne ({stats['low']} - {stats['high']}).
       - Berechne ein Gleichgewichtsniveau (Equilibrium).
       - Trendbewertung (Bullisch/Bärisch) inkl. Indikatoren-Schwäche (RSI/MACD).
    
    3. '### 🛡️ Technische Analyse & Smart Money Concepts:'
       - Suche nach Liquiditäts-Sweeps unter {stats['low']}.
       - Identifiziere FVG-Zonen (Fair Value Gaps) und Orderblocks.
       - Erwähne Market Structure Shifts (BOS/CHoCH).
    
    4. '### 📍 Kritische Preislevel:'
       - Nenne exakte Widerstände und Unterstützungen in USDT.
    
    5. '### ⚡ Mögliche Trading-Setups:'
       - Erstelle ein detailliertes Short- und ein Long-Setup.
       - Nutze Bestätigungssignale (Pin-Bar, Engulfing).
    
    6. '### 🎯 Meine Erwartung (Sentinel AI):'
       - Gib einen klaren Bias ab.
       - Endsatz: "Dies ist keine Anlageberatung... handle mit Bedacht."

    Schreibe auf Deutsch, nutze viele Emojis und fette Formatierung für Discord.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return f"❌ Fehler bei der Analyse von {coin}."

def send_to_discord():
    for coin in ["BTC", "SOL", "SUI"]:
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            requests.post(WEBHOOK, json={
                "username": f"Sentinel Alpha | {coin}",
                "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                "content": text[:2000]
            })
        time.sleep(10)

if __name__ == "__main__":
    send_to_discord()
