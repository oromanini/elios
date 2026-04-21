import asyncio
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


def _format_phone_for_whatsapp(phone: str) -> str:
    clean = re.sub(r"\D", "", phone or "")
    if len(clean) in (10, 11) and not clean.startswith("55"):
        clean = f"55{clean}"
    return clean


async def send_whatsapp_nps_link(phone: str, nps_id: str):
    if not EVOLUTION_API_KEY:
        logger.warning("Envio de WhatsApp desativado: EVOLUTION_API_KEY não configurada.")
        return

    clean_phone = _format_phone_for_whatsapp(phone)
    if len(clean_phone) < 12:
        logger.warning("Envio de WhatsApp abortado: telefone inválido (%s).", phone)
        return

    base_url = FRONTEND_URL
    link = f"{base_url}/nps/{nps_id}"
    first_payload = {
        "number": clean_phone,
        "text": "Olá! Está na hora do seu Check-in de Performance Mensal do ELIOS. "
        "Clique no link para avaliar as suas metas:",
        "linkPreview": True,
    }
    second_payload = {
        "number": clean_phone,
        "text": link,
        "linkPreview": True,
    }
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }

    endpoint = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            logger.info("Tentando enviar primeira mensagem de NPS para %s.", clean_phone)
            first_response = await client.post(endpoint, json=first_payload, headers=headers)
            first_response.raise_for_status()
            logger.info("Primeira mensagem de NPS enviada para %s.", clean_phone)

            await asyncio.sleep(1)

            logger.info("Tentando enviar link de NPS para %s.", clean_phone)
            second_response = await client.post(endpoint, json=second_payload, headers=headers)
            second_response.raise_for_status()
            logger.info("Link de NPS enviado para %s.", clean_phone)
    except Exception as exc:
        logger.warning("Falha ao enviar WhatsApp para %s: %s", phone, exc)


async def process_nps_cycles(db, target_user_id: str = None):
    now = datetime.now(timezone.utc)
    query = {"is_active": True, "role": "DEFAULT"}
    if target_user_id is not None:
        query["id"] = target_user_id
    users = await db.users.find(query).to_list(length=None)

    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue

        try:
            last_record = await db.nps_records.find_one({"user_id": user_id}, sort=[("send_date", -1)])

            next_cycle = 1
            should_generate = False

            if not last_record:
                should_generate = True
                next_cycle = 1
            else:
                if last_record.get("status") == "pending":
                    logger.info(
                        "Usuário %s possui ciclo %s pendente. Pulando geração.",
                        user_id,
                        last_record.get("cycle"),
                    )
                    continue

                last_send_date = last_record.get("send_date")
                if last_send_date and last_send_date.tzinfo is None:
                    last_send_date = last_send_date.replace(tzinfo=timezone.utc)
                last_cycle = int(last_record.get("cycle", 0))
                if (
                    last_record.get("status") == "completed"
                    and
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
                        "goal_description": goal.get("description", ""),
                        "goal_pillar": goal.get("pillar", ""),
                        "is_completed": False,
                        "score": None,
                    }
                )

            if len(evaluations) == 0:
                continue

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
            logger.info("Novo registro NPS criado para usuário %s: %s", user_id, novo_nps_id)

            phone = user.get("phone") or user.get("whatsapp")
            if phone:
                await send_whatsapp_nps_link(phone, str(novo_nps_id))
        except Exception:
            logger.error("Falha ao processar ciclo NPS para user_id=%s", user_id, exc_info=True)
