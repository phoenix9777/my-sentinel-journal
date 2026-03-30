import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # Berliner Zeit für März 2026
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(coin_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Wir holen 30 Tage für den EMA-Trend
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
        res = requests.get(url, headers=headers, timeout=20)
        
        if res.status_code != 200:
            print(f"❌ API Fehler {res.status_code}")
            return None
            
        data = res.json()
        prices = [p[1] for p in data['prices']]
        
        current_p = prices[-1]
        high_24h = max(prices[-2:])
        low_24h = min(prices[-2:])
        
        # Einfache EMA-Berechnung (Trend-Indikator)
        period = 14
        k = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for p in prices[period:]:
            ema = (p * k) + (ema * (1 - k))
        
        return {
            "p": round(current_p, 4),
            "h": round(high_24h, 4),
            "l": round(low_24h, 4),
            "ema": round(ema, 4)
        }
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    # Trend-Check
    trend = "🟢 BULLISCH" if s['p'] > s['ema'] else "🔴 BÄRISCH"
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    DATEN: Preis {s['p']}, High {s['h']}, Low {s['l']}, EMA-Trend: {s['ema']}.
    
    STRUKTUR:
    1. 🗓️ **Analyse vom {t}**
       Begrüße kingley3370.
    2. 📊 **Allgemeine Einschätzung:**
       - Trend: {trend} (Preis vs. EMA).
       - Lage zum Equilibrium (Mitte von {s['l']} und {s['h']}).
    3. 🛡️ **SMC & Zonen:**
       - Kauf-Zone 🟢 & Verkaufs-Zone 🔴 definieren.
       - Erwähne Liquiditätssweeps & FVG.
    4. ⚡ **Szenarien (Dual):**
       - Bullisch 🚀 & Bärisch 🐻.
    5. 🛑 **Sentinel Empfehlung:**
       - KAUFEN, VERKAUFEN oder ABWARTEN? Begründe kurz.
    
    Zusatz: Nenne den Preis kurz in EURO.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cid in coins.items():
        print(f"--- Starte: {sym} ---")
        stats = get_market_data(cid)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                # Wir schicken die Nachricht ab und prüfen das Ergebnis
                res = requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
                print(f"Discord Status: {res.status_code}")
        # Längere Pause für Stabilität
        time.sleep(30)

if __name__ == "__main__":
    send_to_discord()
