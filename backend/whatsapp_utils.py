import os
import re
from typing import Any, Dict, List, Set

import httpx

EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "https://api-whatsapp.hutooeducacao.com")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "elios-bot")


def format_phone_for_whatsapp(phone: str) -> str:
    clean = re.sub(r"\D", "", phone or "")
    if len(clean) in (10, 11) and not clean.startswith("55"):
        clean = f"55{clean}"
    return clean


async def send_whatsapp_text(recipient: str, text: str):
    clean_phone = re.sub(r"\D", "", str(recipient))

    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": clean_phone,
        "text": text,
        "delay": 0,
        "linkPreview": False,
    }
    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()


def normalize_whatsapp_jid(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if not digits:
        return ""
    return f"{digits}@s.whatsapp.net"


async def get_group_participants(group_jid: str) -> Set[str]:
    headers = {"apikey": EVOLUTION_API_KEY}
    endpoint = f"{EVOLUTION_API_URL}/group/participants/{EVOLUTION_INSTANCE}"
    params = {"groupJid": group_jid}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

    body = response.json() if response.content else {}
    participants: List[Dict[str, Any]] = body.get("participants") or []
    normalized: Set[str] = set()
    for participant in participants:
        participant_id = participant.get("id")
        if isinstance(participant_id, str):
            jid = normalize_whatsapp_jid(participant_id)
            if jid:
                normalized.add(jid)
    return normalized


async def add_group_participant(group_jid: str, participant_phone: str):
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "groupJid": group_jid,
        "action": "add",
        "participants": [re.sub(r"\D", "", str(participant_phone or ""))],
    }
    endpoint = f"{EVOLUTION_API_URL}/group/updateParticipant/{EVOLUTION_INSTANCE}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()


async def send_whatsapp_media(recipient: str, media: str, caption: str, filename: str = "profile.jpg"):
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": recipient,
        "mediatype": "image",
        "mimetype": "image/jpeg",
        "caption": caption,
        "media": media,
        "fileName": filename,
        "delay": 0,
        "linkPreview": False,
    }
    endpoint = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
