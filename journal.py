import os
import time
import yfinance as yf
import requests
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_current_time():
    return datetime.now().strftime("%d.%m.%Y | %H:%M")

def get_live_data(symbol):
    try:
        # Ticker-Korrektur: SUI wird auf Yahoo oft als SUI-USD geführt
        ticker_symbol = f"{symbol}-USD"
        ticker = yf.Ticker(ticker_symbol)
        
        # Wir versuchen erst 1h Daten, falls das scheitert 1d
        df = ticker.history(period="5d", interval="1h")
        if df.empty:
            df = ticker.history(period="10d", interval="1d")
        
        if df.empty:
            print(f"⚠️ Keine Daten für {symbol}")
            return None
            
        current_price = df['Close'].iloc[-1]
        recent_high = df['High'].tail(24).max()
        recent_low = df['Low'].tail(24).min()
        
        return {
            "price": round(current_price, 4),
            "high": round(recent_high, 4),
            "low": round(recent_low, 4),
            "equilibrium": round((recent_high + recent_low) / 2, 4)
        }
    except Exception as e:
        print(f"❌ Yahoo Fehler bei {symbol}: {e}")
        return None

def get_crypto_analysis(coin, stats):
    # Wir nutzen 1.5-flash, das ist am kulantesten bei Finanz-Prompts
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    # Prompt optimiert, um Gemini-Sperren zu umgehen (Rein edukativer Fokus)
    prompt = f"""
    Schreibe eine edukative Marktanalyse für {coin}/USD am {timestamp}. 
    Nutze die Daten: Aktueller Preis {stats['price']}, High {stats['high']}, Low {stats['low']}.
    
    Analysiere basierend auf Smart Money Concepts:
    1. Einschätzung: Preis im Verhältnis zum Equilibrium ({stats['equilibrium']}).
    2. SMC Konzepte: Erkläre theoretische FVG-Zonen und Liquiditäts-Sweeps.
    3. Level: Nenne Widerstände und Unterstützungen.
    4. Setup-Idee: Skizziere ein mögliches Long- und Short-Szenario für kingley3370.
    
    Formatierung: Professionell, viele Emojis, Finora AI Style. 
    WICHTIG: Beende IMMER mit: 'Dies ist keine Anlageberatung!'
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_data = response.json()
        
        # Sicherheits-Check für die Antwort
        if 'candidates' in res_data:
            return res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"⚠️ Gemini API Response Fehler bei {coin}: {res_data}")
            return None
    except Exception as e:
        print(f"❌ Gemini Verbindungsfehler bei {coin}: {e}")
        return None

def send_to_discord():
    if not WEBHOOK: return
    for coin in ["BTC", "SOL", "SUI"]:
        print(f"🔄 Analysiere {coin}...")
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            if text:
                payload = {
                    "username": f"Sentinel Alpha | {coin}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text[:1900] # Puffer lassen
                }
                requests.post(WEBHOOK, json=payload)
                print(f"🚀 {coin} gesendet!")
        time.sleep(10)

if __name__ == "__main__":
    send_to_discord()
