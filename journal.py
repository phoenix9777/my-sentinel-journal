import requests
import json
import os

# Holt die Daten aus den GitHub Secrets
WEBHOOK = os.getenv("DISCORD_WEBHOOK")
GEMINI_KEY = os.getenv("GEMINI_KEY")

def get_analysis():
    # Wir nutzen 1.5-flash – das ist 2026 am stabilsten im Free-Tier
    model = "gemini-1.5-flash" 
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        "Analysiere BTC, SOL und SUI auf dem 4H-Chart. "
        "Schreibe auf Deutsch, nutze Emojis und Headlines. Sei präzise."
    )
    
    try:
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        data = response.json()
        
        # Falls Gemini eine Fehlermeldung schickt, poste sie in Discord
        if "error" in data:
            return f"❌ Gemini-Fehler: {data['error']['message']}"
            
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"❌ Script-Fehler: {str(e)}"

def send_to_discord():
    text = get_analysis()
    # Sicherstellen, dass der Text nicht zu lang für Discord ist
    payload = {"username": "Sentinel Alpha 3.0", "content": text[:2000]}
    requests.post(WEBHOOK, json=payload)

if __name__ == "__main__":
    send_to_discord()
