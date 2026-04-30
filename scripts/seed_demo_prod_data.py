#!/usr/bin/env python3
"""Popula dados demo de usuários, respostas, metas e NPS no MongoDB.

Uso:
  python scripts/seed_demo_prod_data.py

Requisitos:
- Variável de ambiente MONGO_ATLAS_URI configurada.
- Coleção questions previamente populada com os 12 pilares.

O script é idempotente por email de usuário e por chaves de registro (user_id + ciclo etc).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from pymongo import MongoClient

DEFAULT_PASSWORD = os.getenv("DEMO_USERS_PASSWORD", "Demo@12345")

USERS = [
    {"full_name": "Usuário Demo 1", "email": "demo.user1@elios.local"},
    {"full_name": "Usuário Demo 2", "email": "demo.user2@elios.local"},
    {"full_name": "Usuário Demo 3", "email": "demo.user3@elios.local"},
]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    mongo_uri = os.getenv("MONGO_ATLAS_URI")
    if not mongo_uri:
        raise RuntimeError("MONGO_ATLAS_URI não configurada.")

    client = MongoClient(mongo_uri)
    db = client["elios"]

    questions = list(db.questions.find({"is_active": True}, {"_id": 0, "id": 1, "pillar": 1}).sort("order", 1))
    if not questions:
        raise RuntimeError("Nenhuma pergunta ativa encontrada em questions.")

    base_day = datetime.now(timezone.utc).replace(day=15, hour=12, minute=0, second=0, microsecond=0)

    created_users = 0
    updated_users = 0
    total_responses = 0
    total_goals = 0
    total_nps = 0

    for idx, blueprint in enumerate(USERS, start=1):
        existing = db.users.find_one({"email": blueprint["email"]}, {"_id": 0, "id": 1})
        user_id = existing["id"] if existing else str(uuid.uuid4())

        created_at = (base_day - timedelta(days=120 + idx * 3)).isoformat()
        user_doc = {
            "id": user_id,
            "full_name": blueprint["full_name"],
            "email": blueprint["email"],
            "password_hash": hash_password(DEFAULT_PASSWORD),
            "role": "DEFAULT",
            "is_active": True,
            "form_completed": True,
            "elios_summary": "Usuário demo para validação visual do cliente.",
            "created_at": created_at,
        }
        result = db.users.update_one({"email": blueprint["email"]}, {"$set": user_doc}, upsert=True)
        if result.upserted_id:
            created_users += 1
        else:
            updated_users += 1

        for q_pos, question in enumerate(questions, start=1):
            rating = ((idx + q_pos) % 4) + 7
            answer = (
                f"[{blueprint['full_name']}] Situação atual do pilar {question['pillar']} e plano para 12 meses "
                f"com ação semanal #{q_pos}."
            )
            response_doc = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "question_id": question["id"],
                "answer": answer,
                "rating": rating,
                "created_at": now_iso(),
                "version": 1,
            }
            db.form_responses.update_one(
                {"user_id": user_id, "question_id": question["id"]},
                {"$set": response_doc},
                upsert=True,
            )
            total_responses += 1

        goal_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "pillar": "META MAGNUS",
            "title": f"Meta principal trimestral - {blueprint['full_name']}",
            "description": "Executar rotina semanal e elevar nota média dos pilares em 90 dias.",
            "target_date": (base_day + timedelta(days=90)).date().isoformat(),
            "status": "active",
            "is_deleted": False,
            "created_at": now_iso(),
        }
        db.goals.update_one(
            {"user_id": user_id, "pillar": "META MAGNUS", "title": goal_doc["title"]},
            {"$set": goal_doc},
            upsert=True,
        )
        total_goals += 1

        for cycle in range(1, 4):
            send_date = (base_day - timedelta(days=(4 - cycle) * 30)).replace(day=5)
            fill_date = send_date + timedelta(days=2)
            evaluations = [
                {
                    "goal_id": goal_doc["id"],
                    "goal_title": goal_doc["title"],
                    "goal_description": goal_doc["description"],
                    "goal_pillar": goal_doc["pillar"],
                    "is_completed": cycle >= 2,
                    "score": min(10, 6 + cycle + idx),
                }
            ]
            nps_doc = {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "cycle": cycle,
                "send_date": send_date,
                "fill_date": fill_date,
                "evaluations": evaluations,
                "status": "filled",
            }
            db.nps_records.update_one(
                {"user_id": user_id, "cycle": cycle},
                {"$set": nps_doc},
                upsert=True,
            )
            total_nps += 1

    print("✅ Seed concluído")
    print(f"Usuários criados: {created_users} | atualizados: {updated_users}")
    print(f"Respostas tratadas: {total_responses}")
    print(f"Metas tratadas: {total_goals}")
    print(f"Registros NPS tratados: {total_nps}")
    print(f"Senha padrão dos usuários demo: {DEFAULT_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
