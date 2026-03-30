import os, requests, time
from datetime import datetime, timedelta

# API KEYS
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

def get_berlin_time():
    now = datetime.utcnow() + timedelta(hours=2)
    is_weekend = now.weekday() >= 5
    return now.strftime("%d.%m.%Y | %H:%M"), is_weekend

def get_market_context():
    """Sammelt alle Veto-Faktoren: DXY, Sentiment, Wochenende"""
    context = {"dxy_trend": "Neutral", "fng": "50", "weekend_mode": False}
    time_str, context["weekend_mode"] = get_berlin_time()
    
    try:
        # 1. Makro: DXY (Dollar Index)
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=DX-Y.NYB&apikey={ALPHA_VANTAGE_KEY}"
        res = requests.get(url, timeout=10).json()
        dxy_change = float(res.get("Global Quote", {}).get("10. change percent", "0").replace("%", ""))
        context["dxy_trend"] = "BULLISH (Risk-Off)" if dxy_change > 0.1 else "Stable/Bearish"
        
        # 2. Sentiment: Fear & Greed
        fng_res = requests.get("https://api.alternative.me/fng/", timeout=10).json()
        context["fng"] = fng_res['data'][0]['value']
    except: pass
    return context

def get_analysis(symbol, price_data, ctx):
    url = "https://api.groq.com/openai/v1/chat/completions"
    t_str, _ = get_berlin_time()
    
    # Der ultimative Profi-Prompt
    prompt = f"""
    DU BIST EIN INSTITUTIONELLER RISK-MANAGER. Analysiere {symbol.upper()}.
    
    DATEN:
    - Preis: {price_data['usd']}$ | 24h: {price_data['usd_24h_change']:.2f}%
    - DXY Trend: {ctx['dxy_trend']}
    - Fear & Greed: {ctx['fng']}
    - Wochenende (Low Liquidity): {ctx['weekend_mode']}
    
    DEINE LOGIK-VORGABEN:
    1. VETO-SYSTEM: Wenn DXY Bullisch ODER Wochenende ODER Fear > 75 -> KAUFEN ist VERBOTEN (Bias max. Neutral).
    2. SMC-LIQUIDITÄT: Suche nach 'Liquidation Magnets' unter dem aktuellen Preis.
    3. CONFIDENCE-SCORE: Berechne einen Wert (0-100%). Nur >80% erlaubt 'KAUFEN'.
    
    REPORT-STRUKTUR:
    👑 {symbol.upper()} - Risk & Liquidity Report
    
    🏛️ **Makro-Filter:** [DXY & Weekend Status]
    🧲 **Liquidity-Check:** [Wo liegen die Magnet-Level für Stop-Losses?]
    🎯 **Confidence-Score:** [X/100%]
    
    🛑 **SENTINEL ENTSCHEIDUNG:** **[BIAS]**
    ⚠️ **VETO/WARNUNG:** [Warum ist Vorsicht geboten? (z.B. Fake-Out Gefahr am Wochenende)]
    
    💶 **Preis:** {round(price_data['usd'] * 0.92, 2)} €
    """
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except: return None

def send():
    cg_res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,solana,sui&vs_currencies=usd&include_24hr_change=true").json()
    ctx = get_market_context()
    
    for sym, cg_id in {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}.items():
        print(f"Check {sym}...")
        report = get_analysis(sym, cg_res[cg_id], ctx)
        if report:
            requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": report})
            time.sleep(2)

if __name__ == "__main__":
    send()
