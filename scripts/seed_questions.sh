#!/usr/bin/env bash
set -euo pipefail

# Seed/repair the 12 onboarding questions used by /form.
# - Logs in as admin
# - Upserts by (title + pillar)
# - Ensures order/description/is_active are correct
#
# Required deps: curl, jq
#
# Usage:
#   BASE_URL="http://localhost:8001" \
#   ADMIN_EMAIL="admin@hutooeducacao.com" \
#   ADMIN_PASSWORD="Admin@123" \
#   ./scripts/seed_questions.sh

BASE_URL="${BASE_URL:-http://localhost:8001}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@hutooeducacao.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin@123}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "❌ Missing dependency: $1" >&2
    exit 1
  }
}

require_cmd curl
require_cmd jq

api() {
  local method="$1"
  local path="$2"
  local data="${3:-}"

  if [[ -n "$data" ]]; then
    curl -sS -X "$method" "$BASE_URL/api$path" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$data"
  else
    curl -sS -X "$method" "$BASE_URL/api$path" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json"
  fi
}

echo "🔐 Logging in as admin: $ADMIN_EMAIL"
LOGIN_PAYLOAD=$(jq -n --arg email "$ADMIN_EMAIL" --arg password "$ADMIN_PASSWORD" '{email: $email, password: $password}')
LOGIN_RESPONSE=$(curl -sS -X POST "$BASE_URL/api/auth/login" -H "Content-Type: application/json" -d "$LOGIN_PAYLOAD")
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token // empty')

if [[ -z "$TOKEN" ]]; then
  echo "❌ Failed to authenticate. Response:"
  echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "📥 Loading existing admin questions"
EXISTING=$(api GET "/admin/questions")

question_payload() {
  local pillar="$1"; local title="$2"; local description="$3"; local order="$4"
  jq -n \
    --arg pillar "$pillar" \
    --arg title "$title" \
    --arg description "$description" \
    --argjson order "$order" \
    --argjson is_active true \
    '{pillar: $pillar, title: $title, description: $description, order: $order, is_active: $is_active}'
}

upsert_question() {
  local pillar="$1"; local title="$2"; local description="$3"; local order="$4"
  local payload id

  payload=$(question_payload "$pillar" "$title" "$description" "$order")

  id=$(echo "$EXISTING" | jq -r --arg pillar "$pillar" --arg title "$title" '
      map(select(.pillar == $pillar and .title == $title))
      | sort_by(.order)
      | .[0].id // empty
    ')

  if [[ -n "$id" ]]; then
    api PUT "/admin/questions/$id" "$payload" >/dev/null
    echo "♻️  Updated: [$order] $title"
  else
    api POST "/admin/questions" "$payload" >/dev/null
    echo "✅ Created: [$order] $title"
  fi
}

upsert_question "ESPIRITUALIDADE" "Espiritualidade" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)" 1
upsert_question "CUIDADOS COM A SAÚDE" "Cuidados com a Saúde" "Como estou e como desejo estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)" 2
upsert_question "EQUILÍBRIO EMOCIONAL" "Equilíbrio Emocional" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 3
upsert_question "LAZER" "Lazer" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 4
upsert_question "GESTÃO DO TEMPO E ORGANIZAÇÃO" "Gestão do Tempo e Organização" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)" 5
upsert_question "DESENVOLVIMENTO INTELECTUAL" "Desenvolvimento Intelectual" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 6
upsert_question "IMAGEM PESSOAL" "Imagem Pessoal" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 7
upsert_question "FAMÍLIA" "Família" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 8
upsert_question "CRESCIMENTO PROFISSIONAL" "Crescimento Profissional" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 9
upsert_question "FINANÇAS" "Finanças" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 10
upsert_question "NETWORKING E CONTRIBUIÇÃO" "Networking e Contribuição" "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)." 11
upsert_question "META MAGNUS" "Meta Magnus" "A MAIOR E MAIS IMPORTANTE META PARA ATINGIR EM 12 MESES. (Seja específico e claro)." 12

echo "🔎 Verifying public form questions count"
PUBLIC_COUNT=$(curl -sS "$BASE_URL/api/questions" | jq 'length')
echo "🎯 Done. Active questions in /api/questions: $PUBLIC_COUNT"
