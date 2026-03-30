import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def calculate_ema(prices, period):
    if len(prices) < period: return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * k) + (ema * (1 - k))
    return round(ema, 2)

def get_market_data(coin_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Aktuelle Daten
        url_now = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true"
        # Historische Daten für EMA (30 Tage)
        url_hist = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
        
        res_now = requests.get(url_now, headers=headers, timeout=20).json()
        res_hist = requests.get(url_hist, headers=headers, timeout=20).json()
        
        m = res_now['market_data']
        prices = [p[1] for p in res_hist['prices']]
        
        ema50 = calculate_ema(prices, 50) if len(prices) >= 30 else None # Näherungswert
        ema200 = calculate_ema(prices, 200) if len(prices) >= 200 else None
        
        cross_status = "Neutral"
        if ema50 and ema200:
            if ema50 > ema200: cross_status = "🟡 GOLDEN CROSS (Bullisch)"
            else: cross_status = "💀 DEATH CROSS (Bärisch)"

        return {
            "p": m['current_price']['usd'],
            "h": m['high_24h']['usd'],
            "l": m['low_24h']['usd'],
            "c": m['price_change_percentage_24h'],
            "ath": m['ath']['usd'],
            "ema_status": cross_status,
            "is_breakout": m['current_price']['usd'] >= m['high_24h']['usd']
        }
    except Exception as e:
        print(f"Fehler bei {coin_id}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    breakout_msg = "🚨 ACHTUNG: PREIS BRICHT GERADE DAS 24H HOCH! (BULLISH BREAKOUT)" if s['is_breakout'] else "Seitwärtsbewegung innerhalb der Range."

    prompt = f"""
    Erstelle eine PROFESSIONELLE 4H-Analyse für {symbol}/USD (Finora AI Elite Style).
    DATEN: Preis {s['p']}, High {s['h']}, Low {s['l']}, Change {s['c']}%, EMA: {s['ema_status']}.
    
    STRUKTUR:
    1. 🗓️ **Analyse vom {t}**
       {breakout_msg}
    
    2. 📊 **Allgemeine Einschätzung & EMA Cross:**
       - Analyse des {s['ema_status']}. Was bedeutet das für den Trend?
       - Lage zum Equilibrium (Mitte von {s['l']} und {s['h']}).
    
    3. 🛡️ **SMC & Zonen:**
       - Kauf-Zone (Demand) 🟢 und Verkaufs-Zone (Supply) 🔴 definieren.
       - Erwähne FVG-Gaps und Liquiditätssweeps.
    
    4. ⚡ **Szenarien (Dual-Weg):**
       - **Bullisch 🚀**: Bedingung für Anstieg Richtung {s['ath']}.
       - **Bärisch 🐻**: Risiko bei Bruch von {s['l']}.
    
    5. 📍 **Key Levels:**
       - Liste Support (🟢) und Resistance (🔴) Linien auf.
    
    6. 🎯 **Sentinel Erwartung:**
       - Favorit-Szenario für kingley3370. Disclaimer.
    """
    
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=40)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cid in coins.items():
        print(f"Verarbeite {sym}...")
        stats = get_market_data(cid)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Elite | {sym}",
                    "content": text
                })
        time.sleep(25) # Höheres Delay für EMA-Abfragen (Rate Limit!)

if __name__ == "__main__":
    send_to_discord()
