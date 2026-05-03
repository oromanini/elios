
import re, unicodedata
from .schemas import AdminIntent

def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", (text or "").lower())
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", normalized).strip()

def detect_admin_intent(text: str) -> AdminIntent:
    t = normalize_text(text)
    if re.search(r"confirmar envio\s+[a-f0-9\-]{8,}", t):
        return AdminIntent.CONFIRM_BROADCAST
    if any(k in t for k in ["todos os usuarios ativos", "todos os ativos", "todos os clientes ativos"]) and any(v in t for v in ["mande", "enviar", "envie", "avise", "disparar", "dispara"]):
        return AdminIntent.BROADCAST_TO_ACTIVE_USERS
    if any(k in t for k in ["quantos", "total"]) and any(k in t for k in ["usuarios", "clientes"]):
        return AdminIntent.GET_USERS_COUNT
    if "nps" in t and any(k in t for k in ["preencheram", "respondeu", "respond", "pendente", "nao preencheram"]):
        return AdminIntent.GET_NPS_CURRENT_CYCLE_STATUS
    if any(k in t for k in ["abaixo de", "menor que"]) and any(k in t for k in ["meta", "saude", "financas", "espiritualidade", "nota"]):
        return AdminIntent.LIST_USERS_WITH_GOAL_SCORE_BELOW
    if any(v in t for v in ["mande", "envie", "avise", "dispara", "disparar", "mandar", "enviar"]) and any(k in t for k in ["mensagem", "whatsapp", "zap", "usuario", "cliente"]):
        return AdminIntent.SEND_MESSAGE_TO_USER
    return AdminIntent.UNKNOWN
