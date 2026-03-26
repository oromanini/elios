#!/usr/bin/env python3
"""Seed/repair onboarding questions via ELIOS API.

Usage:
  python scripts/seed_questions.py \
    --base-url http://localhost:8001 \
    --admin-email admin@hutooeducacao.com \
    --admin-password Admin@123

Environment fallbacks:
  BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

QUESTIONS = [
    {
        "pillar": "ESPIRITUALIDADE",
        "title": "Espiritualidade",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)",
        "order": 1,
    },
    {
        "pillar": "CUIDADOS COM A SAÚDE",
        "title": "Cuidados com a Saúde",
        "description": "Como estou e como desejo estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)",
        "order": 2,
    },
    {
        "pillar": "EQUILÍBRIO EMOCIONAL",
        "title": "Equilíbrio Emocional",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 3,
    },
    {
        "pillar": "LAZER",
        "title": "Lazer",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 4,
    },
    {
        "pillar": "GESTÃO DO TEMPO E ORGANIZAÇÃO",
        "title": "Gestão do Tempo e Organização",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)",
        "order": 5,
    },
    {
        "pillar": "DESENVOLVIMENTO INTELECTUAL",
        "title": "Desenvolvimento Intelectual",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 6,
    },
    {
        "pillar": "IMAGEM PESSOAL",
        "title": "Imagem Pessoal",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 7,
    },
    {
        "pillar": "FAMÍLIA",
        "title": "Família",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 8,
    },
    {
        "pillar": "CRESCIMENTO PROFISSIONAL",
        "title": "Crescimento Profissional",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 9,
    },
    {
        "pillar": "FINANÇAS",
        "title": "Finanças",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 10,
    },
    {
        "pillar": "NETWORKING E CONTRIBUIÇÃO",
        "title": "Networking e Contribuição",
        "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta).",
        "order": 11,
    },
    {
        "pillar": "META MAGNUS",
        "title": "Meta Magnus",
        "description": "A MAIOR E MAIS IMPORTANTE META PARA ATINGIR EM 12 MESES. (Seja específico e claro).",
        "order": 12,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed/repair ELIOS onboarding questions")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://localhost:8001"), help="API base URL, e.g. http://localhost:8001")
    parser.add_argument("--admin-email", default=os.getenv("ADMIN_EMAIL", "admin@hutooeducacao.com"), help="Admin login email")
    parser.add_argument("--admin-password", default=os.getenv("ADMIN_PASSWORD", "Admin@123"), help="Admin login password")
    return parser.parse_args()


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload) if payload else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} on {method} {url}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection error on {method} {url}: {exc}") from exc


def login(base_url: str, email: str, password: str) -> str:
    print(f"🔐 Login admin: {email}")
    payload = {"email": email, "password": password}
    response = request_json("POST", f"{base_url}/api/auth/login", payload)
    token = response.get("token") if isinstance(response, dict) else None
    if not token:
        raise RuntimeError(f"Token ausente no login: {response}")
    return token


def upsert_questions(base_url: str, token: str) -> None:
    print("📥 Carregando perguntas existentes (admin)")
    existing = request_json("GET", f"{base_url}/api/admin/questions", token=token)
    if not isinstance(existing, list):
        raise RuntimeError(f"Resposta inesperada em /admin/questions: {existing}")

    existing_map: dict[tuple[str, str], dict[str, Any]] = {}
    for item in existing:
        if not isinstance(item, dict):
            continue
        key = (item.get("pillar", ""), item.get("title", ""))
        if key not in existing_map:
            existing_map[key] = item

    created = 0
    updated = 0

    for question in QUESTIONS:
        key = (question["pillar"], question["title"])
        payload = {
            "pillar": question["pillar"],
            "title": question["title"],
            "description": question["description"],
            "order": question["order"],
            "is_active": True,
        }

        current = existing_map.get(key)
        if current and current.get("id"):
            qid = current["id"]
            request_json("PUT", f"{base_url}/api/admin/questions/{qid}", payload, token=token)
            updated += 1
            print(f"♻️  Updated [{question['order']:02d}] {question['title']}")
        else:
            request_json("POST", f"{base_url}/api/admin/questions", payload, token=token)
            created += 1
            print(f"✅ Created [{question['order']:02d}] {question['title']}")

    public_questions = request_json("GET", f"{base_url}/api/questions")
    public_count = len(public_questions) if isinstance(public_questions, list) else "?"
    print(f"🎯 Done. created={created}, updated={updated}, active_public={public_count}")


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    email = args.admin_email
    password = args.admin_password
    try:
        token = login(base_url, email, password)
        upsert_questions(base_url, token)
        return 0
    except RuntimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
