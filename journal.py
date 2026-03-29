import os
import time
from binance.client import Client
import requests
from datetime import datetime

# Daten aus GitHub Secrets
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y | %H:%M")

def get_live_data(symbol):
    try:
        # Initialisierung ohne API-Key (reicht für Marktdaten)
        client = Client("", "")
        klines = client.get_klines(symbol=f"{symbol}USDT", interval=Client.KLINE_INTERVAL_4HOUR, limit=50)
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        return {
            "price": closes[-1],
            "high": max(highs[-20:]),
            "low": min(lows[-20:]),
            "open": closes[0]
        }
    except Exception as e:
        print(f"❌ Binance-Fehler ({symbol}): {e}")
        return None

def get_crypto_analysis(coin, stats):
    # Wir nutzen 1.5-flash oder 2.0-flash (was bei dir aktiv ist)
    model = "gemini-1.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    # DER FINORA PROMPT - Hier entsteht die Magie
    prompt = f"""
    Du bist 'Sentinel Alpha 3.0', ein High-End Krypto-Analyst mit Fokus auf Smart Money Concepts (SMC).
    Erstelle eine Analyse für {coin}/USDT (4H-Chart) für kingley3370.
    
    DATEN STAND {timestamp}:
    - Aktueller Preis: {stats['price']} USDT
    - 20-Perioden High: {stats['high']}
    - 20-Perioden Low: {stats['low']}
    
    STRUKTUR (Finora AI Style):
    1. ### 📅 Analyse vom {timestamp}
       Begrüße kingley3370 professionell.
    
    2. ### 📊 Allgemeine Einschätzung:
       Analysiere die aktuelle Lage im 4H-Zeitrahmen. Wo steht der Preis im Verhältnis zum Equilibrium ({stats['low']} bis {stats['high']})?
    
    3. ### 🛡️ Technische Analyse & Smart Money Concepts:
       Diskutiere Liquiditäts-Sweeps, FVG-Zonen (Fair Value Gaps), Orderblocks und Market Structure (BOS/CHoCH).
    
    4. ### 📍 Kritische Preislevel:
       Nenne exakte Widerstände und Unterstützungen basierend auf den Daten.
    
    5. ### ⚡ Mögliche Trading-Setups:
       Erstelle ein Short- und ein Long-Setup mit konkreten 🎯 Entry, 🛑 Stop-Loss und 💰 Take-Profit Zonen.
    
    6. ### 🎯 Meine Erwartung:
       Gib einen klaren Bias ab. Beende mit: "Dies ist keine Anlageberatung... handle mit Bedacht."

    Schreibe auf Deutsch, nutze viele Emojis und Markdown-Formatierung.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_data = response.json()
        return res_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Gemini Fehler ({coin}): {e}")
        return None

def send_to_discord():
    if not WEBHOOK: return
    for coin in ["BTC", "SOL", "SUI"]:
        print(f"🔄 Verarbeite {coin}...")
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            if text:
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Alpha | {coin}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text[:2000]
                })
                print(f"✅ {coin} gesendet!")
        time.sleep(10)

if __name__ == "__main__":
    send_to_discord()
