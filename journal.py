import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    # UTC+2 für Berlin (März 2026 Sommerzeit)
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(coin_id):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Wir holen 30 Tage Historie für EMA und Range
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=30&interval=daily"
        res = requests.get(url, headers=headers, timeout=20)
        
        if res.status_code != 200:
            print(f"❌ API Fehler bei {coin_id}: Status {res.status_code}")
            return None
            
        data = res.json()
        prices = [p[1] for p in data['prices']]
        
        current_p = prices[-1]
        # Range der letzten 2 Tage
        high_24h = max(prices[-2:])
        low_24h = min(prices[-2:])
        
        # EMA-Berechnung (14er Periode als Trend-Indikator)
        period = 14
        k = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price * k) + (ema * (1 - k))
        
        return {
            "p": round(current_p, 2),
            "h": round(high_24h, 2),
            "l": round(low_24h, 2),
            "ema": round(ema, 2),
            "is_breakout": current_p >= high_24h
        }
    except Exception as e:
        print(f"❌ Fehler bei Datenabruf {coin_id}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    # Gemini 2.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    breakout_status = "🚨 BREAKOUT ALARM: Kurs testet lokales Hoch!" if s['is_breakout'] else "Markt konsolidiert in der Range."
    trend = "🟢 BULLISCH" if s['p'] > s['ema'] else "🔴 BÄRISCH"

    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    DATEN: Preis {s['p']}, High {s['h']}, Low {s['l']}, Trend-Basis (EMA): {s['ema']}.
    
    Layout:
    1. 🗓️ **Analyse vom {t}**
       {breakout_status}
    2. 📊 **Allgemeine Einschätzung:**
       - Status: {trend} (Preis über/unter EMA).
       - Lage zum Equilibrium (Mitte von {s['l']} und {s['h']}).
    3. 🛡️ **SMC & Zonen:**
       - Kauf-Zone 🟢 und Verkaufs-Zone 🔴 definieren.
       - Erwähne FVG-Gaps und Liquiditätssweeps.
    4. ⚡ **Szenarien (Dual):**
       - Bullisch 🚀: Ziel bei Bruch von {s['h']}.
       - Bärisch 🐻: Risiko bei Fall unter {s['l']}.
    5. 📍 **Key Levels:**
       - Support (🟢) und Resistance (🔴) mit Preisen.
    6. 🎯 **Sentinel Erwartung:**
       - Dein Bias für kingley3370. Disclaimer.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"⚠️ Gemini Fehler bei {symbol}: {data}")
            return None
    except Exception as e:
        print(f"❌ Gemini Timeout/Fehler bei {symbol}: {e}")
        return None

def send_to_discord():
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    
    for sym, cid in coins.items():
        print(f"--- Starte Verarbeitung: {sym} ---")
        stats = get_market_data(cid)
        
        if stats:
            print(f"✅ Daten für {sym} erhalten. Generiere Analyse...")
            text = get_crypto_analysis(sym, stats)
            
            if text:
                res = requests.post(WEBHOOK, json={
                    "username": f"Sentinel Elite | {sym}",
                    "content": text
                })
                if res.status_code in [200, 204]:
                    print(f"🚀 {sym} erfolgreich an Discord gesendet!")
                else:
                    print(f"❌ Discord Fehler bei {sym}: {res.status_code}")
            else:
                print(f"⚠️ Analyse für {sym} konnte nicht erstellt werden.")
        
        # WICHTIG: 30 Sekunden echte Pause zwischen den Coins
        print(f"⏳ Pause (30s) vor dem nächsten Coin...")
        time.sleep(30)

if __name__ == "__main__":
    send_to_discord()
