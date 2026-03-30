import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_berlin_time():
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(symbol):
    try:
        url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol}&tsyms=USD"
        res = requests.get(url, timeout=20)
        data = res.json()
        raw = data['RAW'][symbol]['USD']
        return {"p": raw['PRICE'], "h": raw['HIGH24HOUR'], "l": raw['LOW24HOUR'], "c": raw['CHANGEPCT24HOUR']}
    except: return None

def get_crypto_analysis(symbol, s):
    # Wir nutzen v1beta für bessere Safety-Settings Kontrolle
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    # Der alte, gut strukturierte Prompt, filtersicher formuliert
    payload = {
        "contents": [{"parts": [{"text": f"Schreibe eine ELITE 4H-Analyse für {symbol}/USD (Finora AI Style). Daten: Preis {s['p']}, High {s['h']}, Low {s['l']}, Change {s['c']}%. Erstelle ein Journal für user kingley3370 mit Headlines und Emojis. Struktur: 1. Analyse vom {t}. 2. Allgemeine Einschätzung & SMC-Zonen 🟢/🔴 (FVG, Liquidity). 3. Duale Szenarien (🚀/🐻). 4. Strategischer Bias mit Begründung. Preis auch in EURO nennen. KEINE Längenbeschränkung, antworte im Markdown-Format für Discord."}]}],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.8
        }
    }
    
    try:
        res = requests.post(url, json=payload, timeout=90)
        res_data = res.json()
        
        # Wir loggen genau, falls Gemini blockiert
        if 'candidates' in res_data:
            candidate = res_data['candidates'][0]
            if 'content' in candidate:
                return candidate['content']['parts'][0]['text']
            elif 'finishReason' in candidate:
                print(f"⚠️ Gemini blockiert wegen: {candidate['finishReason']}")
        
        print(f"⚠️ Unerwartete Antwort für {symbol}: {res_data}")
        return None
    except Exception as e:
        print(f"⚠️ Fehler bei {symbol}: {e}")
        return None

def send_to_discord():
    coins = ["BTC", "SOL", "SUI"]
    for sym in coins:
        print(f"--- Verarbeite {sym} ---")
        stats = get_market_data(sym)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                # Wichtig: Text splitten, falls er > 2000 Zeichen ist, um Abschneiden zu verhindern
                if len(text) > 1900:
                    parts = [text[i:i+1900] for i in range(0, len(text), 1900)]
                    for part in parts:
                        requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": part})
                        time.sleep(1) # Kurze Pause zwischen den Teilen
                else:
                    requests.post(WEBHOOK, json={"username": f"Sentinel Elite | {sym}", "content": text})
                print(f"🚀 {sym} gesendet!")
            else:
                print(f"⚠️ {sym} Analyse fehlgeschlagen.")
        else:
            print(f"⚠️ Keine Marktdaten für {sym}.")
        time.sleep(15)

if __name__ == "__main__":
    send_to_discord()
