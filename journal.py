import os, requests, time
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data():
    """Holt Preise. Wenn EUR fehlt, nutzen wir einen Standardkurs."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,sui&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=15).json()
        return res
    except:
        return None

def get_sentiment():
    try:
        res = requests.get("https://api.alternative.me/fng/", timeout=10).json()
        return f"{res['data'][0]['value']} ({res['data'][0]['value_classification']})"
    except: return "Neutral"

def get_macro():
    if not ALPHA_VANTAGE_KEY: return "0%"
    try:
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=DX-Y.NYB&apikey={ALPHA_VANTAGE_KEY}"
        res = requests.get(url, timeout=10).json()
        return res.get("Global Quote", {}).get("10. change percent", "0%")
    except: return "0%"

def get_analysis(symbol, data, fng, macro):
    url = "https://api.groq.com/openai/v1/chat/completions"
    t = get_berlin_time()
    
    # Sicherer Euro-Check (Kurs ca. 0.92)
    price_usd = data['usd']
    price_eur = round(price_usd * 0.92, 2)

    prompt = f"""
    Schreibe eine PROFESSIONELLE MARKTANALYSE für {symbol.upper()}. 
    KEINE Einleitung ("Hier ist die Analyse..."), KEIN Gelaber. Direkt mit dem Report starten.
    
    WERTE:
    Preis: {price_usd}$ ({price_eur}€)
    24h: {data['usd_24h_change']:.2f}%
    Fear & Greed: {fng}
    DXY Change: {macro}

    STRUKTUR:
    👑 {symbol.upper()} - Institutional Report ({t})
    
    🏛️ **Makro- & Sentiment-Status:**
    • DXY: {macro} (Einfluss auf Krypto-Liquidity)
    • Markt-Psychologie: {fng}
    
    📊 **Markt-Check & SMC:**
    • Trend: [Einschätzung basierend auf {data['usd_24h_change']:.2f}%]
    • SMC-Zonen: [Nenne Support/Resistance nahe {price_usd}$]
    
    🛑 **SENTINEL ENTSCHEIDUNG:** **[KAUFEN, VERKAUFEN oder ABWARTEN]**
    • **Begründung:** [Max 1 Satz]
    
    ⚠️ **RISIKOWARNUNG:** [Ein Satz zur Gefahr]
    
    💶 **Preis:** {price_eur} €
    """
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3 # Sehr stabil und sachlich
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Groq Fehler: {e}")
        return None

def send():
    print("Starte Datensammlung...")
    cg_data = get_market_data()
    if not cg_data:
        print("Konnte CoinGecko nicht erreichen.")
        return
    
    fng = get_sentiment()
    macro = get_macro()
    
    mapping = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cg_id in mapping.items():
        if cg_id in cg_data:
            print(f"Analysiere {sym}...")
            text = get_analysis(sym, cg_data[cg_id], fng, macro)
            if text:
                requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text})
                print(f"✅ {sym} gesendet.")
        time.sleep(2)

if __name__ == "__main__":
    send()
