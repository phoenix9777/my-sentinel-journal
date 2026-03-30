import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(symbol):
    # 3 Versuche, falls die API kurz zickt
    for i in range(3):
        try:
            url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol}&tsyms=USD"
            res = requests.get(url, timeout=20)
            data = res.json()
            raw = data['RAW'][symbol]['USD']
            return {
                "p": raw['PRICE'],
                "h": raw['HIGH24HOUR'],
                "l": raw['LOW24HOUR'],
                "c": raw['CHANGEPCT24HOUR']
            }
        except:
            time.sleep(5)
            continue
    return None

def get_crypto_analysis(symbol, s):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    prompt = f"""
    Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style).
    Daten: Preis {s['p']}, High {s['h']}, Low {s['l']}, Change {s['c']}%.
    
    Layout:
    1. 🗓️ **Analyse vom {t}**
       Begrüße kingley3370.
    2. 📊 **Einschätzung & SMC:** (Zonen 🟢/🔴, FVG, Sweeps)
    3. ⚡ **Szenarien:** Bullisch 🚀 & Bärisch 🐻.
    4. 🛑 **Sentinel Empfehlung:** KAUFEN, VERKAUFEN oder ABWARTEN? + Begründung.
    
    Zusatz: Preis in EURO. Kurz und knackig!
    """
    
    try:
        # Timeout auf 90 Sekunden erhöht!
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"⚠️ Gemini Timeout bei {symbol}: {e}")
        return None

def send_to_discord():
    coins = ["BTC", "SOL", "SUI"]
    for sym in coins:
        print(f"--- Verarbeite {sym} ---")
        stats = get_market_data(sym)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                # Nachricht senden und Ergebnis prüfen
                discord_res = requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text[:1990]})
                if discord_res.status_code in [200, 204]:
                    print(f"🚀 {sym} erfolgreich gesendet!")
                else:
                    print(f"❌ Discord Fehler bei {sym}: {discord_res.status_code}")
            else:
                print(f"⚠️ Keine Analyse für {sym} generiert.")
        else:
            print(f"⚠️ Keine Marktdaten für {sym} erhalten.")
        
        # Pause zwischen den Coins
        time.sleep(15)

if __name__ == "__main__":
    send_to_discord()
