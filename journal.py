import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data():
    try:
        # Ein einziger Call für alle Coins (spart Quota & Zeit)
        ids = "bitcoin,solana,sui"
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true&include_last_updated_at=true"
        res = requests.get(url, timeout=15)
        return res.json()
    except Exception as e:
        print(f"❌ CoinGecko Fehler: {e}")
        return None

def get_crypto_analysis(symbol, data):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    # Kompakter Prompt für schnelle, klare Antworten
    prompt = f"""
    Erstelle eine 4H-Analyse für {symbol.upper()}. 
    User: kingley3370. Zeit: {t}.
    Daten: Preis {data['usd']}$, 24h Change {data['usd_24h_change']:.2f}%.
    
    STRUKTUR (WICHTIG):
    1. 🗓️ **Analyse vom {t}**
    2. 📊 **Markt-Check:** Kurz & knackig (Trend, Zonen).
    3. 🛑 **SENTINEL ENTSCHEIDUNG:** - Schreib groß: **KAUFEN**, **VERKAUFEN** oder **ABWARTEN**.
       - Begründe es kurz (SMC/Bias).
    4. 💶 **Preis in EURO**.
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
    }

    try:
        res = requests.post(url, json=payload, timeout=60)
        # Falls Gemini doch mal blockt (429), kurz warten
        if res.status_code == 429:
            time.sleep(30)
            return get_crypto_analysis(symbol, data)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    data = get_market_data()
    if not data:
        print("⚠️ Keine Daten von CoinGecko.")
        return

    mapping = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    
    for sym, cg_id in mapping.items():
        print(f"--- Analyse {sym} ---")
        if cg_id in data:
            analysis = get_crypto_analysis(sym, data[cg_id])
            if analysis:
                # Schneller Versand an Discord
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Elite | {sym}", 
                    "content": analysis[:1990]
                })
                print(f"🚀 {sym} gesendet!")
        # Kleine Pause für die Gemini-Leitung
        time.sleep(5)

if __name__ == "__main__":
    send_to_discord()
