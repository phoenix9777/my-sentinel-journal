import os
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # UTC+2 für Berlin
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data():
    try:
        # Kompakter Call für alle drei Coins
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,sui&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def get_analysis(symbol, data):
    # Nutzung von Gemini 2.0 Flash für die schnellste Antwortzeit
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    # Der ultimative Prompt für das visuelle Layout
    prompt = f"""
    Erstelle eine 4H-Analyse für {symbol.upper()}. 
    User: kingley3370 | Zeit: {t}.
    Daten: Preis {data['usd']}$, Change {data['usd_24h_change']:.2f}%.
    
    FORMAT-VORGABE (STRENG EINHALTEN):
    Schreibe exakt in diesem Look für Discord (Markdown):
    
    [Emoji] [Coin-Name] ([Symbol]/USD) - [Kurzer, kreativer Untertitel]
    
    1. 🗓️ **Analyse vom {t}**
       [Ein kurzer Satz zur aktuellen Lage]
    
    2. 📊 **Markt-Check & SMC**
       * [Bulletpoint zu Struktur/Trend]
       * [Bulletpoint zu Zonen 🟢/🔴]
       * [Bulletpoint zu Indikatoren]
    
    3. 🛑 **SENTINEL ENTSCHEIDUNG:**
       **[Fettes KAUFEN, VERKAUFEN oder ABWARTEN]**
       * **Begründung:** [Kurzer, knackiger Satz]
    
    4. 💶 **Preis in EURO:** ca. [Berechneter Euro-Preis] €
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}]
    }
    
    try:
        # Direkter Call ohne Pausen
        res = requests.post(url, json=payload, timeout=30)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Gemini API Fehler {res.status_code}")
            return None
    except:
        return None

def send():
    # 1. Daten holen
    data = get_market_data()
    if not data:
        print("Fehler: CoinGecko antwortet nicht.")
        return

    # 2. Coins verarbeiten
    mapping = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    
    for sym, cg_id in mapping.items():
        print(f"Verarbeite {sym}...")
        if cg_id in data:
            text = get_analysis(sym, data[cg_id])
            
            if text:
                # Sofort an Discord senden
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Elite | {sym}", 
                    "content": text[:1990]
                })
                print(f"✅ {sym} erfolgreich gesendet.")
            else:
                print(f"❌ {sym} Analyse fehlgeschlagen.")

if __name__ == "__main__":
    send()
