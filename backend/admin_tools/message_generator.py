
from __future__ import annotations
import json, requests

def call_groq_json(base_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, max_tokens: int = 300) -> dict:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0, "max_tokens": max_tokens},
        timeout=20,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    return json.loads(content)

def call_groq_text(base_url: str, api_key: str, model: str, prompt: str, max_tokens: int = 220) -> str:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
