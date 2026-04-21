import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

import httpx

EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
EVOLUTION_API_URL = "https://api-whatsapp.hutooeducacao.com"
EVOLUTION_INSTANCE = "elios-bot"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

logger = logging.getLogger(__name__)


def _is_valid_phone(phone: str) -> bool:
    normalized_phone = re.sub(r"\D", "", phone or "")
    return len(normalized_phone) >= 10


async def send_whatsapp_nps_link(phone: str, nps_id: str):
    if not EVOLUTION_API_KEY:
        logger.warning("Envio de WhatsApp desativado: EVOLUTION_API_KEY não configurada.")
        return

    if not _is_valid_phone(phone):
        logger.warning("Envio de WhatsApp abortado: telefone inválido (%s).", phone)
        return

    link = f"{FRONTEND_URL}/nps/{nps_id}"
    payload = {
        "number": phone,
        "text": "Olá! Está na hora do seu Check-in de Performance Mensal do ELIOS. "
        "Clique no link para avaliar as suas metas: " + link,
        "linkPreview": True,
    }
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }

    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Falha ao enviar WhatsApp para %s: %s", phone, exc)


async def process_nps_cycles(db):
    now = datetime.now(timezone.utc)
    users = await db.users.find({"is_active": True}).to_list(length=None)

    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue

        last_record = await db.nps_records.find_one({"user_id": user_id}, sort=[("send_date", -1)])

        next_cycle = 1
        should_generate = False

        if not last_record:
            should_generate = True
        else:
            last_send_date = last_record.get("send_date")
            last_cycle = int(last_record.get("cycle", 0))
            if (
                isinstance(last_send_date, datetime)
                and now - last_send_date >= timedelta(days=30)
                and last_cycle < 12
            ):
                should_generate = True
                next_cycle = last_cycle + 1

        if not should_generate:
            continue

        goals: List[Dict[str, Any]] = await db.goals.find({"user_id": user_id}).to_list(length=None)
        evaluations = []
        for goal in goals:
            if goal.get("is_completed", False):
                continue
            evaluations.append(
                {
                    "goal_id": goal.get("id", ""),
                    "goal_title": goal.get("title", "Meta sem título"),
                    "is_completed": False,
                    "score": None,
                }
            )

        nps_record = {
            "user_id": user_id,
            "cycle": next_cycle,
            "send_date": datetime.now(timezone.utc),
            "fill_date": None,
            "evaluations": evaluations,
            "status": "pending",
        }
        insert_result = await db.nps_records.insert_one(nps_record)
        novo_nps_id = insert_result.inserted_id

        phone = user.get("phone") or user.get("whatsapp")
        if phone:
            await send_whatsapp_nps_link(phone, str(novo_nps_id))
