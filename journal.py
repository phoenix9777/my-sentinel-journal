import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(coin_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200: return None
        data = res.json()
        prices = [p[1] for p in data['prices']]
        current_p = prices[-1]
        def calc_ema(p_list, period):
            k = 2 / (period + 1)
            ema = sum(p_list[:period]) / period
            for p in p_list[period:]: ema = (p * k) + (ema * (1 - k))
            return ema
        return {
            "p": round(current_p, 4),
            "h": round(max(prices[-2:]), 4),
            "l": round(min(prices[-2:]), 4),
            "ema": round(calc_ema(prices, 14), 4)
        }
    except: return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    trend = "🟢 BULLISCH" if s['p'] > s['ema'] else "🔴 BÄRISCH"
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    Daten: Preis {s['p']}, High {s['h']}, Low {s['l']}, EMA {s['ema']}. Trend: {trend}.
    
    STRUKTUR:
    1. 🗓️ **Analyse vom {t}**
    2. 📊 **Einschätzung:** Trendlage & Equilibrium.
    3. 🛡️ **SMC:** Kauf-Zone 🟢 & Verkaufs-Zone 🔴, FVG & Sweeps.
    4. ⚡ **Szenarien:** Bullisch 🚀 & Bärisch 🐻.
    5. 🛑 **Empfehlung:** KAUFEN, VERKAUFEN oder ABWARTEN? + Begründung.
    
    Zusatz: Preis in EURO. KEIN langes Gelaber, komm auf den Punkt.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    for sym, cid in coins.items():
        print(f"--- Starte: {sym} ---")
        stats = get_market_data(cid)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                # Discord Limit Fix: Text splitten falls > 2000 Zeichen
                if len(text) > 1900:
                    parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
                    for part in parts:
                        requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": part})
                        time.sleep(1)
                else:
                    requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text})
                print(f"✅ {sym} gesendet.")
        time.sleep(40) # Längere Pause für SOL Stabilität

if __name__ == "__main__":
    send_to_discord()
