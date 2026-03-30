import os
import time
import requests
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y | %H:%M")

def get_live_data(coin_id):
    try:
        # CoinGecko Public API (No Key needed)
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        market_data = data['market_data']
        current_price = market_data['current_price']['usd']
        high_24h = market_data['high_24h']['usd']
        low_24h = market_data['low_24h']['usd']
        
        return {
            "price": current_price,
            "high": high_24h,
            "low": low_24h,
            "equilibrium": round((high_24h + low_24h) / 2, 4),
            "change_24h": market_data['price_change_percentage_24h']
        }
    except Exception as e:
        print(f"❌ CoinGecko Fehler bei {coin_id}: {e}")
        return None

def get_crypto_analysis(coin_name, stats):
    # Gemini 2.5 Flash mit stabilem v1 Pfad
    model = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    prompt = f"""
    Du bist 'Sentinel Alpha 3.0', ein High-End Krypto-Analyst (Finora AI Style).
    Erstelle eine EXTREM AUSFÜHRLICHE 4H-Analyse für {coin_name}/USD für kingley3370.
    
    DATEN ({timestamp}):
    - Preis: {stats['price']} USD
    - 24H High: {stats['high']} | 24H Low: {stats['low']}
    - 24H Change: {stats['change_24h']}%
    - Equilibrium: {stats['equilibrium']}
    
    DEINE STRUKTUR (Finora AI Style):
    ### 📅 Analyse vom {timestamp}
    (Begrüße kingley3370 persönlich.)
    
    ### 📊 Allgemeine Einschätzung:
    (Equilibrium-Check, Trend-Dynamik, Volumen-Interpretation.)
    
    ### 🛡️ Technische Analyse & Smart Money Concepts:
    (FVG-Zonen, Liquiditäts-Sweeps, Orderblocks, BOS/CHoCH basierend auf den Range-Daten.)
    
    ### 📍 Kritische Preislevel:
    (Nenne exakte Widerstände & Supports in USD.)
    
    ### ⚡ Mögliche Trading-Setups:
    (Detaillierte Long & Short Szenarien mit 🎯 Entry, 🛑 SL, 💰 TP.)
    
    ### 🎯 Meine Erwartung:
    (Klarer Bias für kingley3370. Favorit-Szenario.)

    Schreibe auf Deutsch, nutze viele Emojis und Markdown. Beende mit Disclaimer.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=40)
        res_data = response.json()
        if 'candidates' in res_data:
            return res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"⚠️ API Fehler: {res_data}")
            return None
    except Exception as e:
        print(f"❌ Gemini Fehler: {e}")
        return None

def send_to_discord():
    if not WEBHOOK: return
    # CoinGecko IDs: 'bitcoin', 'solana', 'sui'
    coins = {"BTC": "bitcoin", "SOL": "solana", "SUI": "sui"}
    
    for symbol, cg_id in coins.items():
        print(f"🔄 Analysiere {symbol} via CoinGecko...")
        stats = get_live_data(cg_id)
        if stats:
            text = get_crypto_analysis(symbol, stats)
            if text:
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Alpha | {symbol}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text[:2000]
                })
                print(f"🚀 {symbol} gesendet!")
        time.sleep(15) # CoinGecko Rate Limit Schutz

if __name__ == "__main__":
    send_to_discord()
