import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # UTC+2 (März 2026 Sommerzeit)
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(coin_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 30 Tage Historie für EMA-Berechnung
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
        res = requests.get(url, headers=headers, timeout=20)
        
        if res.status_code != 200:
            print(f"❌ API Fehler bei {coin_id}: Status {res.status_code}")
            return None
            
        data = res.json()
        prices = [p[1] for p in data['prices']]
        
        current_p = prices[-1]
        high_24h = max(prices[-2:])
        low_24h = min(prices[-2:])
        
        # EMA-Berechnung (10er Fast / 25er Slow)
        def calc_ema(p_list, period):
            k = 2 / (period + 1)
            ema = sum(p_list[:period]) / period
            for price in p_list[period:]:
                ema = (price * k) + (ema * (1 - k))
            return ema

        ema_fast = calc_ema(prices, 10)
        ema_slow = calc_ema(prices, 25)
        
        # Cross-Logik (FEHLER BEHOBEN: ema_fast statt path_fast)
        cross_msg = "🟡 Neutral"
        if ema_fast > ema_slow:
            cross_msg = "🟢 GOLDEN CROSS (Bullisch)"
        elif ema_fast < ema_slow:
            cross_msg = "💀 DEATH CROSS (Bärisch)"

        return {
            "p": round(current_p, 2),
            "h": round(high_24h, 2),
            "l": round(low_24h, 2),
            "ema_f": round(ema_fast, 2),
            "ema_s": round(ema_slow, 2),
            "cross": cross_msg,
            "is_breakout": current_p >= high_24h
        }
    except Exception as e:
        print(f"❌ Fehler bei {coin_id}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    breakout_status = "🚨 BREAKOUT ALARM: Kurs testet lokales Hoch!" if s['is_breakout'] else "Markt konsolidiert."

    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    DATEN: Preis {s['p']}, High {s['h']}, Low {s['l']}, EMA-Fast: {s['ema_f']}, EMA-Slow: {s['ema_s']}, Signal: {s['cross']}.
    
    Layout & Inhalt:
    1. 🗓️ **Analyse vom {t}**
       {breakout_status}
    2. 📊 **Trend-Check & EMA Cross:**
       - Aktuelles Signal: {s['cross']}
       - Lage: Preis steht bei {s['p']} USD.
    3. 🛡️ **SMC & Zonen:**
       - Kauf-Zone 🟢 und Verkaufs-Zone 🔴 definieren.
       - Erwähne Liquiditätssweeps und FVG-Gaps.
    4. ⚡ **Szenarien (Dual):**
       - Bullisch 🚀: Was passiert bei Bruch von {s['h']}?
       - Bärisch 🐻: Was passiert bei Bruch von {s['l']}?
    5. 📍 **Key Levels:**
       - Support (🟢) und Resistance (🔴) mit Preisen.
    6. 🛑 **Sentinel Handels-Empfehlung:**
       - Gib kingley3370 eine klare Ansage: KAUFEN, VERKAUFEN oder ABWARTEN.
       - Begründe kurz das Risk/Reward.
    
    Zusatz: Nenne den Preis kurz in EURO für die Steuer-Dokumentation.
    Disclaimer am Ende.
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
            print(f"✅ Daten erhalten für {sym}. Generiere Analyse...")
            text = get_crypto_analysis(sym, stats)
            if text:
                requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text})
                print(f"🚀 {sym} gesendet!")
        time.sleep(30)

if __name__ == "__main__":
    send_to_discord()
