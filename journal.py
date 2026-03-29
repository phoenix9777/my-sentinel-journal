import requests
import os

# Deine Daten (Sicher verstaut)
WEBHOOK = "https://discord.com/api/webhooks/1487819789731758170/vffd2_Ox6XrW9YP-S4-PBsHA76MxXGua9Kw4cVZRGkhiw_4wCLQNXiB9kiUJayqxU9N6"
GEMINI_KEY = "AIzaSyD3787AesVRWKyhnPFFZR773FMiFu2vuxM"

def get_analysis():
    # Hier fragt das Script kurz bei Google Gemini nach
    prompt = "Analysiere SOL, BTC und SUI auf Deutsch für ein 4H-Journal. Kurz und knackig mit Emojis."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
    return response.json()['candidates'][0]['content']['parts'][0]['text']

def send_to_discord():
    text = get_analysis()
    requests.post(WEBHOOK, json={"username": "Sentinel Alpha", "content": text})

if __name__ == "__main__":
    send_to_discord()
