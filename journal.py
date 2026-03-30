import os
import time
import requests
from datetime import datetime, timedelta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")
WUNSCH_COIN = os.getenv("INPUT_SYMBOL")

def get_berlin_time():
    # Berliner Zeit (Sommerzeit 2026: UTC+2)
    return (datetime.utcnow() + timedelta(hours=2)).strftime("%d.%m.%Y | %H:%M")

def get_market_data(symbol):
    try:
        # CryptoCompare für professionelle Daten-Tiefe
        url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol}&tsyms=USD"
        res = requests.get(url, timeout=20)
        data = res.json()
        raw = data['RAW'][symbol]['USD']
        return {
            "p": raw['PRICE'], 
            "h": raw['HIGH24HOUR'], 
            "l": raw['LOW24HOUR'], 
            "c": raw['CHANGEPCT24HOUR'],
            "v": raw['VOLUME24HOURTO']
        }
    except Exception as e:
        print(f"Fehler bei Datenabfrage {symbol}: {e}")
        return None

def get_crypto_analysis(symbol, s):
    # Nutzung von Gemini 2.0 Flash für maximale Geschwindigkeit und Präzision
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    t = get_berlin_time()
    
    # Institutioneller Prompt-Aufbau
    prompt = f"""
    Erstelle eine INSTITUTIONELLE 4H-MARKTANALYSE für {symbol}/USD im Sentinel Alpha 3.0 Elite-Style.
    
    DATEN-INPUT:
    - Preis: {s['p']} USD
    - 24h High: {s['h']} | 24h Low: {s['l']}
    - 24h Change: {s['c']}%
    - Volumen: {s['v']} USD
    
    ANALYSE-VORGABEN (STRENG EINHALTEN):
    1. MARKET STRUCTURE: Definiere die Phase (z.B. Bearish Markdown, Accumulation). Multi-Timeframe Check (4h/12h/Daily).
    2. INDICATOR ASSESSMENT: Bewerte RSI, MACD-Histogramm und simuliere die Trendstärke (ADX). Erwähne EMA 50/200 Status (z.B. Death Cross).
    3. SMC & FLOW: Identifiziere FVG (Fair Value Gaps) und Orderblocks. Analyse der Volume-Conviction.
    4. PRICE SCENARIOS: Bullisch 🚀 & Bärisch 🐻 mit konkreten Key-Levels.
    5. STRATEGISCHER BIAS: Klare Handlungsanweisung für kingley3370 (Bias: Long/Short/Neutral) mit Begründung.
    
    ZUSATZ:
    - Nenne den Preis am Ende kurz in EURO.
    - Nutze fette Headlines, Emojis und saubere Gliederung für Discord (Markdown).
    """

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "safetySettings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}],
        "generationConfig": {"temperature": 0.75, "topP": 0.95}
    }

    try:
        res = requests.post(url, json=payload, timeout=90)
        if res.status_code == 429:
            print("⏳ API-Quota erreicht. Warte 60s...")
            time.sleep(60)
            return get_crypto_analysis(symbol, s)
        
        res_json = res.json()
        return res_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini-Fehler bei {symbol}: {e}")
        return None

def send_to_discord():
    # Check ob manueller Request oder automatischer Lauf
    if WUNSCH_COIN and WUNSCH_COIN.strip() != "":
        coins = [WUNSCH_COIN.strip().upper()]
    else:
        coins = ["BTC", "SOL", "SUI"]

    for sym in coins:
        print(f"--- Starte Analyse für {sym} ---")
        stats = get_market_data(sym)
        if stats:
            text = get_crypto_analysis(sym, stats)
            if text:
                # Discord-Split Logik (Max 2000 Zeichen pro Nachricht)
                if len(text) > 1950:
                    parts = [text[i:i+1950] for i in range(0, len(text), 1950)]
                    for part in parts:
                        requests.post(WEBHOOK, json={"username": f"Sentinel Alpha | {sym}", "content": part})
                        time.sleep(1)
                else:
                    requests.post(WEBHOOK, json={"username": f"Sentinel Alpha | {sym}", "content": text})
                print(f"✅ {sym} erfolgreich an Discord gesendet.")
        time.sleep(15) # Safety-Pause

if __name__ == "__main__":
    send_to_discord()
