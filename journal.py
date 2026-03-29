import requests
import json

# Deine Daten
WEBHOOK = "https://discord.com/api/webhooks/1487819789731758170/vffd2_Ox6XrW9YP-S4-PBsHA76MxXGua9Kw4cVZRGkhiw_4wCLQNXiB9kiUJayqxU9N6"
GEMINI_KEY = "AIzaSyD3787AesVRWKyhnPFFZR773FMiFu2vuxM"

def get_analysis():
    # Upgrade auf Gemini 3.0 Flash Preview
    model = "gemini-3.0-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        "Du bist das 'Sentinel Alpha 3.0 Journal'. Erstelle eine hochpräzise Marktanalyse "
        "für BTC, SOL und SUI auf Deutsch. Fokus: 4-Stunden-Chart (4H).\n\n"
        "Struktur:\n"
        "1. Professionelle Headline mit Emojis\n"
        "2. Kurze, knackige Analyse zu BTC, SOL und SUI (getrennte Sektionen)\n"
        "3. Sentiment-Check (Bullish/Bearish) pro Coin.\n"
        "Verwende Fettdruck und Listen für beste Lesbarkeit in Discord."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    data = response.json()

    # Sicherheits-Check
    if 'candidates' not in data:
        error_text = f"⚠️ Gemini API Fehler ({model}): {json.dumps(data.get('error', data))}"
        print(error_text)
        return error_text
        
    return data['candidates'][0]['content']['parts'][0]['text']

def send_to_discord():
    analysis_text = get_analysis()
    
    payload = {
        "username": "Sentinel Alpha | 3.0 Flash",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/en/b/b9/Solana_logo.png",
        "content": analysis_text
    }
    
    requests.post(WEBHOOK, json=payload)

if __name__ == "__main__":
    send_to_discord()
