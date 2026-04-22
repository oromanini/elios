import os
import re

import httpx

EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "https://api-whatsapp.hutooeducacao.com")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "elios-bot")


def _format_phone_for_whatsapp(phone: str) -> str:
    clean = re.sub(r"\D", "", phone or "")
    if len(clean) in (10, 11) and not clean.startswith("55"):
        clean = f"55{clean}"
    return clean


async def _send_whatsapp_text(clean_phone: str, text: str):
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": clean_phone,
        "text": text,
        "linkPreview": True,
    }
    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
