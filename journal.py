import requests
import os
import time
import pandas as pd
import pandas_ta as ta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_live_data(symbol):
    # 1. Kurs & Indikatoren von Binance (4H Chart)
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=4h&limit=100"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'cts', 'qv', 'nt', 'tbv', 'tqv', 'ignore'])
    df['c'] = df['c'].astype(float)
    
    # Technische Indikatoren berechnen
    rsi = df.ta.rsi(length=14).iloc[-1]
    macd = df.ta.macd().iloc[-1] # Gibt MACD, Histogramm und Signal
    current_price = df['c'].iloc[-1]
    
    # 2. Fear & Greed Index
    fng_data = requests.get("https://api.alternative.me/fng/").json()
    fng_value = fng_data['data'][0]['value']
    fng_label = fng_data['data'][0]['value_classification']
    
    return {
        "price": current_price,
        "rsi": round(rsi, 2),
        "macd": macd.to_dict(),
        "fng": f"{fng_value} ({fng_label})"
    }

def get_crypto_analysis(coin, stats):
    model = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        f"Hallo kingley3370, hier sind die LIVE-DATEN für {coin}:\n"
        f"- Aktueller Preis: {stats['price']} USDT\n"
        f"- RSI (14): {stats['rsi']}\n"
        f"- MACD: {stats['macd']}\n"
        f"- Markt-Sentiment (Fear & Greed): {stats['fng']}\n\n"
        "Erstelle eine detaillierte Finora-AI-Style Analyse. Nutze Smart Money Concepts (SMC), "
        "erkläre FVG-Zonen und Liquiditäts-Sweeps basierend auf diesen echten Werten. "
        "Gib konkrete Setups (Long/Short) mit TP und SL an. Sei extrem professionell."
    )
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Fehler bei {coin}: {str(e)}"

def send_to_discord():
    coins = ["BTC", "SOL", "SUI"]
    for coin in coins:
        stats = get_live_data(coin)
        text = get_crypto_analysis(coin, stats)
        payload = {
            "username": f"Sentinel Alpha | {coin}",
            "content": text[:2000]
        }
        requests.post(WEBHOOK, json=payload)
        time.sleep(5)

if __name__ == "__main__":
    send_to_discord()
