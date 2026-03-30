import os, requests, time
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY") # Kostenlos auf alphavantage.co

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_sentiment():
    """Holt den Fear & Greed Index (Psychologie)"""
    try:
        res = requests.get("https://api.alternative.me/fng/").json()
        fng_val = res['data'][0]['value']
        fng_class = res['data'][0]['value_classification']
        return f"Fear & Greed Index: {fng_val} ({fng_class})"
    except: return "Sentiment-Daten aktuell nicht verfügbar."

def get_macro():
    """Holt DXY (Dollar Index) via Alpha Vantage"""
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=DX-Y.NYB&apikey={ALPHA_VANTAGE_KEY}"
        res = requests.get(url).json()
        quote = res.get("Global Quote", {})
        change = quote.get("10. change percent", "0%")
        return f"DXY Change: {change}"
    except: return "DXY-Daten nicht verfügbar."

def get_analysis(symbol, data, fng, macro):
    url = "https://api.groq.com/openai/v1/chat/completions"
    t = get_berlin_time()
    
    # Institutioneller Prompt mit Makro-Logik
    prompt = f"""
    INSTITUTIONAL 4H ANALYSIS FOR {symbol.upper()}
    Preis: {data['usd']}$ | 24h Change: {data['usd_24h_change']:.2f}%
    Markt-Sentiment: {fng}
    Makro-Status (DXY): {macro}

    ANALYSE-LOGIK (WICHTIG):
    1. Wenn DXY steigt (>0.1%): Sei bärisch/vorsichtig (Dollar-Stärke drückt Krypto).
    2. Wenn F&G < 30 (Extreme Fear): Suche nach 'Long Sweeps' (Smart Money kauft Angst).
    3. Wenn F&G > 70 (Greed): Achte auf 'Liquidity Traps' (Smart Money verkauft in Gier).

    STRUKTUR (EXAKT):
    👑 {symbol.upper()} - Institutional Risk Report
    
    • 🏛️ **Makro- & Sentiment-Check:** [Analysiere DXY & Fear/Greed]
    • 📊 **Markt-Check & SMC:** [Trend & SMC-Zonen]
    • 🛑 **SENTINEL ENTSCHEIDUNG:** **[BIAS]** (KAUFEN/VERKAUFEN/ABWARTEN)
    • ⚠️ **RISIKOWARNUNG:** [Explizite Warnung bei Makro-Gefahr]
    
    💶 **Preis in EURO:** ca. [Preis] €
    """
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content'] if res.status_code == 200 else None
    except: return None

def send():
    # 1. Daten sammeln
    cg_data = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,sui&vs_currencies=usd&include_24hr_change=true").json()
    fng = get_sentiment()
    macro = get_macro()
    
    mapping = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cg_id in mapping.items():
        print(f"Verarbeite {sym}...")
        text = get_analysis(sym, cg_data[cg_id], fng, macro)
        if text:
            requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
            time.sleep(2)

if __name__ == "__main__":
    send()
