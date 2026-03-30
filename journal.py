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
        ticker_map = {"BTC": "BTC-USD", "SOL": "SOL-USD", "SUI": "SUI-USD"}
        ticker = yf.Ticker(ticker_map[symbol])
        
        # Holt Daten für die letzten 7 Tage (Stunden-Intervall)
        df = ticker.history(period="7d", interval="1h")
        
        if df.empty:
            return None
            
        current_price = df['Close'].iloc[-1]
        recent_high = df['High'].tail(48).max() # Letzte 48h High
        recent_low = df['Low'].tail(48).min()   # Letzte 48h Low
        volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].tail(24).mean()
        
        return {
            "price": round(current_price, 2),
            "high": round(recent_high, 2),
            "low": round(recent_low, 2),
            "equilibrium": round((recent_high + recent_low) / 2, 2),
            "vol_status": "erhöht" if volume > avg_volume else "normal",
            "volume": volume
        }
    except Exception as e:
        print(f"❌ Fehler bei {symbol}: {e}")
        return None

def get_crypto_analysis(coin, stats):
    # Wir nutzen das stärkste Modell für viel Text
    model = "gemini-1.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    timestamp = get_current_time()
    
    # DER MASSIVE PROMPT FÜR MAXIMALE TIEFE
    prompt = f"""
    Du bist 'Sentinel Alpha 3.0', das fortschrittlichste KI-Modell für Krypto-Analysen (Finora AI Style).
    Erstelle eine EXTREM AUSFÜHRLICHE 4H-Analyse für {coin}/USD für kingley3370.
    
    AKTUELLE DATENSTAND {timestamp}:
    - Kurs: {stats['price']} USD
    - 48H-Range High: {stats['high']} | Low: {stats['low']}
    - Equilibrium (Gleichgewicht): {stats['equilibrium']}
    - Volumen-Status: {stats['vol_status']}
    
    DEINE STRUKTUR (Zwingend ausführlich!):
    
    ### 📅 Analyse vom {timestamp}
    (Begrüße kingley3370 persönlich und nenne den Fokus der Analyse.)
    
    ### 📊 Allgemeine Einschätzung:
    - Wo steht der Kurs im Verhältnis zum Equilibrium ({stats['equilibrium']})?
    - Analysiere den Trend (Bullisch/Bärisch) und die aktuelle Dynamik.
    - Erwähne Volumen-Anomalien und Marktsentiment (Fear & Greed Logik).
    
    ### 🛡️ Technische Analyse & Smart Money Concepts:
    - Identifiziere Liquiditäts-Sweeps (Liquidity Grabs) unter {stats['low']} oder über {stats['high']}.
    - Beschreibe potenzielle FVG-Zonen (Fair Value Gaps) und Orderblocks im Detail.
    - Erkläre Market Structure Shifts (BOS oder CHoCH).
    
    ### 📍 Kritische Preislevel:
    - Liste mindestens 4 Widerstände (Resistances) und 3 Unterstützungen (Supports) mit exakten USDT-Werten auf.
    
    ### ⚡ Mögliche Trading-Setups:
    - Short-Setup: (Bedingung, Bestätigungssignal wie Pin-Bar/Engulfing, 🎯 Entry, 🛑 SL, 💰 TP).
    - Long-Setup: (Bedingung, Bestätigungssignal, 🎯 Entry, 🛑 SL, 💰 TP).
    
    ### 🎯 Meine Erwartung (Sentinel AI):
    - Gib deinen klaren Bias ab. Was ist dein Favorit-Szenario?
    - Beende mit: "Dies ist keine Anlageberatung, sondern eine rein edukative Analyse! Bitte bestimme dein Risiko selbst."

    SCHREIBSTIL: Professionell, analytisch, tiefgründig. Nutze VIELE Emojis und Markdown-Formatierung.
    """
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
        res_data = response.json()
        return res_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"❌ Gemini Fehler bei {coin}: {e}")
        return None

def send_to_discord():
    for coin in ["BTC", "SOL", "SUI"]:
        print(f"🔄 Verarbeite {coin}...")
        stats = get_live_data(coin)
        if stats:
            text = get_crypto_analysis(coin, stats)
            if text:
                requests.post(WEBHOOK, json={
                    "username": f"Sentinel Alpha | {coin}",
                    "avatar_url": "https://i.imgur.com/8N7j5fX.png",
                    "content": text[:2000] # Discord Limit beachten
                })
                print(f"🚀 {coin} gesendet!")
        time.sleep(10)

if __name__ == "__main__":
    send_to_discord()
