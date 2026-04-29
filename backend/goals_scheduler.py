import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from whatsapp_utils import format_phone_for_whatsapp, send_whatsapp_text

logger = logging.getLogger(__name__)

WEEKLY_PROGRESS_LINK = "https://dashboard.elios.com.br/dashboard/weekly-progress"
WEEKLY_PROGRESS_MESSAGE = (
    "Olá governante! 🚀 Seu resumo semanal de progresso está pronto. Clique no link abaixo para visualizar sua evolução e as metas que precisamos ajustar:\n"
    "https://dashboard.elios.com.br/dashboard/weekly-progress\n"
    "Lembre-se: o objetivo é a Meta MAGNUS! Estou aqui para ajudar."
)


def _normalize_user_role(user: Dict[str, Any]) -> str:
    return str(user.get("role") or "").upper().strip()


def calculate_goal_average(scores: List[float]) -> Optional[float]:
    valid_scores = [float(score) for score in scores if isinstance(score, (int, float))]
    if not valid_scores:
        return None
    return round(sum(valid_scores) / len(valid_scores), 2)


def build_goal_snapshot(goals: List[Dict[str, Any]], nps_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    scores_by_goal: Dict[str, List[float]] = {}
    for record in nps_records:
        for evaluation in record.get("evaluations", []):
            goal_id = evaluation.get("goal_id")
            score = evaluation.get("score")
            if not goal_id or not isinstance(score, (int, float)):
                continue
            scores_by_goal.setdefault(goal_id, []).append(float(score))

    meta_naves: List[Dict[str, Any]] = []
    medias_calculadas: Dict[str, Optional[float]] = {}
    for goal in goals:
        goal_id = goal.get("id")
        if not goal_id:
            continue
        recent_scores = scores_by_goal.get(goal_id, [])[-3:]
        average = calculate_goal_average(recent_scores)
        medias_calculadas[goal_id] = average
        meta_naves.append(
            {
                "goal_id": goal_id,
                "goal_title": goal.get("title", "Meta sem título"),
                "pillar": goal.get("pillar", ""),
                "scores": recent_scores,
                "average": average,
            }
        )

    return {
        "meta_naves": meta_naves,
        "medias_calculadas": medias_calculadas,
    }


async def _insert_goal_log(
    db: Any,
    user_id: str,
    status: str,
    link_sent: bool,
    snapshot_data: Dict[str, Any],
):
    await db.goal_reminders_log.insert_one(
        {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "status": status,
            "link_sent": link_sent,
            "snapshot_data": snapshot_data,
        }
    )


async def process_weekly_goal_reminders(db: Any):
    now = datetime.now(timezone.utc)
    users = await db.users.find({"is_active": True}).to_list(length=None)

    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue

        role = _normalize_user_role(user)
        if role == "ADMIN":
            continue
        if role not in {"USER", "DEFAULT"}:
            continue

        goals = await db.goals.find({"user_id": user_id, "is_deleted": {"$ne": True}}).to_list(length=None)
        if not goals:
            continue

        nps_records = await db.nps_records.find(
            {"user_id": user_id, "status": "completed"}
        ).sort("send_date", -1).to_list(length=3)

        snapshot = build_goal_snapshot(goals, nps_records)
        available_averages = [
            item.get("average") for item in snapshot["meta_naves"] if isinstance(item.get("average"), (int, float))
        ]

        if not available_averages:
            logger.info("Usuário %s sem dados NPS nos últimos 3 ciclos. Ignorando.", user_id)
            continue

        must_send = any(avg < 7.0 for avg in available_averages)
        send_status = "success"
        link_sent = False

        if must_send:
            duplicate_logs = await db.goal_reminders_log.find(
                {
                    "user_id": user_id,
                    "link_sent": True,
                }
            ).to_list(length=10)
            has_recent_duplicate = any(
                isinstance(log.get("timestamp"), datetime)
                and ((log.get("timestamp").replace(tzinfo=timezone.utc) if log.get("timestamp").tzinfo is None else log.get("timestamp")) >= now - timedelta(minutes=5))
                for log in duplicate_logs
            )
            if has_recent_duplicate:
                logger.info("Lembrete semanal já enviado recentemente para %s. Ignorando duplicidade.", user_id)
                continue

            phone = user.get("whatsapp") or user.get("phone")
            clean_phone = format_phone_for_whatsapp(phone or "")
            if len(clean_phone) < 12:
                send_status = "failed"
                logger.warning("Falha no envio semanal para %s: telefone inválido.", user_id)
            else:
                try:
                    await send_whatsapp_text(clean_phone, WEEKLY_PROGRESS_MESSAGE)
                    link_sent = True
                except Exception:
                    send_status = "failed"
                    logger.error("Erro ao enviar lembrete semanal para user_id=%s", user_id, exc_info=True)

        await _insert_goal_log(
            db=db,
            user_id=user_id,
            status=send_status,
            link_sent=link_sent,
            snapshot_data=snapshot,
        )
