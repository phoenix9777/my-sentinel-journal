import os, requests, time
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data():
    try:
        # Wir holen USD Preise UND den EUR Wechselkurs in einem Rutsch
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,sui,eur&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=10).json()
        usd_eur = res['eur']['usd'] # Wie viel 1 EUR in USD wert ist
        return res, usd_eur
    except: return None, 1.09

def get_sentiment():
    try:
        res = requests.get("https://api.alternative.me/fng/").json()
        return f"{res['data'][0]['value']} ({res['data'][0]['value_classification']})"
    except: return "N/A"

def get_macro():
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=DX-Y.NYB&apikey={ALPHA_VANTAGE_KEY}"
        res = requests.get(url).json()
        change = res.get("Global Quote", {}).get("10. change percent", "0%")
        return change
    except: return "0%"

def get_analysis(symbol, data, fng, macro, eur_rate):
    url = "https://api.groq.com/openai/v1/chat/completions"
    t = get_berlin_time()
    
    # Wir berechnen den Euro Preis direkt im Code, damit die KI nicht lügt
    price_eur = round(data['usd'] / eur_rate, 2) if symbol != "BTC" else round(data['usd'] / eur_rate, 0)

    prompt = f"""
    Schreibe eine PROFESSIONELLE MARKTANALYSE für {symbol.upper()}. 
    Kein Gelaber, keine Einleitung, keine Erklärungen der Logik.
    
    DATEN:
    Preis: {data['usd']}$ ({price_eur}€)
    24h Change: {data['usd_24h_change']:.2f}%
    Fear & Greed: {fng}
    DXY Change: {macro}

    STRUKTUR (STRENG EINHALTEN):
    👑 {symbol.upper()} - Institutional Report ({t})
    
    🏛️ **Makro- & Sentiment-Status:**
    • DXY: {macro} (Einfluss auf Krypto-Liquidity)
    • Markt-Psychologie: {fng}
    
    📊 **Markt-Check & SMC:**
    • Trend: [Kurze Einschätzung basierend auf 24h Change]
    • SMC-Zonen: [Nenne realistische Support/Resistance Level basierend auf dem Preis]
    
    🛑 **SENTINEL ENTSCHEIDUNG:** **[KAUFEN, VERKAUFEN oder ABWARTEN]**
    • **Begründung:** [Maximal 15 Wörter]
    
    ⚠️ **RISIKOWARNUNG:** [Ein Satz zur Gefahr bei DXY-Stärke oder Extreme Fear]
    
    💶 **Preis:** {price_eur} €
    """
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4 # Niedrige Temperature = Weniger Gelaber, mehr Fakten
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except: return None

def send():
    cg_data, eur_rate = get_market_data()
    if not cg_data: return
    
    fng = get_sentiment()
    macro = get_macro()
    
    mapping = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cg_id in mapping.items():
        print(f"Analyse {sym}...")
        text = get_analysis(sym, cg_data[cg_id], fng, macro, eur_rate)
        if text:
            requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text})
            time.sleep(2)

if __name__ == "__main__":
    send()
