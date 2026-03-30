import os
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,sui&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def get_analysis(symbol, data):
    url = "https://api.groq.com/openai/v1/chat/completions"
    t = get_berlin_time()
    
    prompt = f"""
    Erstelle eine 4H-Analyse für {symbol.upper()}. 
    User: kingley3370 | Zeit: {t}.
    Daten: Preis {data['usd']}$, Change {data['usd_24h_change']:.2f}%.
    
    STRUKTUR (EXAKT SO EINHALTEN):
    👑 {symbol.upper()} ({symbol.upper()}/USD) - [Kreativer Titel]
    
    [Einleitungssatz zur aktuellen Lage]
    
    • **Aktueller Zustand:** [Kurzer Text mit Preis-Highlight]
    • **Schlüsselwiderstände:**
        ◦ [Level 1]: [Kurzer Text]
        ◦ [Level 2]: [ATH Info]
    • **Schlüsselunterstützungen:**
        ◦ [Level 1]: [Kurzer Text]
        ◦ [Level 2]: [Psychologische Marke]
    • **Szenarien:**
        ◦ **Bullisch 🚀:** [Text]
        ◦ **Bärisch 🐻:** [Text]
    • **Indikatoren:** [RSI und MACD Info]
    
    🛑 **ENTSCHEIDUNG:** **KAUFEN**, **VERKAUFEN** oder **ABWARTEN**.
    💶 **Preis in EURO:** ca. [Berechneter Preis] €
    """
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        else:
            print(f"Groq API Fehler {res.status_code}: {res.text}")
            return None
    except Exception as e:
        print(f"Fehler: {e}")
        return None

def send():
    data = get_market_data()
    if not data:
        print("Fehler: CoinGecko antwortet nicht.")
        return

    mapping = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cg_id in mapping.items():
        print(f"Verarbeite {sym}...")
        text = get_analysis(sym, data[cg_id])
        if text:
            requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
            print(f"✅ {sym} gesendet.")
        else:
            print(f"❌ {sym} fehlgeschlagen.")

if __name__ == "__main__":
    send()
