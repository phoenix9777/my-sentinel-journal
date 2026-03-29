import requests
import json
import os
import time

# Holt die Daten sicher aus den GitHub Secrets
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_crypto_analysis(coin):
    model = "gemini-2.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        f"Du bist 'Sentinel Alpha 3.0', ein High-End Krypto-Analyst. Analysiere {coin}/USDT im 4H-Chart für kingley3370.\n\n"
        "Nutze exakt diese Struktur wie Finora AI:\n"
        "1. Begrüßung: 'Hallo kingley3370, hier ist dein Sentinel Check für {coin}!'\n"
        "2. Allgemeine Einschätzung: (Preis, Handelsspanne, Gleichgewichtsniveau, Trendbewertung (MACD/RSI Schwäche/Stärke)).\n"
        "3. Technische Analyse & Smart Money Concepts: (Liquidität-Sweeps, FVG-Zonen, Orderblocks, Market Structure Shift).\n"
        "4. Kritische Preislevel: (Präzise Widerstände und Unterstützungen).\n"
        "5. Mögliche Trading-Setups: (Detaillierte Long/Short Setups mit Bestätigungen wie Pin-Bar/Engulfing).\n"
        "6. Deine Erwartung: (Bias und Favorit-Szenario).\n\n"
        "Schreibe auf Deutsch, sei extrem ausführlich und nutze Markdown (Fett, Listen) für Discord."
    )
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Fehler bei der Analyse von {coin}: {str(e)}"

def send_to_discord():
    coins = ["BTC", "SOL", "SUI"]
    # Link zu einem coolen Logo (Kannst du gegen jedes Bild-URL tauschen)
    logo_url = "https://i.imgur.com/8N7j5fX.png" 

    for coin in coins:
        text = get_crypto_analysis(coin)
        payload = {
            "username": f"Sentinel Alpha | {coin}",
            "avatar_url": logo_url,
            "content": text[:2000]
        }
        requests.post(WEBHOOK, json=payload)
        print(f"{coin} Analyse gesendet.")
        time.sleep(10) # 10 Sekunden Pause zwischen den Coins, damit Discord nicht blockt

if __name__ == "__main__":
    send_to_discord()
