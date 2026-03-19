import os
import requests

def responder(mensaje):
    API_KEY = os.getenv("OPENAI_API_KEY")

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Eres asistente de clínica dental"},
            {"role": "user", "content": mensaje}
        ]
    }

    res = requests.post(url, headers=headers, json=data)
    return res.json()["choices"][0]["message"]["content"]