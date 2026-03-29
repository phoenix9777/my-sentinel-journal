import requests
import os
import time
import pandas as pd
import pandas_ta as ta

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_live_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=4h&limit=100"
        data = requests.get(url).json()
        df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'cts', 'qv', 'nt', 'tbv', 'tqv', 'ignore'])
        df['c'] = df['c'].astype(float)
        
        rsi_val = ta.rsi(df['c'], length=14).iloc[-1]
        macd_df = ta.macd(df['c'])
        macd_val = macd_df.iloc[-1].to_dict()
        current_price = df['c'].iloc[-1]
        
        fng_val = "N/A"
        try:
            fng_res = requests.get("https://api.alternative.me/fng/").json()
            fng_val = fng_res['data'][0]['value']
        except: pass
        
        return {"price": current_price, "rsi": round(rsi_val, 2), "macd": macd_val, "fng": fng_val}
    except Exception as e:
        print(f"Fehler: {e}")
        return None

def get_crypto_analysis(coin, stats):
    model = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        f"Hallo kingley3370! Erstelle eine fette 4H-Analyse für {coin}/USDT.\n"
        f"DATEN: Preis {stats['price']}, RSI {stats['rsi']}, MACD {stats['macd']}, Fear&Greed {stats['fng']}.\n\n"
        "ANWEISUNG:\n"
        "1. Nutze VIELE Emojis (z.B. 🚀 für Bullish, 📉 für Bearish, ⚖️ für Neutral).\n"
        "2. Nutze Smart Money Concepts (SMC), FVG-Zonen und Liquiditäts-Sweeps.\n"
        "3. Erstelle eine Sektion 'Mögliches Setup' mit 🎯 Entry, 🛑 Stop-Loss und 💰 Take-Profit.\n"
        "4. Sprich kingley3370 direkt an. Sei extrem ausführlich (Finora AI Style).\n"
        "5. Formatiere alles perfekt für Discord (Fett, Code-Blöcke, Listen)."
    )
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return f"❌ Fehler bei der Analyse für {coin}."

def send_to_discord():
    coins = ["BTC", "SOL", "SUI"]
    for coin in coins:
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            # Discord Nachricht senden
            requests.post(WEBHOOK, json={"username": f"Sentinel Alpha | {coin}", "content": text[:2000]})
        time.sleep(5) # Pause gegen Rate-Limits

if __name__ == "__main__":
    send_to_discord()
