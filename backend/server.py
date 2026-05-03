from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, UploadFile, File, Form, Request, Response, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from io import BytesIO
import base64
import json
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator, model_validator
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime, timezone, timedelta, date
import jwt
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import asyncio
import requests
import re
import sqlite3
import hashlib
import unicodedata
import httpx
from PIL import Image, UnidentifiedImageError
from bson import ObjectId
from bson.errors import InvalidId
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from nps_scheduler import process_nps_cycles, process_nps_reminders
from goals_scheduler import process_weekly_goal_reminders
from whatsapp_utils import (
    EVOLUTION_API_KEY,
    EVOLUTION_API_URL as DEFAULT_EVOLUTION_API_URL,
    EVOLUTION_INSTANCE as DEFAULT_EVOLUTION_INSTANCE,
    add_group_participant,
    format_phone_for_whatsapp,
    get_group_participants,
    normalize_whatsapp_jid,
    send_whatsapp_media,
    send_whatsapp_text,
    send_whatsapp_message as send_whatsapp_message_via_evolution,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
WHATSAPP_BOT_NUMBER = os.environ.get("WHATSAPP_BOT_NUMBER", os.environ.get("BOT_NUMBER", ""))
ELIOS_WHATSAPP_GROUP_JID = os.environ.get("ELIOS_WHATSAPP_GROUP_JID", "")
ENV = os.environ.get('ENV', 'development').lower()

# MongoDB connection
mongo_url = os.environ['MONGO_ATLAS_URI']
client = AsyncIOMotorClient(mongo_url)
db = client['elios']

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-key')
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = int(os.environ.get("JWT_EXP_HOURS", "12"))
JWT_COOKIE_NAME = os.environ.get("JWT_COOKIE_NAME", "elios_token")
JWT_COOKIE_MAX_AGE = JWT_EXP_HOURS * 3600
JWT_COOKIE_DOMAIN = os.environ.get("JWT_COOKIE_DOMAIN") or None
JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "lax").lower()
JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "true").lower() == "true"
ALLOWED_SAMESITE_VALUES = {"lax", "strict", "none"}

if ENV == "production":
    # Em produção (Cloud Run + frontend em domínio diferente/subdomínio), o cookie
    # precisa ser explícito para sobreviver às políticas modernas do navegador.
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "none"
    # Domain deve ser opcional: quando ausente, o navegador cria cookie host-only
    # para o domínio exato da API, evitando descartes por domínio incompatível.
    JWT_COOKIE_DOMAIN = JWT_COOKIE_DOMAIN or os.environ.get("JWT_COOKIE_BASE_DOMAIN") or None

if JWT_COOKIE_SAMESITE not in ALLOWED_SAMESITE_VALUES:
    raise RuntimeError("JWT_COOKIE_SAMESITE inválido. Use: lax, strict ou none.")
if JWT_COOKIE_SAMESITE == "none" and not JWT_COOKIE_SECURE:
    raise RuntimeError("JWT_COOKIE_SECURE deve ser true quando JWT_COOKIE_SAMESITE=none.")


def normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


FRONTEND_URL = normalize_origin(os.getenv("FRONTEND_URL", "http://localhost:3000"))

raw_cors = os.getenv("CORS_ORIGINS", FRONTEND_URL)
CORS_ORIGINS = [normalize_origin(origin) for origin in raw_cors.split(",") if origin.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = [FRONTEND_URL]
if FRONTEND_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_URL)
if '*' in CORS_ORIGINS:
    raise RuntimeError('CORS_ORIGINS não pode conter "*" quando cookies com credenciais estão habilitados.')
if ENV == "production":
    invalid_origins = [origin for origin in CORS_ORIGINS if not origin.startswith("https://")]
    if invalid_origins:
        CORS_ORIGINS = [origin for origin in CORS_ORIGINS if origin.startswith("https://")]
        logging.warning(
            "Ignorando CORS_ORIGINS inválidas em produção (somente https é permitido): %s",
            ", ".join(invalid_origins),
        )
        if not CORS_ORIGINS:
            raise RuntimeError(
                "Nenhuma origem CORS https válida encontrada em produção. "
                "Defina CORS_ORIGINS com URLs https exatas do frontend."
            )

# AI Configuration (Groq only)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_BASE_URL = os.environ.get('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')
GROQ_FORM_MODEL = os.environ.get('GROQ_FORM_MODEL', '')

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
FRONTEND_RESET_PASSWORD_URL = os.environ.get("FRONTEND_RESET_PASSWORD_URL", "")
RESET_PASSWORD_TTL_MINUTES = int(os.environ.get("RESET_PASSWORD_TTL_MINUTES", "30"))

# Upload Configuration
UPLOAD_DIR_LOCAL = Path(os.environ.get('UPLOAD_DIR_LOCAL', ROOT_DIR / 'uploads/profile_photos'))
R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY', '')
R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY', '')
R2_ENDPOINT = os.environ.get('R2_ENDPOINT', '')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', '')
R2_PUBLIC_BASE_URL = os.environ.get('R2_PUBLIC_BASE_URL', '')

if ENV == "production" and JWT_SECRET == "default-secret-key":
    raise RuntimeError("JWT_SECRET inválido em produção. Configure um segredo forte via variável de ambiente.")

# Security
LOGIN_ATTEMPTS: Dict[str, List[datetime]] = {}
MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_WINDOW_MINUTES = int(os.environ.get("LOGIN_WINDOW_MINUTES", "15"))
INIT_SETUP_TOKEN = os.environ.get("INIT_SETUP_TOKEN", "")

# Create the main app without a prefix
app = FastAPI(title="ELIOS - Sistema de Performance Elite")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")
nps_router = APIRouter(prefix="/api/nps")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")

# Default ELIOS System Prompt
DEFAULT_ELIOS_PROMPT = """Você é o ELIOS, uma Inteligência Artificial avançada atuando como Coach de Alta Performance Individual. 
Sua missão é ajudar o usuário a alcançar a excelência equilibrando os 11 Pilares da Vida.

OS 11 PILARES:
1. ESPIRITUALIDADE - Fé, propósito de vida, visão de mundo
2. CUIDADOS COM A SAÚDE - Exercícios, alimentação, saúde física
3. EQUILÍBRIO EMOCIONAL - Saúde mental, gestão de emoções
4. LAZER - Tempo de qualidade para descanso e diversão
5. GESTÃO DO TEMPO E ORGANIZAÇÃO - Rotina, produtividade
6. DESENVOLVIMENTO INTELECTUAL - Estudos, leitura, aprendizado
7. IMAGEM PESSOAL - Vestimenta, postura, linguajar
8. FAMÍLIA - Relacionamento com cônjuge e filhos
9. CRESCIMENTO PROFISSIONAL - Carreira e desenvolvimento
10. FINANÇAS - Gestão financeira, investimentos
11. NETWORKING E CONTRIBUIÇÃO - Conexões e contribuição social
+ META MAGNUS - A maior e mais importante meta para os próximos 12 meses

DIRETRIZES DE COMPORTAMENTO:
1. Tom de Voz: Você é implacável com os resultados, mas profundamente empático com o processo humano. Seja direto, prático, encorajador e sem rodeios. Evite clichês motivacionais genéricos.
2. Foco nos Dados: Suas respostas DEVEM ser ancoradas nas metas ativas do usuário. Nunca dê conselhos isolados se você puder conectá-los a uma meta que ele já possui.
3. Visão Sistêmica: Entenda que os 11 pilares estão conectados. Se o usuário relatar estresse financeiro, avalie como isso pode estar impactando o pilar de saúde ou relacionamentos, e vice-versa.
4. Estrutura de Resposta: 
   - Valide o sentimento ou o obstáculo do usuário rapidamente.
   - Analise a situação com base nas metas atuais dele.
   - Entregue um plano de ação tático de 1 a 3 passos curtos para ele aplicar HOJE.
5. Personalização: Use o nome do usuário quando apropriado. Referencie metas específicas dele.
6. Linguagem: Fale em português brasileiro, de forma clara e profissional.
7. Responde de forma extremamente concisa e direta ao ponto.
8. Proibido usar mais de 2 parágrafos ou 150 palavras por resposta.
9. Usa bullet points para planos de ação."""

# ==================== MODELS ====================

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: Optional[str] = None
    role: str = "DEFAULT"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: str
    form_completed: bool = False
    elios_summary: Optional[str] = None
    profile_photo_url: Optional[str] = None
    whatsapp: Optional[str] = None
    whatsapp_in_elios_group: Optional[bool] = None

class AddUserToWhatsappGroupPayload(BaseModel):
    biography: str = Field(min_length=5, max_length=600)

class MetadataEntry(BaseModel):
    id: str
    type: str
    name: str
    value: str

class MetadataUpdateItem(BaseModel):
    type: str
    name: str
    value: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

class AdminUserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "ADMIN"
    is_active: bool = True

class AdminUserFormResponses(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    full_name: str
    email: str
    created_at: str
    form_completed: bool = False
    responses_by_pillar: Dict[str, str]
    goals_by_pillar: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)

class QuestionCreate(BaseModel):
    pillar: str
    title: str
    description: str
    order: int

class QuestionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    pillar: str
    title: str
    description: str
    order: int
    is_active: bool = True

class QuestionUpdate(BaseModel):
    pillar: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None

class FormResponseCreate(BaseModel):
    question_id: str
    answer: str
    rating: Optional[int] = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def validate_rating_requirement(self) -> "FormResponseCreate":
        if self.question_id != META_MAGNUS_QUESTION_ID and self.rating is None:
            raise ValueError("rating é obrigatório para todos os pilares, exceto Meta Magnus")
        return self

META_MAGNUS_QUESTION_ID = "ca7e651a-a3a7-41f0-b38f-81f5bcc0b699"

class PillarEnum(str, Enum):
    ESPIRITUALIDADE = "ESPIRITUALIDADE"
    CUIDADOS_COM_A_SAUDE = "CUIDADOS COM A SAÚDE"
    EQUILIBRIO_EMOCIONAL = "EQUILÍBRIO EMOCIONAL"
    LAZER = "LAZER"
    GESTAO_DO_TEMPO_E_ORGANIZACAO = "GESTÃO DO TEMPO E ORGANIZAÇÃO"
    DESENVOLVIMENTO_INTELECTUAL = "DESENVOLVIMENTO INTELECTUAL"
    IMAGEM_PESSOAL = "IMAGEM PESSOAL"
    FAMILIA = "FAMÍLIA"
    CRESCIMENTO_PROFISSIONAL = "CRESCIMENTO PROFISSIONAL"
    FINANCAS = "FINANÇAS"
    NETWORKING_E_CONTRIBUICAO = "NETWORKING E CONTRIBUIÇÃO"
    META_MAGNUS = "META MAGNUS"


def _normalize_goal_title(title: str, max_words: int = 10) -> str:
    cleaned = re.sub(r"\s+", " ", (title or "").strip())
    if not cleaned:
        return ""
    words = cleaned.split(" ")
    return " ".join(words[:max_words])

class FormDetectedGoal(BaseModel):
    question_id: str
    pillar: PillarEnum | str
    title: str
    description: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = re.sub(r"\s+", " ", (value or "").strip())[:60]
        if not normalized:
            raise ValueError("title vazio")
        return normalized

class FormSubmission(BaseModel):
    full_name: str
    email: EmailStr
    whatsapp: str
    date_of_birth: Optional[str] = None
    profile_photo: Optional[UploadFile] = None
    responses: List[FormResponseCreate]
    detected_goals: List[FormDetectedGoal] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_detected_goals_mapping(self) -> "FormSubmission":
        response_by_question = {resp.question_id: (resp.answer or "").strip() for resp in self.responses if resp.question_id}
        normalized_goals_by_question: Dict[str, FormDetectedGoal] = {}

        for goal in self.detected_goals:
            if not goal.question_id:
                continue
            response_text = response_by_question.get(goal.question_id, "")
            normalized_title = _normalize_goal_title(goal.title, max_words=10)[:60] or _normalize_goal_title(response_text, max_words=10)[:60] or "Meta"
            normalized_goals_by_question[goal.question_id] = FormDetectedGoal(
                question_id=goal.question_id,
                pillar=PillarEnum.META_MAGNUS.value if goal.question_id == META_MAGNUS_QUESTION_ID else goal.pillar,
                title=normalized_title,
                description=goal.description or (response_text or None),
            )

        if META_MAGNUS_QUESTION_ID in response_by_question:
            response_text = response_by_question[META_MAGNUS_QUESTION_ID]
            normalized_goals_by_question[META_MAGNUS_QUESTION_ID] = FormDetectedGoal(
                question_id=META_MAGNUS_QUESTION_ID,
                pillar=PillarEnum.META_MAGNUS.value,
                title=_normalize_goal_title(response_text, max_words=10)[:60] or "Meta Magnus",
                description=response_text or None,
            )

        self.detected_goals = list(normalized_goals_by_question.values())
        return self

    @classmethod
    def as_form(
        cls,
        full_name: str = Form(...),
        email: EmailStr = Form(...),
        whatsapp: str = Form(...),
        date_of_birth: Optional[str] = Form(None),
        responses: str = Form(...),
        detected_goals: Optional[str] = Form(None),
        profile_photo: Optional[UploadFile] = File(None)
    ) -> "FormSubmission":
        try:
            parsed_responses = json.loads(responses)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=422, detail="Campo 'responses' inválido. Envie um JSON válido.") from exc

        try:
            response_items = [FormResponseCreate.model_validate(item) for item in parsed_responses]
        except Exception as exc:
            raise HTTPException(status_code=422, detail="Formato de respostas inválido.") from exc

        parsed_detected_goals: List[FormDetectedGoal] = []
        if detected_goals:
            try:
                goals_payload = json.loads(detected_goals)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail="Campo 'detected_goals' inválido. Envie um JSON válido.") from exc

            try:
                parsed_detected_goals = [FormDetectedGoal.model_validate(item) for item in goals_payload]
            except Exception as exc:
                logger.error("Erro de validação em detected_goals no parse. payload=%s error=%s", {"responses": parsed_responses, "detected_goals": goals_payload}, str(exc))
                raise HTTPException(status_code=422, detail="Formato de metas detectadas inválido.") from exc

        response_map = {item.question_id: (item.answer or "").strip() for item in response_items if item.question_id}
        goal_map = {goal.question_id: goal for goal in parsed_detected_goals if goal.question_id}

        reconciled_goals: List[FormDetectedGoal] = []
        for qid, response_text in response_map.items():
            existing_goal = goal_map.get(qid)
            if existing_goal:
                reconciled_goals.append(
                    FormDetectedGoal(
                        question_id=qid,
                        pillar=PillarEnum.META_MAGNUS.value if qid == META_MAGNUS_QUESTION_ID else existing_goal.pillar,
                        title=_normalize_goal_title(existing_goal.title, max_words=10)[:60] or _normalize_goal_title(response_text, max_words=10)[:60] or "Meta",
                        description=existing_goal.description or response_text or None,
                    )
                )
            elif qid == META_MAGNUS_QUESTION_ID:
                reconciled_goals.append(
                    FormDetectedGoal(
                        question_id=META_MAGNUS_QUESTION_ID,
                        pillar=PillarEnum.META_MAGNUS.value,
                        title=_normalize_goal_title(response_text, max_words=10)[:60] or "Meta Magnus",
                        description=response_text or None,
                    )
                )

        parsed_detected_goals = reconciled_goals
        return cls(
            full_name=full_name,
            email=email,
            whatsapp=whatsapp,
            date_of_birth=date_of_birth,
            responses=response_items,
            detected_goals=parsed_detected_goals,
            profile_photo=profile_photo
        )

class GoalCreate(BaseModel):
    pillar: str
    title: str
    description: Optional[str] = None
    target_date: Optional[str] = None

class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target_date: Optional[str] = None
    status: Optional[str] = None

class GoalResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    pillar: str
    title: str
    description: Optional[str] = None
    target_date: Optional[str] = None
    status: str = "active"
    created_at: str
    is_deleted: bool = False


def _parse_iso_to_date(value: str) -> date:
    """Parse ISO datetime/date strings into date."""
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return date.fromisoformat(value[:10])


def _add_12_months(value: date) -> date:
    """Add 12 calendar months preserving day when possible."""
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        # Handles Feb 29 -> Feb 28 in non-leap years
        return value.replace(year=value.year + 1, day=28)


def _get_user_cycle_window(user_created_at: str, reference_day: Optional[date] = None) -> tuple[date, date]:
    """
    Return the active cycle start/end for the reference day.
    Cycle 1: starts on registration date and ends 12 months later.
    Next cycle starts on D+1 of previous cycle end.
    """
    today = reference_day or datetime.now(timezone.utc).date()
    cycle_start = _parse_iso_to_date(user_created_at)
    cycle_end = _add_12_months(cycle_start)

    while today > cycle_end:
        cycle_start = cycle_end + timedelta(days=1)
        cycle_end = _add_12_months(cycle_start)

    return cycle_start, cycle_end


def _get_current_cycle_deadline(user_created_at: str, reference_day: Optional[date] = None) -> str:
    """Return current cycle end as YYYY-MM-DD."""
    _, cycle_end = _get_user_cycle_window(user_created_at, reference_day=reference_day)
    return cycle_end.isoformat()

class ChatMessage(BaseModel):
    message: str
    context: Optional[str] = None
    pillar: Optional[str] = None

class AIKnowledgeCreate(BaseModel):
    category: str
    content: str
    priority: int = 1

class AIKnowledgeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    category: str
    content: str
    priority: int
    created_at: str
    created_by: str

class AnalyzeResponseRequest(BaseModel):
    pillar: str
    question: str
    answer: str

class DetectedGoal(BaseModel):
    pillar: PillarEnum | str
    title: str
    description: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = re.sub(r"\s+", " ", (value or "").strip())[:60]
        if not normalized:
            raise ValueError("title vazio")
        return normalized

class AnalyzeResponseResult(BaseModel):
    feedback: str
    objectives: List[str]
    detected_goals: List[DetectedGoal]
    is_satisfactory: bool
    has_goal: bool
    can_proceed: bool
    needs_improvement: bool

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class SystemPromptUpdate(BaseModel):
    prompt: str

class GoalEvaluation(BaseModel):
    goal_id: str
    goal_title: str
    goal_description: Optional[str] = None
    goal_pillar: Optional[str] = None
    is_completed: bool
    score: Optional[int] = Field(default=None, ge=1, le=10)

class NPSRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    id: str = Field(alias="_id")
    user_id: str
    cycle: int = Field(ge=1, le=12)
    send_date: datetime
    fill_date: Optional[datetime] = None
    evaluations: List[GoalEvaluation]
    status: str

class NPSSubmissionEvaluation(BaseModel):
    goal_id: str
    score: int = Field(ge=1, le=10)

class NPSSubmission(BaseModel):
    evaluations: List[NPSSubmissionEvaluation]


class NPSHistoryItem(BaseModel):
    id: str
    send_date: datetime
    fill_date: Optional[datetime] = None
    status: str
    average_score: Optional[float] = None
    cycle: int


class AdminNPSOverviewItem(BaseModel):
    user_id: str
    full_name: str
    email: str
    last_nps_status: Optional[str] = None
    last_nps_date: Optional[datetime] = None

PILLARS_WITH_META_MAGNUS = [
    "ESPIRITUALIDADE",
    "CUIDADOS COM A SAÚDE",
    "EQUILÍBRIO EMOCIONAL",
    "LAZER",
    "GESTÃO DO TEMPO E ORGANIZAÇÃO",
    "DESENVOLVIMENTO INTELECTUAL",
    "IMAGEM PESSOAL",
    "FAMÍLIA",
    "CRESCIMENTO PROFISSIONAL",
    "FINANÇAS",
    "NETWORKING E CONTRIBUIÇÃO",
    "META MAGNUS",
]

META_MAGNUS_QUESTION_ID = "ca7e651a-a3a7-41f0-b38f-81f5bcc0b699"


class PillarEnum(str, Enum):
    ESPIRITUALIDADE = "ESPIRITUALIDADE"
    CUIDADOS_COM_A_SAUDE = "CUIDADOS COM A SAÚDE"
    EQUILIBRIO_EMOCIONAL = "EQUILÍBRIO EMOCIONAL"
    LAZER = "LAZER"
    GESTAO_DO_TEMPO_E_ORGANIZACAO = "GESTÃO DO TEMPO E ORGANIZAÇÃO"
    DESENVOLVIMENTO_INTELECTUAL = "DESENVOLVIMENTO INTELECTUAL"
    IMAGEM_PESSOAL = "IMAGEM PESSOAL"
    FAMILIA = "FAMÍLIA"
    CRESCIMENTO_PROFISSIONAL = "CRESCIMENTO PROFISSIONAL"
    FINANCAS = "FINANÇAS"
    NETWORKING_E_CONTRIBUICAO = "NETWORKING E CONTRIBUIÇÃO"
    META_MAGNUS = "META MAGNUS"

# ==================== HELPER FUNCTIONS ====================

def generate_password(length=10):
    """Generate a random password"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def hash_password(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_password_strength(password: str) -> None:
    """Validate password minimum complexity."""
    if len(password) < 10:
        raise HTTPException(status_code=400, detail="A senha deve ter no mínimo 10 caracteres.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="A senha deve incluir ao menos uma letra maiúscula.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="A senha deve incluir ao menos uma letra minúscula.")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=400, detail="A senha deve incluir ao menos um número.")

def _prune_attempts(attempts: List[datetime], now: datetime) -> List[datetime]:
    window_start = now - timedelta(minutes=LOGIN_WINDOW_MINUTES)
    return [attempt for attempt in attempts if attempt >= window_start]

def ensure_login_not_rate_limited(identifier: str) -> None:
    now = datetime.now(timezone.utc)
    recent_attempts = _prune_attempts(LOGIN_ATTEMPTS.get(identifier, []), now)
    LOGIN_ATTEMPTS[identifier] = recent_attempts
    if len(recent_attempts) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente em alguns minutos."
        )

def record_failed_login_attempt(identifier: str) -> None:
    now = datetime.now(timezone.utc)
    recent_attempts = _prune_attempts(LOGIN_ATTEMPTS.get(identifier, []), now)
    recent_attempts.append(now)
    LOGIN_ATTEMPTS[identifier] = recent_attempts

def clear_login_attempts(identifier: str) -> None:
    LOGIN_ATTEMPTS.pop(identifier, None)

def ensure_init_route_allowed(setup_token: Optional[str]) -> None:
    """Protect one-time init endpoints in production."""
    if ENV != "production":
        return
    if not INIT_SETUP_TOKEN:
        raise HTTPException(status_code=403, detail="Endpoint de inicialização desativado em produção.")
    if setup_token != INIT_SETUP_TOKEN:
        raise HTTPException(status_code=403, detail="Token de inicialização inválido.")

def generate_password_reset_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash

def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

async def optimize_profile_picture(file: UploadFile) -> BytesIO:
    """Validate and optimize a profile image before upload."""
    allowed_types = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Formato de imagem inválido. Use JPEG ou PNG.")

    raw_bytes = await file.read()
    max_size_bytes = 5 * 1024 * 1024
    if len(raw_bytes) > max_size_bytes:
        raise HTTPException(status_code=413, detail="Imagem excede o tamanho máximo de 5MB.")

    try:
        image = Image.open(BytesIO(raw_bytes))
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=415, detail="Arquivo enviado não é uma imagem válida.") from exc

    image = image.convert("RGB")
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((400, 400), Image.Resampling.LANCZOS)

    optimized_bytes = BytesIO()
    image.save(optimized_bytes, format="JPEG", quality=80, optimize=True)
    optimized_bytes.seek(0)
    await file.close()
    return optimized_bytes

async def upload_profile_picture(user_id: str, file: UploadFile) -> str:
    """Upload optimized profile image to local storage (dev) or Cloudflare R2 (prod)."""
    optimized_bytes = await optimize_profile_picture(file)
    filename = f"{user_id}_profile.jpg"

    if ENV == "development":
        UPLOAD_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
        local_path = UPLOAD_DIR_LOCAL / filename
        with open(local_path, "wb") as local_file:
            local_file.write(optimized_bytes.getbuffer())
        return f"/uploads/profile_photos/{filename}"

    if ENV == "production":
        if not all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT, R2_BUCKET_NAME]):
            raise HTTPException(
                status_code=500,
                detail="R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT e R2_BUCKET_NAME são obrigatórios em produção.",
            )

        try:
            import boto3
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="Dependência boto3 não instalada.") from exc

        object_path = f"profile_photos/{filename}"

        s3_client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT.rstrip("/"),
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
            region_name="auto",
        )

        s3_client.upload_fileobj(
            optimized_bytes,
            R2_BUCKET_NAME,
            object_path,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

        if R2_PUBLIC_BASE_URL:
            return f"{R2_PUBLIC_BASE_URL.rstrip('/')}/{object_path}"

        return f"{R2_ENDPOINT.rstrip('/')}/{R2_BUCKET_NAME}/{object_path}"

    raise HTTPException(status_code=500, detail="ENV inválido para upload de imagem.")

def _build_cookie_security_config(request: Optional[Request] = None) -> Dict[str, Any]:
    """Build cookie security settings with safe defaults and HTTPS awareness."""
    secure = JWT_COOKIE_SECURE
    if request is not None and request.url.scheme != "https" and ENV != "production":
        secure = False

    samesite = JWT_COOKIE_SAMESITE
    if samesite == "none" and not secure:
        samesite = "lax"

    return {
        "secure": secure,
        "samesite": samesite,
        "domain": JWT_COOKIE_DOMAIN,
    }


async def create_user_session(user_id: str, request: Optional[Request] = None) -> str:
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    session_doc = {
        "id": session_id,
        "user_id": user_id,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=JWT_EXP_HOURS)).isoformat(),
        "last_seen_at": now.isoformat(),
        "revoked_at": None,
        "ip_address": request.client.host if request and request.client else None,
        "user_agent": request.headers.get("user-agent") if request else None,
    }
    await db.sessions.insert_one(session_doc)
    return session_id


def create_token(user_id: str, session_id: str) -> str:
    """Create a JWT token"""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXP_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0].lower(), parts[1].strip()
    if scheme != "bearer" or not token:
        return None
    return token


def _extract_auth_token(request: Request) -> Optional[str]:
    # Prefer cookie for backward compatibility; fallback to Bearer for browsers
    # that block third-party cookies when frontend and API are on different domains.
    return request.cookies.get(JWT_COOKIE_NAME) or _extract_bearer_token(request)

async def get_current_user(request: Request):
    """Get the current authenticated user"""
    token = _extract_auth_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    payload = decode_token(token)
    session_id = payload.get("sid")
    if not session_id:
        raise HTTPException(status_code=401, detail="Sessão inválida")

    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or session.get("revoked_at"):
        raise HTTPException(status_code=401, detail="Sessão encerrada")

    try:
        session_expiry = datetime.fromisoformat(session["expires_at"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Sessão inválida")

    if session_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sessão expirada")

    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {"last_seen_at": datetime.now(timezone.utc).isoformat()}}
    )

    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Usuário inativo. Aguarde aprovação do administrador.")
    return user

async def get_admin_user(user: dict = Depends(get_current_user)):
    """Get the current user and verify they are an admin"""
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores.")
    return user

def send_welcome_email(to_email: str, full_name: str, password: str):
    """Send welcome email with credentials"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Bem-vindo ao ELIOS - Suas Credenciais de Acesso'
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #0d0d0d; color: #e5e7eb; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px; background-color: #141414; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #ffffff; }}
                .subtitle {{ color: #cbd5e1; }}
                .body-text {{ color: #e5e7eb; }}
                .credentials {{ background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .field {{ margin: 10px 0; }}
                .label {{ color: #cbd5e1; font-size: 12px; text-transform: uppercase; }}
                .value {{ color: #f8fafc; font-size: 18px; font-weight: bold; }}
                .warning {{ background-color: #f59e0b20; border-left: 4px solid #f59e0b; color: #fde68a; padding: 15px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ELIOS</div>
                    <p class="subtitle">Assistente de Performance da Elite</p>
                </div>
                
                <p class="body-text">Olá, <strong>{full_name}</strong>!</p>
                
                <p class="body-text">Parabéns por completar seu cadastro no programa Elite da HUTOO EDUCAÇÃO!</p>
                
                <p class="body-text">Suas credenciais de acesso ao sistema ELIOS são:</p>
                
                <div class="credentials">
                    <div class="field">
                        <div class="label">Email</div>
                        <div class="value">{to_email}</div>
                    </div>
                    <div class="field">
                        <div class="label">Senha Temporária</div>
                        <div class="value">{password}</div>
                    </div>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Importante:</strong><br>
                    Sua conta precisa ser ativada por um administrador antes que você possa acessar o sistema.
                    Você receberá uma notificação quando sua conta estiver ativa.
                </div>
                
                <p class="body-text">Recomendamos que você altere sua senha após o primeiro acesso.</p>
                
                <div class="footer">
                    <p>HUTOO EDUCAÇÃO - Programa Elite</p>
                    <p>Este é um email automático, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        
        logger.info(f"Welcome email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_password_reset_email(to_email: str, full_name: str, reset_token: str):
    """Send password reset instructions."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'ELIOS - Redefinição de Senha'
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email

        reset_link = (
            f"{FRONTEND_RESET_PASSWORD_URL.rstrip('/')}?token={reset_token}"
            if FRONTEND_RESET_PASSWORD_URL else ""
        )

        instructions = (
            f'<p class="body-text"><a href="{reset_link}">Clique aqui para redefinir sua senha</a></p>'
            if reset_link else
            f'<p class="body-text">Use este token para redefinir sua senha: <strong>{reset_token}</strong></p>'
        )

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #0d0d0d; color: #e5e7eb; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px; background-color: #141414; border-radius: 10px; }}
                .body-text {{ color: #e5e7eb; }}
                .warning {{ background-color: #f59e0b20; border-left: 4px solid #f59e0b; color: #fde68a; padding: 15px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <p class="body-text">Olá, <strong>{full_name}</strong>.</p>
                <p class="body-text">Recebemos uma solicitação para redefinir sua senha no ELIOS.</p>
                {instructions}
                <div class="warning">
                    Este link/token expira em {RESET_PASSWORD_TTL_MINUTES} minutos.
                    Se você não solicitou essa alteração, ignore este email.
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        logger.info(f"Password reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False

# ==================== AI FUNCTIONS ====================

async def get_system_prompt() -> str:
    """Get the system prompt from database or use default"""
    config = await db.system_config.find_one({"key": "elios_prompt"}, {"_id": 0})
    if config and config.get("value"):
        return config["value"]
    return DEFAULT_ELIOS_PROMPT

async def generate_elios_summary(user_id: str) -> str:
    """Generate and persist an executive summary for user form responses."""
    responses = await db.form_responses.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    if not responses:
        await db.users.update_one({"id": user_id}, {"$set": {"elios_summary": ""}})
        return ""

    question_ids = list({response["question_id"] for response in responses if response.get("question_id")})
    questions = await db.questions.find(
        {"id": {"$in": question_ids}},
        {"_id": 0, "id": 1, "title": 1, "pillar": 1}
    ).to_list(200)
    questions_map = {question["id"]: question for question in questions}

    formatted_responses = []
    for index, response in enumerate(responses, start=1):
        question = questions_map.get(response["question_id"], {})
        formatted_responses.append(
            f"{index}. Pilar: {question.get('pillar', 'N/A')} | "
            f"Pergunta: {question.get('title', 'Pergunta não encontrada')} | "
            f"Resposta: {response.get('answer', '')}"
        )

    system_prompt = (
        "Resume os 11 pilares e a Meta Magnus deste utilizador num perfil técnico e denso "
        "de no máximo 400 tokens. Este resumo servirá de base para um Coach de IA."
    )
    user_message = "Consolide as respostas abaixo no formato solicitado:\n\n" + "\n".join(formatted_responses)

    summary = await call_ai_provider(system_prompt, user_message)
    if not summary or summary.startswith("Erro"):
        logger.warning(f"Failed to generate ELIOS summary for user_id={user_id}: {summary}")
        return summary or ""

    await db.users.update_one({"id": user_id}, {"$set": {"elios_summary": summary}})
    return summary

async def build_user_context(user_id: str) -> str:
    """Build comprehensive user context for ELIOS"""
    context_parts = []
    
    # Get user info
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    elios_summary = user.get("elios_summary") if user else None
    if elios_summary:
        if user:
            context_parts.append(f"USUÁRIO: {user.get('full_name', 'Desconhecido')}")
        context_parts.append("\n[ELIOS SUMMARY - PERFIL CONSOLIDADO DO USUÁRIO]")
        context_parts.append(elios_summary)
        recent_goals = await db.goals.find(
            {"user_id": user_id, "is_deleted": False},
            {"_id": 0, "pillar": 1, "title": 1, "description": 1, "status": 1, "created_at": 1}
        ).sort("created_at", -1).limit(5).to_list(5)

        context_parts.append("\n[5 METAS MAIS RECENTES DO USUÁRIO]")
        if recent_goals:
            for goal in recent_goals:
                context_parts.append(
                    f"- [{goal.get('pillar', 'SEM PILAR')}] {goal.get('title', 'Sem título')} "
                    f"({goal.get('status', 'sem status')})"
                )
                if goal.get("description"):
                    context_parts.append(f"  {goal['description'][:200]}")
        else:
            context_parts.append("- Nenhuma meta encontrada.")
        context_parts.append("\n[FIM DO CONTEXTO INJETADO PELO SISTEMA]")
        return "\n".join(context_parts)

    if user:
        context_parts.append(f"USUÁRIO: {user.get('full_name', 'Desconhecido')}")

    # Fallback for legacy users without summary
    questions = await db.questions.find({"is_active": True}, {"_id": 0}).to_list(100)
    questions_map = {q["id"]: q for q in questions}
    responses = await db.form_responses.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    pillar_responses = {}
    for resp in responses:
        question = questions_map.get(resp["question_id"])
        if question:
            pillar = question["pillar"]
            pillar_responses[pillar] = {
                "resposta_inicial": resp["answer"],
                "data_preenchimento": resp.get("created_at", "N/A")
            }

    context_parts.append("\n[DADOS DOS 11 PILARES DO USUÁRIO]")
    fallback_pillars_order = [
        "ESPIRITUALIDADE", "CUIDADOS COM A SAÚDE", "EQUILÍBRIO EMOCIONAL",
        "LAZER", "GESTÃO DO TEMPO E ORGANIZAÇÃO", "DESENVOLVIMENTO INTELECTUAL",
        "IMAGEM PESSOAL", "FAMÍLIA", "CRESCIMENTO PROFISSIONAL",
        "FINANÇAS", "NETWORKING E CONTRIBUIÇÃO", "META MAGNUS"
    ]
    for pillar in fallback_pillars_order:
        context_parts.append(f"\n📌 {pillar}:")
        if pillar in pillar_responses:
            resp_data = pillar_responses[pillar]
            context_parts.append(f"   Resposta Inicial: {resp_data['resposta_inicial'][:500]}...")
        else:
            context_parts.append("   Resposta Inicial: Não preenchido")

    # Get only active goals organized by pillar
    goals = await db.goals.find(
        {"user_id": user_id, "is_deleted": False, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    pillar_goals = {}
    for goal in goals:
        pillar = goal["pillar"]
        if pillar not in pillar_goals:
            pillar_goals[pillar] = []
        pillar_goals[pillar].append({
            "titulo": goal["title"],
            "descricao": goal["description"],
            "status": goal["status"],
            "data_limite": goal.get("target_date", "Sem prazo")
        })
    
    # Build goals context for each pillar
    context_parts.append("\n[METAS ATIVAS DO USUÁRIO]")
    
    pillars_order = [
        "ESPIRITUALIDADE", "CUIDADOS COM A SAÚDE", "EQUILÍBRIO EMOCIONAL",
        "LAZER", "GESTÃO DO TEMPO E ORGANIZAÇÃO", "DESENVOLVIMENTO INTELECTUAL",
        "IMAGEM PESSOAL", "FAMÍLIA", "CRESCIMENTO PROFISSIONAL",
        "FINANÇAS", "NETWORKING E CONTRIBUIÇÃO", "META MAGNUS"
    ]
    
    for pillar in pillars_order:
        context_parts.append(f"\n📌 {pillar}:")

        # Active goals
        if pillar in pillar_goals:
            context_parts.append(f"   Metas Ativas ({len(pillar_goals[pillar])}):")
            for goal in pillar_goals[pillar]:
                context_parts.append(f"      🎯 {goal['titulo']} ({goal['status']})")
                if goal["descricao"]:
                    context_parts.append(f"         └─ {goal['descricao'][:200]}")
        else:
            context_parts.append("   Metas Ativas: Nenhuma meta definida")

    # Add additional knowledge from admin
    knowledge_docs = await db.ai_knowledge.find({"is_active": True}, {"_id": 0}).sort("priority", -1).to_list(50)
    if knowledge_docs:
        context_parts.append("\n[CONHECIMENTO ADICIONAL DO PROGRAMA ELITE]")
        for doc in knowledge_docs:
            context_parts.append(f"- [{doc['category']}] {doc['content']}")
    
    context_parts.append("\n[FIM DO CONTEXTO INJETADO PELO SISTEMA]")
    
    return "\n".join(context_parts)

ADMIN_ROLES = {"ADMIN"}

def _ensure_admin_role(user_role: Optional[str]) -> None:
    if (user_role or "").upper() not in ADMIN_ROLES:
        raise PermissionError("Acesso negado: apenas administradores podem usar esta ferramenta.")

def _is_safe_select_query(sql_query: str) -> bool:
    normalized = (sql_query or "").strip().lower()
    if not normalized.startswith("select"):
        return False
    blocked = [" drop ", " delete ", " update ", " insert ", " alter ", " truncate ", " create "]
    padded = f" {normalized} "
    return not any(token in padded for token in blocked)

async def execute_db_query(sql_query: str, user_role: Optional[str]) -> List[Dict[str, Any]]:
    _ensure_admin_role(user_role)
    if not _is_safe_select_query(sql_query):
        raise ValueError("Consulta inválida. Apenas comandos SELECT são permitidos.")

    users = await db.users.find({}, {"_id": 0, "id": 1, "full_name": 1, "whatsapp": 1, "email": 1, "role": 1, "created_at": 1}).to_list(5000)
    goals = await db.goals.find({}, {"_id": 0, "id": 1, "user_id": 1, "title": 1, "progress": 1, "status": 1}).to_list(5000)
    nps = await db.nps_responses.find({}, {"_id": 0, "id": 1, "user_id": 1, "score": 1, "feedback": 1}).to_list(5000)

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id TEXT, nome TEXT, whatsapp TEXT, email TEXT, cargo TEXT, data_cadastro TEXT)")
    cur.execute("CREATE TABLE goals (id TEXT, user_id TEXT, titulo TEXT, progresso REAL, status TEXT)")
    cur.execute("CREATE TABLE nps_responses (id TEXT, user_id TEXT, nota REAL, feedback TEXT)")

    cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", [
        (u.get("id", ""), u.get("full_name", ""), u.get("whatsapp", ""), u.get("email", ""), u.get("role", ""), u.get("created_at", "")) for u in users
    ])
    cur.executemany("INSERT INTO goals VALUES (?, ?, ?, ?, ?)", [
        (g.get("id", ""), g.get("user_id", ""), g.get("title", ""), g.get("progress", 0), g.get("status", "")) for g in goals
    ])
    cur.executemany("INSERT INTO nps_responses VALUES (?, ?, ?, ?)", [
        (r.get("id", ""), r.get("user_id", ""), r.get("score", 0), r.get("feedback", "")) for r in nps
    ])

    try:
        rows = cur.execute(sql_query).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


async def send_whatsapp_message(phone: str, message: str, user_role: Optional[str]) -> Dict[str, str]:
    _ensure_admin_role(user_role)
    await send_whatsapp_message_via_evolution(phone, message)
    return {"status": "sent"}

def get_ai_provider_settings() -> Dict[str, str]:
    """Return Groq provider settings."""
    return {
        "api_key": GROQ_API_KEY,
        "base_url": GROQ_BASE_URL,
        "model": GROQ_MODEL,
        "name": "Groq"
    }

async def call_ai_provider(
    system_message: str,
    user_message: str,
    history: List[dict] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 400,
    user_role: Optional[str] = None,
) -> str:
    """Call configured AI provider for chat completion using OpenAI-compatible API."""
    provider = get_ai_provider_settings()
    
    if not provider["api_key"]:
        return f"Erro: Chave da API {provider['name']} não configurada. Contate o administrador."
    
    messages = [{"role": "system", "content": system_message}]
    
    # Add conversation history (last 4 messages)
    if history:
        for msg in history[-4:]:
            messages.append({"role": "user", "content": msg["user_message"]})
            messages.append({"role": "assistant", "content": msg["assistant_message"]})
    
    messages.append({"role": "user", "content": user_message})

    tools = None
    if (user_role or "").upper() in ADMIN_ROLES:
        tools = [
            {"type": "function", "function": {"name": "execute_db_query", "description": "Executa consulta analítica SQL read-only nas tabelas users, goals e nps_responses.", "parameters": {"type": "object", "properties": {"sql_query": {"type": "string"}}, "required": ["sql_query"]}}},
            {"type": "function", "function": {"name": "send_whatsapp_message", "description": "Envia mensagem via WhatsApp após confirmação humana do administrador.", "parameters": {"type": "object", "properties": {"phone": {"type": "string"}, "message": {"type": "string"}}, "required": ["phone", "message"]}}}
        ]
    
    payload = {k: v for k, v in {
        "model": model or provider["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "tools": tools
    }.items() if v is not None}

    try:
        response = await asyncio.to_thread(
            requests.post,
            f"{provider['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            logger.error(
                f"{provider['name']} API error: {response.status_code} - {response.text}"
            )
            return "Serviço de IA temporariamente indisponível. Tente novamente em instantes."

        data = response.json()
        first_choice = (data.get("choices") or [{}])[0]
        first_message = first_choice.get("message") or {}

        tool_calls = first_message.get("tool_calls") or []
        if tool_calls:
            messages.append({
                "role": "assistant",
                "content": first_message.get("content") or "",
                "tool_calls": tool_calls
            })

            for tool_call in tool_calls:
                function_data = tool_call.get("function") or {}
                function_name = function_data.get("name")
                raw_arguments = function_data.get("arguments") or "{}"
                tool_call_id = tool_call.get("id")

                try:
                    parsed_arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    parsed_arguments = {}

                tool_result: Any
                try:
                    if function_name == "execute_db_query":
                        tool_result = await execute_db_query(
                            parsed_arguments.get("sql_query", ""),
                            user_role
                        )
                    elif function_name == "send_whatsapp_message":
                        tool_result = await send_whatsapp_message(
                            parsed_arguments.get("phone", ""),
                            parsed_arguments.get("message", ""),
                            user_role
                        )
                    else:
                        tool_result = {"error": f"Ferramenta não suportada: {function_name}"}
                except Exception as tool_error:
                    tool_result = {"error": str(tool_error)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": function_name or "unknown_tool",
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            second_response = await asyncio.to_thread(
                requests.post,
                f"{provider['base_url']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {provider['api_key']}",
                    "Content-Type": "application/json"
                },
                json={k: v for k, v in {
                    "model": model or provider["model"],
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }.items() if v is not None},
                timeout=60
            )

            if second_response.status_code != 200:
                logger.error(
                    f"{provider['name']} API second call error: {second_response.status_code} - {second_response.text}"
                )
                return "Serviço de IA temporariamente indisponível. Tente novamente em instantes."

            second_data = second_response.json()
            second_choice = (second_data.get("choices") or [{}])[0]
            second_message = second_choice.get("message") or {}
            return second_message.get("content") or "Não foi possível gerar uma resposta final."

        return first_message.get("content") or "Não foi possível gerar uma resposta."

    except requests.Timeout:
        logger.error(f"{provider['name']} API timeout")
        return "A resposta demorou muito. Por favor, tente novamente."
    except Exception as e:
        logger.error(f"{provider['name']} API error: {e}")
        return "Erro interno ao processar sua mensagem. Tente novamente."

async def chat_with_elios(user_id: str, message: str, context: str = None, pillar: str = None, user_role: Optional[str] = None) -> str:
    """Main function to chat with ELIOS"""
    
    # Get system prompt
    system_prompt = await get_system_prompt()
    
    # Build user context
    user_context = await build_user_context(user_id)
    
    # Combine system prompt with user context
    full_system_message = f"{system_prompt}\n\n{user_context}"
    
    # Build user message with optional context
    full_user_message = message
    if pillar:
        full_user_message = f"[Pergunta sobre o pilar: {pillar}]\n\n{message}"
    if context:
        full_user_message = f"[Contexto adicional: {context}]\n\n{full_user_message}"
    
    # Get chat history
    history = await db.chat_history.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(4).to_list(4)
    history.reverse()
    
    # Call configured AI provider
    admin_protocol = ""
    if True:
        admin_protocol = "\n\nPROTOCOLO OBRIGATÓRIO PARA WHATSAPP: se o admin pedir envio, primeiro use execute_db_query para buscar nome completo, whatsapp e email; depois responda exatamente pedindo confirmação: Encontrei o usuário [NOME], com WhatsApp [X] e Email [Y]. Posso prosseguir com o envio?; só após confirmação explícita chame send_whatsapp_message."
    response = await call_ai_provider(full_system_message + admin_protocol, full_user_message, history, user_role=user_role)
    
    # Save to chat history
    chat_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_message": message,
        "assistant_message": response,
        "context": context,
        "pillar": pillar,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chat_history.insert_one(chat_entry)
    
    return response

def extract_json_block(raw_text: str) -> Optional[str]:
    if not raw_text:
        return None
    stripped = raw_text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{[\s\S]*\}", stripped)
    return match.group(0) if match else None

def build_analytical_objectives(
    answer: str,
    detected_goals: List[DetectedGoal],
    fallback_objectives: List[str]
) -> List[str]:
    """Return concise SMART-like objectives, avoiding objective text that mirrors the original answer."""
    normalized_answer = (answer or "").strip().lower()
    objective_candidates = [goal.description.strip() for goal in detected_goals if goal.description and goal.description.strip()]
    objective_candidates.extend([goal.title.strip() for goal in detected_goals if goal.title and goal.title.strip()])
    objective_candidates.extend([item.strip() for item in fallback_objectives if item and item.strip()])

    cleaned_objectives: List[str] = []
    for objective in objective_candidates:
        objective_lower = objective.lower()
        mirrors_answer = (
            len(objective) > 110 and
            (objective_lower in normalized_answer or normalized_answer in objective_lower)
        )
        if mirrors_answer:
            continue
        cleaned_objectives.append(objective)

    if cleaned_objectives:
        return cleaned_objectives[:4]

    answer_sentences = [
        sentence.strip(" .;:-")
        for sentence in re.split(r"[.!?]\s+|\n+", (answer or "").strip())
        if sentence.strip()
    ]
    measurable_sentence = next(
        (
            sentence for sentence in answer_sentences
            if re.search(r"\b(\d+|di[aá]ri[oa]|seman[ae]s?|mensal|minutos?|horas?|x\s*por)\b", sentence.lower())
        ),
        None
    )
    if measurable_sentence:
        return [f"Executar a meta descrita com consistência: {measurable_sentence[:140]}."]

    if detected_goals:
        return [f"Transformar '{detected_goals[0].title}' em ação semanal com frequência definida."]

    return fallback_objectives[:4]

async def analyze_form_response(pillar: str, question: str, answer: str) -> AnalyzeResponseResult:
    """Analyze a form response and return structured validation for progression rules."""
    normalized_answer = (answer or "").strip()
    evasive_answers = {"não sei", "nada", "...", "vazio", "nao sei"}
    if normalized_answer.lower() in evasive_answers or len(normalized_answer) < 5:
        return AnalyzeResponseResult(
            feedback="Sua resposta ainda está muito genérica. Adicione ações concretas para este pilar.",
            objectives=["Descreva ao menos uma ação prática e mensurável.", "Inclua frequência ou prazo (ex.: diariamente, 3x por semana)."],
            detected_goals=[],
            is_satisfactory=False,
            has_goal=False,
            can_proceed=False,
            needs_improvement=True,
        )

    provider = get_ai_provider_settings()
    if not provider["api_key"]:
        return AnalyzeResponseResult(
            feedback="Análise de IA indisponível no momento.",
            objectives=["Revise sua resposta para incluir ações concretas e mensuráveis."],
            detected_goals=[],
            is_satisfactory=False,
            has_goal=False,
            can_proceed=False,
            needs_improvement=True,
        )
    
    system_message = """Você é o ELIOS, o Mentor de Alta Performance. Sua missão é analisar a resposta do usuário, validando se ele definiu metas práticas ou se apenas descreveu problemas.

Retorne SOMENTE JSON válido com este formato:
{
  "feedback": "string curta",
  "objectives": ["meta objetiva 1", "meta objetiva 2"],
  "is_satisfactory": true|false,
  "detected_goals": [
    {"question_id": "uuid", "pillar": "NOME DO PILAR", "title": "verbo + frequência", "rating": 0}
  ]
}

REGRAS DE ANÁLISE:
1. Se a resposta for vaga (ex.: "Quero melhorar"), retorne is_satisfactory=false e feedback pedindo objetivo claro com verbo e frequência.
2. Respostas ideais: extraia metas diretas no formato verbo + frequência.
3. Respostas longas com muitas metas: filtre e retorne somente as 3 metas mais importantes.
4. Em detected_goals, inclua question_id e pillar recebidos no contexto, e rating de 0 a 10 quando aplicável.
5. Nunca copie a resposta inteira; title curto com até 60 caracteres.
6. FEEDBACK máximo de 3 linhas."""

    user_message = f"Pilar: {pillar}\nPergunta: {question}\nResposta do usuário: {answer}"

    try:
        response = await call_ai_provider(
            system_message,
            user_message,
            model=GROQ_FORM_MODEL or provider["model"],
            temperature=0.6,
            max_tokens=350
        )
        if not response:
            raise ValueError("Resposta vazia da IA")

        json_block = extract_json_block(response)
        if not json_block:
            raise ValueError("IA não retornou JSON")

        parsed = json.loads(json_block)
        feedback = (parsed.get("feedback") or "").strip()
        objectives = [str(item).strip() for item in parsed.get("objectives", []) if str(item).strip()]
        is_satisfactory = bool(parsed.get("is_satisfactory", False))
        goals_payload = parsed.get("detected_goals", []) or []

        detected_goals = []
        for goal in goals_payload:
            title = str(goal.get("title", "")).strip()[:60]
            if title:
                detected_goals.append(
                    DetectedGoal(
                        pillar=str(goal.get("pillar") or pillar),
                        title=title
                    )
                )

        has_goal = len(detected_goals) > 0
        can_proceed = is_satisfactory and has_goal

        if can_proceed:
            if not feedback:
                feedback = (
                    "Sua resposta está muito boa. Elencou suas dificuldades e definiu metas para enfrentá-las. "
                    "Continue assim nos demais pilares."
                )

            # Se a IA não retornou objetivos, cria automaticamente
            if not objectives:
                objectives = build_analytical_objectives(
                    answer=answer,
                    detected_goals=detected_goals,
                    fallback_objectives=[]
                )

            # Remove duplicatas mantendo a ordem original
            objectives = list(dict.fromkeys(objectives))
        else:
            if not feedback:
                feedback = "Sua resposta precisa melhorar antes de avançar."
            if not objectives:
                objectives = [
                    "Defina uma ação concreta para este pilar.",
                    "Adicione frequência ou prazo para execução."
                ]
            if not has_goal:
                objectives = [
                    "Liste metas claras para este pilar (ex.: ação + frequência/prazo).",
                    "Reescreva sua resposta incluindo pelo menos uma meta mensurável."
                ]

        return AnalyzeResponseResult(
            feedback=feedback,
            objectives=objectives,
            detected_goals=detected_goals,
            is_satisfactory=is_satisfactory,
            has_goal=has_goal,
            can_proceed=can_proceed,
            needs_improvement=not can_proceed,
        )
    except Exception as e:
        logger.error(f"Error analyzing response: {e}")
        fallback_has_goal = bool(re.search(r"\b(di[aá]rio|semana|vezes|minutos?|horas?|todo dia|prazo)\b", normalized_answer.lower()))
        fallback_satisfactory = len(normalized_answer) >= 50
        fallback_can_proceed = fallback_has_goal and fallback_satisfactory
        fallback_objectives = (
            ["Manter a consistência na execução do plano estabelecido."]
            if fallback_can_proceed else
            [
                "Defina uma ação concreta para este pilar.",
                "Adicione frequência ou prazo para execução."
            ]
        )
        if not fallback_has_goal:
            fallback_objectives = [
                "Liste metas claras para este pilar (ex.: ação + frequência/prazo).",
                "Reescreva sua resposta incluindo pelo menos uma meta mensurável."
            ]
        return AnalyzeResponseResult(
            feedback=(
                "Sua resposta está muito boa. Elencou suas dificuldades e definiu metas para enfrentá-las. Continue assim nos demais pilares."
                if fallback_can_proceed else
                "Sua resposta precisa melhorar com metas mais claras para avançar."
            ),
            objectives=fallback_objectives,
            detected_goals=(
                [DetectedGoal(pillar=pillar, title=f"Definir uma meta acionável para {pillar} com frequência semanal.")]
                if fallback_has_goal else []
            ),
            is_satisfactory=fallback_satisfactory,
            has_goal=fallback_has_goal,
            can_proceed=fallback_can_proceed,
            needs_improvement=not fallback_can_proceed,
        )


WHATSAPP_METADATA_NAMES = (
    "EVOLUTION_API_URL",
    "EVOLUTION_INSTANCE",
    "ELIOS_WHATSAPP_GROUP_JID",
)
WHATSAPP_METADATA_TYPES = {
    "EVOLUTION_API_URL": "url",
    "EVOLUTION_INSTANCE": "string",
    "ELIOS_WHATSAPP_GROUP_JID": "string",
}


async def get_metadata_map(names: List[str]) -> Dict[str, str]:
    docs = await db.metadata.find(
        {"name": {"$in": names}},
        {"_id": 0, "name": 1, "value": 1},
    ).to_list(length=len(names))
    result: Dict[str, str] = {}
    for doc in docs:
        name = doc.get("name")
        value = doc.get("value")
        if isinstance(name, str) and isinstance(value, str):
            result[name] = value
    return result


async def get_whatsapp_runtime_settings() -> Dict[str, str]:
    values = await get_metadata_map(list(WHATSAPP_METADATA_NAMES))
    return {
        "api_url": values.get("EVOLUTION_API_URL", "").strip() or DEFAULT_EVOLUTION_API_URL,
        "instance": values.get("EVOLUTION_INSTANCE", "").strip() or DEFAULT_EVOLUTION_INSTANCE,
        "group_jid": values.get("ELIOS_WHATSAPP_GROUP_JID", "").strip() or ELIOS_WHATSAPP_GROUP_JID,
    }


async def _resolve_whatsapp_lid_sender(lid_jid: str) -> str:
    normalized_lid = lid_jid.strip()
    if not normalized_lid:
        return ""

    existing_user = await db.users.find_one(
        {"whatsapp": normalized_lid},
        {"_id": 0, "whatsapp": 1},
    )
    if existing_user and existing_user.get("whatsapp"):
        return existing_user["whatsapp"]

    settings = await get_whatsapp_runtime_settings()
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    endpoint = f"{settings['api_url']}/chat/findContacts/{settings['instance']}"
    payload = {
        "where": {
            "id": normalized_lid,
        }
    }
    resolved_phone_jid = ""
    bot_number_digits = re.sub(r"\D", "", WHATSAPP_BOT_NUMBER or "")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"DEBUG RESOLUÇÃO LID {normalized_lid}: {json.dumps(response_data)}")
    except Exception as exc:
        logger.warning("Falha ao resolver LID '%s' via Evolution API: %s", normalized_lid, str(exc))
        response_data = {}

    search_targets: List[Any] = []
    if isinstance(response_data, dict):
        search_targets.extend(
            [
                response_data.get("id"),
                response_data.get("remoteJid"),
                response_data.get("jid"),
                response_data.get("chatId"),
                response_data.get("number"),
            ]
        )
        contacts = response_data.get("contacts")
        if isinstance(contacts, list):
            for contact in contacts:
                if isinstance(contact, dict):
                    search_targets.extend(
                        [
                            contact.get("id"),
                            contact.get("remoteJid"),
                            contact.get("jid"),
                            contact.get("number"),
                            contact.get("phone"),
                        ]
                    )
    elif isinstance(response_data, list):
        for item in response_data:
            if isinstance(item, dict):
                search_targets.extend(
                    [
                        item.get("id"),
                        item.get("remoteJid"),
                        item.get("jid"),
                        item.get("number"),
                        item.get("phone"),
                    ]
                )

    for candidate in search_targets:
        if isinstance(candidate, str) and "@s.whatsapp.net" in candidate:
            candidate_jid = candidate.strip()
            candidate_digits = re.sub(r"\D", "", candidate_jid)
            if bot_number_digits and candidate_digits == bot_number_digits:
                continue
            resolved_phone_jid = candidate_jid
            break

    if not resolved_phone_jid:
        for candidate in search_targets:
            if isinstance(candidate, str):
                digits_only = re.sub(r"\D", "", candidate)
                if len(digits_only) >= 8:
                    if bot_number_digits and digits_only == bot_number_digits:
                        continue
                    resolved_phone_jid = f"{digits_only}@s.whatsapp.net"
                    break

    if not resolved_phone_jid:
        identity_doc = await db.whatsapp_identity_resolution.find_one(
            {"lid": normalized_lid},
            {"_id": 0, "phone_jid": 1},
        )
        if identity_doc and isinstance(identity_doc.get("phone_jid"), str) and identity_doc["phone_jid"].strip():
            return identity_doc["phone_jid"].strip()

    if not resolved_phone_jid:
        return normalized_lid

    await db.whatsapp_identity_resolution.update_one(
        {"lid": normalized_lid},
        {
            "$set": {
                "lid": normalized_lid,
                "phone_jid": resolved_phone_jid,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )

    return resolved_phone_jid


def normalize_whatsapp_name(name: Any) -> str:
    if not isinstance(name, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    cleaned_chars: List[str] = []
    for char in without_marks:
        category = unicodedata.category(char)
        if category.startswith(("L", "N")) or char in {" ", "-", "_", ".", "'"}:
            cleaned_chars.append(char)
            continue
        if category == "Zs":
            cleaned_chars.append(" ")
    cleaned = re.sub(r"\s+", " ", "".join(cleaned_chars)).strip()
    return cleaned


def _build_phone_jid(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if "@s.whatsapp.net" in value:
        digits = re.sub(r"\D", "", value)
        return f"{digits}@s.whatsapp.net" if digits else ""
    digits = re.sub(r"\D", "", value)
    if 8 <= len(digits) <= 15:
        return f"{digits}@s.whatsapp.net"
    return ""


async def sync_whatsapp_identities() -> int:
    settings = await get_whatsapp_runtime_settings()
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    endpoint = f"{settings['api_url']}/contacts/fetchContacts/{settings['instance']}"
    processed_count = 0

    async with httpx.AsyncClient(timeout=40.0) as client:
        response = await client.post(endpoint, headers=headers, json={})
        response.raise_for_status()
        response_data = response.json()

    contacts: List[Dict[str, Any]] = []
    if isinstance(response_data, list):
        contacts = [item for item in response_data if isinstance(item, dict)]
    elif isinstance(response_data, dict):
        for key in ("contacts", "data", "result"):
            value = response_data.get(key)
            if isinstance(value, list):
                contacts = [item for item in value if isinstance(item, dict)]
                if contacts:
                    break

    if not contacts:
        logger.info("Sincronização de identidades WhatsApp: nenhum contato retornado.")
        return 0

    for contact in contacts:
        lid = (contact.get("id") or "").strip() if isinstance(contact.get("id"), str) else ""
        if not lid:
            continue
        phone_jid = _build_phone_jid(contact.get("number") or contact.get("phone") or "")
        if not phone_jid:
            continue
        push_name = normalize_whatsapp_name(contact.get("pushName") or contact.get("name") or "")
        await db.whatsapp_identity_resolution.update_one(
            {"lid": lid},
            {
                "$set": {
                    "lid": lid,
                    "phone_jid": phone_jid,
                    "push_name": push_name,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
            upsert=True,
        )
        processed_count += 1

    logger.info("Sincronização de identidades WhatsApp concluída: %s contatos processados.", processed_count)
    return processed_count


async def _run_whatsapp_identity_sync_task() -> None:
    try:
        await sync_whatsapp_identities()
    except Exception as exc:
        logger.error("Erro na sincronização de identidades WhatsApp em background: %s", str(exc))


async def _extract_whatsapp_sender(payload: Dict[str, Any]) -> str:
    data = payload.get("data", {}) if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
    key = data.get("key", {}) if isinstance(data.get("key"), dict) else {}

    remote_jid = key.get("remoteJid")
    participant = key.get("participant")
    phone_pattern = re.compile(r"(\d{8,15})")

    def _extract_phone_candidate(value: Any) -> str:
        if isinstance(value, str) and value.strip():
            stripped_value = value.strip()
            match = phone_pattern.search(stripped_value)
            if match:
                return match.group(1)
            return stripped_value
        return ""

    async def _resolve_if_lid(value: str) -> str:
        normalized_value = value.strip()
        if normalized_value.endswith("@lid"):
            return await _resolve_whatsapp_lid_sender(normalized_value)
        return normalized_value

    if isinstance(remote_jid, str) and "@g.us" in remote_jid and isinstance(participant, str) and participant.strip():
        return await _resolve_if_lid(participant)

    is_lid_sender = isinstance(remote_jid, str) and "@lid" in remote_jid

    if isinstance(remote_jid, str) and remote_jid.strip() and not is_lid_sender:
        return remote_jid.strip()

    if isinstance(participant, str) and participant.strip():
        return await _resolve_if_lid(participant)

    if is_lid_sender:
        sender_candidates = [
            data.get("senderJid"),
            data.get("senderLid"),
            data.get("from"),
            data.get("chatId"),
            data.get("author"),
            key.get("id"),
            data.get("instanceId"),
            data.get("pushName"),
            data.get("verifiedName"),
        ]
        message_data = data.get("message", {}) if isinstance(data.get("message"), dict) else {}
        context_info = (
            message_data.get("extendedTextMessage", {}).get("contextInfo", {})
            if isinstance(message_data.get("extendedTextMessage"), dict)
            and isinstance(message_data.get("extendedTextMessage", {}).get("contextInfo"), dict)
            else {}
        )
        sender_candidates.extend(
            [
                context_info.get("participant"),
                context_info.get("remoteJid"),
            ]
        )

        for candidate in sender_candidates:
            extracted_candidate = _extract_phone_candidate(candidate)
            if extracted_candidate:
                return await _resolve_if_lid(extracted_candidate)

    return ""


def _extract_whatsapp_message(payload: Dict[str, Any]) -> str:
    data = payload.get("data", {}) if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
    data_message = data.get("message", {}) if isinstance(data.get("message"), dict) else {}
    extended_text = (
        data_message.get("extendedTextMessage", {})
        if isinstance(data_message.get("extendedTextMessage"), dict)
        else {}
    )

    primary_candidates = [
        data_message.get("conversation"),
        extended_text.get("text"),
    ]
    fallback_candidates = [
        data.get("body"),
        payload.get("text") if isinstance(payload, dict) else None,
    ]

    for candidate in [*primary_candidates, *fallback_candidates]:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def _extract_whatsapp_message_type(payload: Dict[str, Any]) -> str:
    data = payload.get("data", {}) if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
    data_message = data.get("message", {}) if isinstance(data.get("message"), dict) else {}

    if isinstance(data_message, dict) and data_message:
        return next(iter(data_message.keys()))

    if isinstance(data.get("body"), str) and data.get("body", "").strip():
        return "body"

    return "unknown"


def _extract_remote_jid(payload: Dict[str, Any]) -> str:
    payload_dict = payload if isinstance(payload, dict) else {}
    data = payload_dict.get("data", {}) if isinstance(payload_dict.get("data"), dict) else {}
    data_key = data.get("key", {}) if isinstance(data.get("key"), dict) else {}

    remote_jid = data_key.get("remoteJid")
    if isinstance(remote_jid, str) and remote_jid.strip():
        return remote_jid.strip()

    messages = data.get("messages", []) if isinstance(data.get("messages"), list) else []
    for message in messages:
        if not isinstance(message, dict):
            continue
        message_key = message.get("key", {}) if isinstance(message.get("key"), dict) else {}
        remote_jid = message_key.get("remoteJid")
        if isinstance(remote_jid, str) and remote_jid.strip():
            return remote_jid.strip()

    return ""


def _extract_email_candidate(message: str) -> str:
    if not isinstance(message, str):
        return ""
    normalized = message.strip().lower()
    email_pattern = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", re.IGNORECASE)
    if email_pattern.fullmatch(normalized):
        return normalized
    return ""


def _first_name(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().split(" ")[0] if value.strip() else ""


async def _resolve_whatsapp_user_by_identity(remote_jid: str, incoming_message: str) -> Dict[str, Any]:
    identity = await db.whatsapp_identity_resolution.find_one(
        {"lid": remote_jid},
        {"_id": 0, "user_id": 1, "email": 1},
    )
    if identity and identity.get("user_id"):
        user = await db.users.find_one(
            {"id": identity["user_id"]},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1, "whatsapp": 1},
        )
        if user and user.get("id"):
            return {"status": "linked", "user": user}

    email_candidate = _extract_email_candidate(incoming_message)
    if not email_candidate:
        return {"status": "awaiting_email"}

    escaped_email = re.escape(email_candidate)
    user = await db.users.find_one(
        {"email": {"$regex": f"^{escaped_email}$", "$options": "i"}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "whatsapp": 1},
    )
    if not user or not user.get("id"):
        return {"status": "email_not_found"}

    linked_with_other_lid = await db.whatsapp_identity_resolution.find_one(
        {
            "email": {"$regex": f"^{escaped_email}$", "$options": "i"},
            "lid": {"$ne": remote_jid},
        },
        {"_id": 0, "lid": 1},
    )
    if linked_with_other_lid and linked_with_other_lid.get("lid"):
        return {"status": "email_already_linked"}

    now_iso = datetime.now(timezone.utc).isoformat()
    await db.whatsapp_identity_resolution.update_one(
        {"lid": remote_jid},
        {
            "$set": {
                "lid": remote_jid,
                "user_id": user["id"],
                "email": user.get("email", email_candidate),
                "updated_at": now_iso,
            },
            "$setOnInsert": {
                "created_at": now_iso,
            },
        },
        upsert=True,
    )
    await db.whatsapp_identity_history.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "lid": remote_jid,
            "email": user.get("email", email_candidate),
            "event": "link_created",
            "source": "whatsapp_auto_resolution",
            "created_at": now_iso,
        }
    )
    return {"status": "linked_now", "user": user}


async def _send_chatbot_whatsapp_message(target_phone: str, text: str):
    if not EVOLUTION_API_KEY:
        logger.warning("Envio de WhatsApp do chatbot desativado: EVOLUTION_API_KEY não configurada.")
        return

    clean_phone = re.sub(r"\D", "", str(target_phone))
    if len(clean_phone) < 8:
        logger.warning("Envio de WhatsApp do chatbot abortado: telefone inválido (%s).", target_phone)
        return

    try:
        settings = await get_whatsapp_runtime_settings()
        await send_whatsapp_text(
            clean_phone,
            text,
            api_url=settings["api_url"],
            instance=settings["instance"],
        )
        logger.info(f"Resposta do ELIOS enviada com sucesso para {clean_phone}")
    except Exception as exc:
        logger.error(f"Erro crítico: Falha ao enviar resposta via Evolution API para {clean_phone}. Detalhes: {str(exc)}")


def _parse_whatsapp_group_membership(participant_jids: set[str], whatsapp: Optional[str]) -> bool:
    if not isinstance(whatsapp, str) or not whatsapp.strip():
        return False
    normalized = normalize_whatsapp_jid(whatsapp)
    return bool(normalized and normalized in participant_jids)


def _resolve_profile_photo_media(profile_photo_url: Optional[str]) -> Optional[str]:
    if not isinstance(profile_photo_url, str) or not profile_photo_url.strip():
        return None

    if profile_photo_url.startswith("http://") or profile_photo_url.startswith("https://"):
        return profile_photo_url

    local_url = profile_photo_url.strip()
    if not local_url.startswith("/uploads/"):
        return None

    local_path = ROOT_DIR / local_url.lstrip("/")
    if not local_path.exists() or not local_path.is_file():
        return None

    content = local_path.read_bytes()
    encoded = base64.b64encode(content).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"

# ==================== ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "ELIOS API - Sistema de Performance Elite"}


@api_router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    if not EVOLUTION_API_KEY:
        logger.error("Webhook WhatsApp rejeitado: EVOLUTION_API_KEY não configurada.")
        raise HTTPException(status_code=503, detail="Webhook de WhatsApp indisponível.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON inválido.")

    payload_dict = payload if isinstance(payload, dict) else {}
    logger.info("DEBUG ESTRUTURA COMPLETA: %s", json.dumps(payload_dict, ensure_ascii=False))
    payload_data = payload_dict.get("data", {}) if isinstance(payload_dict.get("data"), dict) else {}
    payload_key = payload_data.get("key", {}) if isinstance(payload_data.get("key"), dict) else {}
    message_type = _extract_whatsapp_message_type(payload_dict)
    logger.info(
        "Webhook recebido - Evento: %s | Instância: %s | Tipo: %s",
        payload_dict.get("event"),
        payload_dict.get("instance"),
        message_type,
    )
    logger.info("Metadata da Mensagem: %s", json.dumps(payload_key, ensure_ascii=False))
    if payload_key.get("fromMe") is True:
        return {"status": "ignored", "reason": "self_message"}

    remote_jid = _extract_remote_jid(payload_dict)
    participant = payload_key.get("participant")

    if (isinstance(remote_jid, str) and "@g.us" in remote_jid) or (isinstance(participant, str) and participant.strip()):
        logger.info(f"Mensagem de grupo ignorada: {remote_jid}")
        return {"status": "ignored", "reason": "group_message"}

    incoming_message = _extract_whatsapp_message(payload_dict)
    logger.info("Processamento: remoteJid='%s' | Msg='%s...'", remote_jid, incoming_message[:50])

    if not remote_jid or not incoming_message:
        return {"status": "ignored", "reason": "payload incompleto"}

    resolution = await _resolve_whatsapp_user_by_identity(remote_jid, incoming_message)
    target_id = re.sub(r"\D", "", remote_jid.split("@")[0])
    if len(target_id) < 8:
        return {"status": "ignored", "reason": "telefone inválido"}

    if resolution["status"] == "awaiting_email":
        await _send_chatbot_whatsapp_message(
            target_id,
            "Olá! Sou o ELIOS. Ainda não reconheço este número. Por favor, digite o seu e-mail de cadastro para começarmos.",
        )
        return {"status": "ok", "reason": "awaiting_email"}

    if resolution["status"] == "email_not_found":
        await _send_chatbot_whatsapp_message(
            target_id,
            "Não encontrei este e-mail no seu cadastro. Por favor, confira e envie novamente.",
        )
        return {"status": "ok", "reason": "email_not_found"}

    if resolution["status"] == "email_already_linked":
        await _send_chatbot_whatsapp_message(
            target_id,
            "Esse e-mail está vinculado a outro número de whatsapp. Por favor, fale com o administrador do ELIOS.",
        )
        return {"status": "ok", "reason": "email_already_linked"}

    if resolution["status"] == "linked_now":
        user_name = _first_name(resolution["user"].get("full_name", ""))
        greeting = f"Perfeito, {user_name}! Identifiquei o seu cadastro. Como posso ajudar hoje?" if user_name else "Perfeito! Identifiquei o seu cadastro. Como posso ajudar hoje?"
        await _send_chatbot_whatsapp_message(
            target_id,
            greeting,
        )
        return {"status": "ok", "reason": "linked_now"}

    user = resolution["user"]
    logger.info("Webhook: Iniciando processamento para o mentorado ID: %s (LID: %s)", user["id"], remote_jid)
    ai_response = await chat_with_elios(user["id"], incoming_message)

    await _send_chatbot_whatsapp_message(target_id, ai_response)
    return {"status": "ok", "reason": "linked"}

# ---- AUTH ROUTES ----

@api_router.post("/auth/register")
async def register_user(user: UserCreate):
    """Register a new default user (public endpoint)."""
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    if user.role != "DEFAULT":
        raise HTTPException(
            status_code=403,
            detail="Cadastro público permite apenas usuários com perfil DEFAULT",
        )
    
    password = user.password or generate_password()
    if user.password:
        validate_password_strength(user.password)
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": user.full_name,
        "email": user.email,
        "password_hash": hash_password(password),
        "role": "DEFAULT",
        "is_active": False,
        "form_completed": False,
        "elios_summary": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    return {
        "id": user_doc["id"],
        "email": user.email,
        "message": "Usuário criado com sucesso"
    }

@api_router.post("/auth/login")
async def login(credentials: UserLogin, request: Request, response: Response):
    """Authenticate user and set JWT cookie."""
    client_ip = request.client.host if request.client else "unknown"
    identity_key = f"{credentials.email.lower()}|{client_ip}"
    ensure_login_not_rate_limited(identity_key)

    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})

    if not user:
        record_failed_login_attempt(identity_key)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not verify_password(credentials.password, user["password_hash"]):
        record_failed_login_attempt(identity_key)
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Conta inativa. Aguarde aprovação do administrador.")

    clear_login_attempts(identity_key)
    session_id = await create_user_session(user["id"], request)
    token = create_token(user["id"], session_id)
    cookie_security = _build_cookie_security_config(request)

    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=cookie_security["secure"],
        samesite=cookie_security["samesite"],
        max_age=JWT_COOKIE_MAX_AGE,
        path="/",
        domain=cookie_security["domain"]
    )

    return {
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "form_completed": user.get("form_completed", False),
            "elios_summary": user.get("elios_summary"),
            "profile_photo_url": user.get("profile_photo_url")
        },
        "access_token": token,
        "token_type": "bearer",
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=user["id"],
        full_name=user["full_name"],
        email=user["email"],
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        form_completed=user.get("form_completed", False),
        elios_summary=user.get("elios_summary"),
        profile_photo_url=user.get("profile_photo_url")
    )

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Clear auth cookie."""
    token = _extract_auth_token(request)
    if token:
        try:
            payload = decode_token(token)
            session_id = payload.get("sid")
            if session_id:
                await db.sessions.update_one(
                    {"id": session_id},
                    {"$set": {"revoked_at": datetime.now(timezone.utc).isoformat()}}
                )
        except HTTPException:
            pass

    cookie_security = _build_cookie_security_config(request)
    response.delete_cookie(
        key=JWT_COOKIE_NAME,
        path="/",
        secure=cookie_security["secure"],
        httponly=True,
        samesite=cookie_security["samesite"],
        domain=cookie_security["domain"]
    )
    return {"message": "Logout realizado com sucesso"}

@api_router.post("/auth/change-password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    """Change user password"""
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    validate_password_strength(data.new_password)
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    
    return {"message": "Senha alterada com sucesso"}

@api_router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """Generate a password reset token and send instructions by email."""
    generic_response = {"message": "Se o email existir, enviaremos instruções para redefinição de senha."}
    user = await db.users.find_one({"email": payload.email, "is_active": True}, {"_id": 0})
    if not user:
        # Resposta neutra para evitar enumeração de usuários
        return generic_response

    token, token_hash = generate_password_reset_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=RESET_PASSWORD_TTL_MINUTES)

    await db.password_reset_tokens.update_many(
        {"user_id": user["id"], "used_at": None},
        {"$set": {"used_at": now.isoformat()}}
    )

    await db.password_reset_tokens.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "token_hash": token_hash,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "used_at": None,
        }
    )

    send_password_reset_email(payload.email, user.get("full_name", "Usuário"), token)
    return generic_response

@api_router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    """Reset user password using one-time token."""
    validate_password_strength(payload.new_password)
    token_hash = hash_password_reset_token(payload.token)

    token_doc = await db.password_reset_tokens.find_one({"token_hash": token_hash}, {"_id": 0})
    if not token_doc:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")
    if token_doc.get("used_at"):
        raise HTTPException(status_code=400, detail="Token já utilizado.")

    try:
        expires_at = datetime.fromisoformat(token_doc["expires_at"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.") from exc
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    user = await db.users.find_one({"id": token_doc["user_id"], "is_active": True}, {"_id": 0, "id": 1})
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado.")

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"id": token_doc["user_id"]},
        {"$set": {"password_hash": hash_password(payload.new_password)}}
    )
    await db.password_reset_tokens.update_one(
        {"id": token_doc["id"]},
        {"$set": {"used_at": now.isoformat()}}
    )
    await db.password_reset_tokens.update_many(
        {"user_id": token_doc["user_id"], "used_at": None},
        {"$set": {"used_at": now.isoformat()}}
    )
    await db.sessions.update_many(
        {"user_id": token_doc["user_id"], "revoked_at": None},
        {"$set": {"revoked_at": now.isoformat()}}
    )

    return {"message": "Senha redefinida com sucesso."}

# ---- USERS ROUTES (ADMIN) ----

@api_router.get("/admin/users", response_model=List[UserResponse])
async def list_users(admin: dict = Depends(get_admin_user)):
    """List all users (admin only)"""
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    participant_jids: set[str] = set()
    whatsapp_settings = await get_whatsapp_runtime_settings()
    if whatsapp_settings["group_jid"] and EVOLUTION_API_KEY:
        try:
            participant_jids = await get_group_participants(
                whatsapp_settings["group_jid"],
                api_url=whatsapp_settings["api_url"],
                instance=whatsapp_settings["instance"],
            )
        except Exception as exc:
            logger.warning("Falha ao carregar membros do grupo WhatsApp do ELIOS: %s", str(exc))

    results: List[UserResponse] = []
    for user in users:
        user["whatsapp_in_elios_group"] = _parse_whatsapp_group_membership(
            participant_jids, user.get("whatsapp")
        )
        results.append(UserResponse(**user))
    return results


@api_router.get("/admin/metadata", response_model=List[MetadataEntry])
async def list_metadata(admin: dict = Depends(get_admin_user)):
    _ = admin
    stored_docs = await db.metadata.find(
        {"name": {"$in": list(WHATSAPP_METADATA_NAMES)}},
        {"_id": 0, "id": 1, "type": 1, "name": 1, "value": 1},
    ).to_list(length=len(WHATSAPP_METADATA_NAMES))
    docs_by_name = {
        doc["name"]: doc
        for doc in stored_docs
        if isinstance(doc.get("name"), str)
    }
    fallback_values = await get_whatsapp_runtime_settings()
    runtime_map = {
        "EVOLUTION_API_URL": fallback_values["api_url"],
        "EVOLUTION_INSTANCE": fallback_values["instance"],
        "ELIOS_WHATSAPP_GROUP_JID": fallback_values["group_jid"],
    }

    response: List[MetadataEntry] = []
    for name in WHATSAPP_METADATA_NAMES:
        current = docs_by_name.get(name, {})
        response.append(
            MetadataEntry(
                id=current.get("id") or str(uuid.uuid4()),
                type=current.get("type") or WHATSAPP_METADATA_TYPES[name],
                name=name,
                value=current.get("value") or runtime_map.get(name, ""),
            )
        )
    return response


@api_router.put("/admin/metadata", response_model=List[MetadataEntry])
async def update_metadata(items: List[MetadataUpdateItem], admin: dict = Depends(get_admin_user)):
    _ = admin
    if not items:
        raise HTTPException(status_code=400, detail="Envie ao menos um item para atualização.")
    for item in items:
        if item.name not in WHATSAPP_METADATA_NAMES:
            raise HTTPException(status_code=400, detail=f"Metadata inválida: {item.name}")

    updated_names = set()
    for item in items:
        updated_names.add(item.name)
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = await db.metadata.find_one({"name": item.name}, {"_id": 0, "id": 1})
        await db.metadata.update_one(
            {"name": item.name},
            {
                "$set": {
                    "type": WHATSAPP_METADATA_TYPES[item.name],
                    "name": item.name,
                    "value": item.value.strip(),
                    "updated_at": now_iso,
                },
                "$setOnInsert": {
                    "id": existing.get("id") if existing else str(uuid.uuid4()),
                    "created_at": now_iso,
                },
            },
            upsert=True,
        )

    return await list_metadata(admin)

@api_router.post("/admin/users", response_model=UserResponse)
async def create_user_by_admin(payload: AdminUserCreate, admin: dict = Depends(get_admin_user)):
    """Create a new admin user (admin only)."""
    if payload.role != "ADMIN":
        raise HTTPException(status_code=400, detail="Este endpoint cria apenas usuários ADMIN")
    validate_password_strength(payload.password)

    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": payload.full_name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": "ADMIN",
        "is_active": payload.is_active,
        "form_completed": False,
        "elios_summary": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.users.insert_one(user_doc)
    return UserResponse(**user_doc)

@api_router.get("/admin/users/form-responses", response_model=List[AdminUserFormResponses])
async def list_users_form_responses(
    name: Optional[str] = None,
    email: Optional[str] = None,
    registered_from: Optional[str] = None,
    registered_to: Optional[str] = None,
    admin: dict = Depends(get_admin_user)
):
    """List all default users with their responses grouped by the 11 pillars + Meta Magnus."""
    user_filter: Dict[str, Any] = {"role": "DEFAULT"}

    if name:
        user_filter["full_name"] = {"$regex": re.escape(name), "$options": "i"}
    if email:
        user_filter["email"] = {"$regex": re.escape(email), "$options": "i"}

    created_at_filter: Dict[str, str] = {}
    if registered_from:
        try:
            from_dt = datetime.fromisoformat(f"{registered_from}T00:00:00+00:00")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="registered_from inválido. Use YYYY-MM-DD.") from exc
        created_at_filter["$gte"] = from_dt.isoformat()

    if registered_to:
        try:
            to_dt = datetime.fromisoformat(f"{registered_to}T23:59:59.999999+00:00")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="registered_to inválido. Use YYYY-MM-DD.") from exc
        created_at_filter["$lte"] = to_dt.isoformat()

    if created_at_filter:
        user_filter["created_at"] = created_at_filter

    users = await db.users.find(
        user_filter,
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "created_at": 1, "form_completed": 1}
    ).sort("created_at", -1).to_list(1000)

    user_ids = [user["id"] for user in users]
    goals_by_user: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    if user_ids:
        goal_docs = await db.goals.find(
            {"user_id": {"$in": user_ids}, "is_deleted": False},
            {"_id": 0}
        ).sort("created_at", -1).to_list(5000)

        for goal in goal_docs:
            user_goal_map = goals_by_user.setdefault(goal["user_id"], {})
            pillar_goal_list = user_goal_map.setdefault(goal["pillar"], [])
            pillar_goal_list.append(goal)

    question_docs = await db.questions.find({}, {"_id": 0, "id": 1, "pillar": 1}).to_list(200)
    question_to_pillar = {question["id"]: question.get("pillar") for question in question_docs}

    results: List[AdminUserFormResponses] = []
    for user in users:
        responses = await db.form_responses.find(
            {"user_id": user["id"]},
            {"_id": 0, "question_id": 1, "answer": 1, "created_at": 1}
        ).sort("created_at", 1).to_list(200)

        responses_by_pillar: Dict[str, str] = {pillar: "" for pillar in PILLARS_WITH_META_MAGNUS}
        for response in responses:
            pillar = question_to_pillar.get(response.get("question_id"))
            if pillar in responses_by_pillar:
                responses_by_pillar[pillar] = response.get("answer", "")

        results.append(
            AdminUserFormResponses(
                user_id=user["id"],
                full_name=user["full_name"],
                email=user["email"],
                created_at=user["created_at"],
                form_completed=user.get("form_completed", False),
                responses_by_pillar=responses_by_pillar,
                goals_by_pillar=goals_by_user.get(user["id"], {})
            )
        )

    return results

@api_router.put("/admin/users/{user_id}")
async def update_user(user_id: str, update: UserUpdate, admin: dict = Depends(get_admin_user)):
    """Update user (admin only)"""
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    if "email" in update_dict:
        existing = await db.users.find_one({"email": update_dict["email"], "id": {"$ne": user_id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email já cadastrado")
    current_user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1, "email": 1})
    if not current_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    email_changed = (
        "email" in update_dict
        and isinstance(current_user.get("email"), str)
        and current_user.get("email", "").strip().lower() != update_dict["email"].strip().lower()
    )

    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_dict}
    )

    if email_changed:
        now_iso = datetime.now(timezone.utc).isoformat()
        linked_identities = await db.whatsapp_identity_resolution.find(
            {"user_id": user_id},
            {"_id": 0, "lid": 1, "email": 1},
        ).to_list(200)

        if linked_identities:
            history_docs = []
            for identity in linked_identities:
                lid = identity.get("lid")
                if not isinstance(lid, str) or not lid.strip():
                    continue
                history_docs.append(
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "lid": lid,
                        "email": identity.get("email", current_user.get("email", "")),
                        "event": "link_reset_email_changed",
                        "source": "admin_user_update",
                        "created_at": now_iso,
                        "metadata": {
                            "previous_email": current_user.get("email", ""),
                            "new_email": update_dict["email"],
                            "admin_id": admin.get("id"),
                        },
                    }
                )
            if history_docs:
                await db.whatsapp_identity_history.insert_many(history_docs)

        await db.whatsapp_identity_resolution.delete_many({"user_id": user_id})
    
    return {"message": "Usuário atualizado com sucesso"}

@api_router.put("/admin/users/{user_id}/goals/{goal_id}", response_model=GoalResponse)
async def update_user_goal_by_admin(
    user_id: str,
    goal_id: str,
    update: GoalUpdate,
    admin: dict = Depends(get_admin_user)
):
    """Update a specific default user's goal (admin only)."""
    goal = await db.goals.find_one(
        {"id": goal_id, "user_id": user_id, "is_deleted": False},
        {"_id": 0}
    )

    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")

    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if "target_date" in update_dict:
        update_dict.pop("target_date")
    if not update_dict:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    target_user = await db.users.find_one({"id": user_id}, {"_id": 0, "created_at": 1})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if update_dict.get("status") == "completed":
        cycle_deadline = _get_current_cycle_deadline(target_user["created_at"])
        if datetime.now(timezone.utc).date() > date.fromisoformat(cycle_deadline):
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível concluir metas após o encerramento do ciclo ({cycle_deadline})."
            )

    history_doc = {
        "id": str(uuid.uuid4()),
        "goal_id": goal_id,
        "user_id": user_id,
        "changes": update_dict,
        "old_values": {k: goal.get(k) for k in update_dict.keys()},
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "changed_by": admin["id"],
    }
    await db.goal_history.insert_one(history_doc)

    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.goals.update_one({"id": goal_id}, {"$set": update_dict})

    updated_goal = await db.goals.find_one({"id": goal_id, "user_id": user_id}, {"_id": 0})
    return GoalResponse(**updated_goal)

@api_router.post("/admin/users/{user_id}/profile-photo")
async def update_user_profile_photo(
    user_id: str,
    profile_photo: UploadFile = File(...),
    admin: dict = Depends(get_admin_user)
):
    """Upload or replace a user's profile photo (admin only)."""
    existing_user = await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1})
    if not existing_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    profile_photo_url = await upload_profile_picture(user_id, profile_photo)

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"profile_photo_url": profile_photo_url}}
    )

    return {
        "message": "Foto de perfil atualizada com sucesso",
        "profile_photo_url": profile_photo_url
    }


@api_router.post("/admin/users/{user_id}/whatsapp-group")
async def add_user_to_elios_whatsapp_group(
    user_id: str,
    payload: AddUserToWhatsappGroupPayload,
    admin: dict = Depends(get_admin_user),
):
    settings = await get_whatsapp_runtime_settings()

    if not settings["group_jid"]:
        raise HTTPException(status_code=503, detail="Grupo do WhatsApp do ELIOS não configurado.")
    if not EVOLUTION_API_KEY:
        raise HTTPException(status_code=503, detail="Integração com Evolution API não configurada.")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    clean_phone = format_phone_for_whatsapp(user.get("whatsapp", ""))
    if len(clean_phone) < 12:
        raise HTTPException(status_code=400, detail="Usuário não possui WhatsApp válido cadastrado.")

    participant_jids = await get_group_participants(
        settings["group_jid"],
        api_url=settings["api_url"],
        instance=settings["instance"],
    )
    normalized_jid = normalize_whatsapp_jid(clean_phone)
    if normalized_jid in participant_jids:
        raise HTTPException(status_code=409, detail="Usuário já está no grupo do WhatsApp.")

    await add_group_participant(
        settings["group_jid"],
        clean_phone,
        api_url=settings["api_url"],
        instance=settings["instance"],
    )

    bio = payload.biography.strip()
    profile_media = _resolve_profile_photo_media(user.get("profile_photo_url"))
    caption = f"👋 Novo membro no grupo: {user.get('full_name', 'Usuário')}\n\n📝 Bio: {bio}"

    if profile_media:
        await send_whatsapp_media(
            recipient=settings["group_jid"],
            media=profile_media,
            caption=caption,
            filename=f"{user_id}_profile.jpg",
            api_url=settings["api_url"],
            instance=settings["instance"],
        )
    else:
        await send_whatsapp_text(
            settings["group_jid"],
            caption,
            api_url=settings["api_url"],
            instance=settings["instance"],
        )

    await db.whatsapp_group_invites.insert_one(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "group_jid": settings["group_jid"],
            "biography": bio,
            "added_by_admin_id": admin.get("id"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return {"message": "Usuário adicionado ao grupo e apresentação enviada com sucesso."}

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Delete user (admin only)"""
    result = await db.users.delete_one({"id": user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {"message": "Usuário excluído com sucesso"}

# ---- QUESTIONS ROUTES ----

@api_router.get("/questions", response_model=List[QuestionResponse])
async def list_questions():
    """List all active questions"""
    questions = await db.questions.find(
        {"is_active": True}, 
        {"_id": 0}
    ).sort("order", 1).to_list(100)
    return [QuestionResponse(**q) for q in questions]

@api_router.get("/admin/questions", response_model=List[QuestionResponse])
async def list_all_questions(admin: dict = Depends(get_admin_user)):
    """List all questions including inactive (admin only)"""
    questions = await db.questions.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    return [QuestionResponse(**q) for q in questions]

@api_router.post("/admin/questions", response_model=QuestionResponse)
async def create_question(question: QuestionCreate, admin: dict = Depends(get_admin_user)):
    """Create a new question (admin only)"""
    question_doc = {
        "id": str(uuid.uuid4()),
        **question.model_dump(),
        "is_active": True
    }
    
    await db.questions.insert_one(question_doc)
    return QuestionResponse(**question_doc)

@api_router.put("/admin/questions/{question_id}", response_model=QuestionResponse)
async def update_question(question_id: str, update: QuestionUpdate, admin: dict = Depends(get_admin_user)):
    """Update a question (admin only)"""
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    
    result = await db.questions.find_one_and_update(
        {"id": question_id},
        {"$set": update_dict},
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    result.pop("_id", None)
    return QuestionResponse(**result)

@api_router.delete("/admin/questions/{question_id}")
async def delete_question(question_id: str, admin: dict = Depends(get_admin_user)):
    """Soft delete a question (admin only)"""
    result = await db.questions.update_one(
        {"id": question_id},
        {"$set": {"is_active": False}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    
    return {"message": "Pergunta desativada com sucesso"}

# ---- FORM SUBMISSION ROUTES ----

@api_router.post("/form/submit")
async def submit_form(submission: FormSubmission = Depends(FormSubmission.as_form), background_tasks: BackgroundTasks = None):
    """Submit the complete form and create user"""
    # Check if email already exists
    existing = await db.users.find_one({"email": submission.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado. Faça login ou use outro email.")
    
    # Generate password and create user
    password = generate_password()
    user_id = str(uuid.uuid4())
    profile_photo_url = None

    if submission.profile_photo:
        profile_photo_url = await upload_profile_picture(user_id, submission.profile_photo)
    
    user_doc = {
        "id": user_id,
        "full_name": submission.full_name,
        "email": submission.email,
        "whatsapp": submission.whatsapp,
        "date_of_birth": submission.date_of_birth,
        "password_hash": hash_password(password),
        "role": "DEFAULT",
        "is_active": False,  # Inactive until admin approves
        "form_completed": True,
        "elios_summary": None,
        "profile_photo_url": profile_photo_url,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Save all responses
    for response in submission.responses:
        response_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "question_id": response.question_id,
            "answer": response.answer,
            "rating": response.rating,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": 1
        }
        await db.form_responses.insert_one(response_doc)
        if response.rating is not None:
            await db.pillar_states.update_one(
                {"user_id": user_id, "question_id": response.question_id},
                {"$setOnInsert": {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "question_id": response.question_id,
                    "initial_rating": response.rating,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )

    # Save detected goals extracted by ELIOS during "Próximo"
    normalized_keys = set()
    for goal in submission.detected_goals:
        dedupe_key = (goal.pillar.strip().upper(), goal.title.strip().lower())
        if dedupe_key in normalized_keys:
            continue
        normalized_keys.add(dedupe_key)
        goal_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "pillar": goal.pillar,
            "title": goal.title,
            "description": goal.description or "",
            "target_date": _get_current_cycle_deadline(user_doc["created_at"]),
            "status": "active",
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.goals.insert_one(goal_doc)

    if background_tasks:
        background_tasks.add_task(generate_elios_summary, user_id)
    
    # Send welcome email
    email_sent = send_welcome_email(submission.email, submission.full_name, password)
    
    return {
        "message": "Formulário enviado com sucesso! Verifique seu email para obter suas credenciais.",
        "email_sent": email_sent,
        "user_id": user_id
    }

@api_router.get("/form/responses")
async def get_my_responses(
    user_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    """Get current user's form responses"""
    target_user_id = user["id"]
    if user_id and user_id != user["id"]:
        if user.get("role") != "ADMIN":
            raise HTTPException(status_code=403, detail="Acesso negado.")
        target_user_id = user_id

    responses = await db.form_responses.find(
        {"user_id": target_user_id},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with question data
    enriched = []
    for resp in responses:
        question = await db.questions.find_one({"id": resp["question_id"]}, {"_id": 0})
        enriched.append({
            **resp,
            "question": question
        })
    
    return enriched

@api_router.put("/form/responses/{response_id}")
async def update_response(response_id: str, data: dict, user: dict = Depends(get_current_user)):
    """Update a form response (keeps history)"""
    response = await db.form_responses.find_one(
        {"id": response_id, "user_id": user["id"]},
        {"_id": 0}
    )
    
    if not response:
        raise HTTPException(status_code=404, detail="Resposta não encontrada")
    
    # Save history
    history_doc = {
        "id": str(uuid.uuid4()),
        "response_id": response_id,
        "user_id": user["id"],
        "old_answer": response["answer"],
        "new_answer": data.get("answer"),
        "changed_at": datetime.now(timezone.utc).isoformat()
    }
    await db.response_history.insert_one(history_doc)
    
    # Update response
    new_version = response.get("version", 1) + 1
    await db.form_responses.update_one(
        {"id": response_id},
        {
            "$set": {
                "answer": data.get("answer"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": new_version
            }
        }
    )
    
    return {"message": "Resposta atualizada com sucesso", "version": new_version}

# ---- GOALS ROUTES ----

@api_router.get("/goals", response_model=List[GoalResponse])
async def list_goals(user: dict = Depends(get_current_user)):
    """List user's goals"""
    goals = await db.goals.find(
        {"user_id": user["id"], "is_deleted": False},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    current_cycle_deadline = _get_current_cycle_deadline(user["created_at"])
    for goal in goals:
        if goal.get("status") == "active" and goal.get("target_date") != current_cycle_deadline:
            goal["target_date"] = current_cycle_deadline
            await db.goals.update_one(
                {"id": goal["id"], "user_id": user["id"]},
                {"$set": {"target_date": current_cycle_deadline, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
    return [GoalResponse(**g) for g in goals]

@api_router.get("/goals/pillar/{pillar}")
async def get_goals_by_pillar(pillar: str, user: dict = Depends(get_current_user)):
    """Get goals for a specific pillar"""
    goals = await db.goals.find(
        {"user_id": user["id"], "pillar": pillar, "is_deleted": False},
        {"_id": 0}
    ).to_list(100)
    current_cycle_deadline = _get_current_cycle_deadline(user["created_at"])
    for goal in goals:
        if goal.get("status") == "active" and goal.get("target_date") != current_cycle_deadline:
            goal["target_date"] = current_cycle_deadline
            await db.goals.update_one(
                {"id": goal["id"], "user_id": user["id"]},
                {"$set": {"target_date": current_cycle_deadline, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
    return goals

@api_router.post("/goals", response_model=GoalResponse)
async def create_goal(goal: GoalCreate, user: dict = Depends(get_current_user)):
    """Create a new goal"""
    cycle_deadline = _get_current_cycle_deadline(user["created_at"])
    goal_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "pillar": goal.pillar,
        "title": goal.title,
        "description": goal.description or "",
        "target_date": cycle_deadline,
        "status": "active",
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.goals.insert_one(goal_doc)
    return GoalResponse(**goal_doc)

@api_router.put("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: str, update: GoalUpdate, user: dict = Depends(get_current_user)):
    """Update a goal (keeps history)"""
    goal = await db.goals.find_one(
        {"id": goal_id, "user_id": user["id"]},
        {"_id": 0}
    )
    
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    if "target_date" in update_dict:
        update_dict.pop("target_date")

    if update_dict.get("status") == "completed":
        cycle_deadline = _get_current_cycle_deadline(user["created_at"])
        if datetime.now(timezone.utc).date() > date.fromisoformat(cycle_deadline):
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível concluir metas após o encerramento do ciclo ({cycle_deadline})."
            )
    
    if update_dict:
        # Save history
        history_doc = {
            "id": str(uuid.uuid4()),
            "goal_id": goal_id,
            "user_id": user["id"],
            "changes": update_dict,
            "old_values": {k: goal.get(k) for k in update_dict.keys()},
            "changed_at": datetime.now(timezone.utc).isoformat()
        }
        await db.goal_history.insert_one(history_doc)
        
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.goals.update_one(
            {"id": goal_id},
            {"$set": update_dict}
        )
    
    updated = await db.goals.find_one({"id": goal_id}, {"_id": 0})
    return GoalResponse(**updated)

@api_router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user: dict = Depends(get_current_user)):
    """Soft delete a goal"""
    result = await db.goals.update_one(
        {"id": goal_id, "user_id": user["id"]},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    
    return {"message": "Meta excluída com sucesso"}

@api_router.get("/goals/{goal_id}/history")
async def get_goal_history(goal_id: str, user: dict = Depends(get_current_user)):
    """Get history of changes for a goal"""
    goal = await db.goals.find_one({"id": goal_id, "user_id": user["id"]})
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    
    history = await db.goal_history.find(
        {"goal_id": goal_id},
        {"_id": 0}
    ).sort("changed_at", -1).to_list(100)
    
    return history


@api_router.get("/goals/weekly-progress")
async def get_weekly_progress(
    user_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    target_user_id = current_user["id"]
    if user_id and user_id != current_user["id"]:
        if current_user.get("role") != "ADMIN":
            raise HTTPException(status_code=403, detail="Acesso negado.")
        target_user_id = user_id

    target_user = await db.users.find_one({"id": target_user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    goals = await db.goals.find(
        {"user_id": target_user_id, "is_deleted": {"$ne": True}},
        {"_id": 0, "id": 1, "title": 1, "pillar": 1},
    ).to_list(length=None)

    nps_records = await db.nps_records.find(
        {"user_id": target_user_id, "status": "completed"}
    ).sort("send_date", -1).to_list(length=3)

    scores_by_goal: Dict[str, List[Dict[str, Any]]] = {}
    for record in reversed(nps_records):
        reference_date = record.get("fill_date") or record.get("send_date")
        month_label = ""
        if isinstance(reference_date, datetime):
            month_label = reference_date.strftime("%b/%Y")
        for evaluation in record.get("evaluations", []):
            goal_id = evaluation.get("goal_id")
            score = evaluation.get("score")
            if not goal_id or not isinstance(score, (int, float)):
                continue
            scores_by_goal.setdefault(goal_id, []).append(
                {"month": month_label or "Ciclo", "score": round(float(score), 2)}
            )

    progress_items = []
    for goal in goals:
        goal_id = goal.get("id")
        points = scores_by_goal.get(goal_id, [])[-3:]
        values = [point["score"] for point in points]
        average = round(sum(values) / len(values), 2) if values else None
        progress_items.append(
            {
                "goal_id": goal_id,
                "goal_title": goal.get("title", "Meta sem título"),
                "pillar": goal.get("pillar", ""),
                "average": average,
                "series": points,
            }
        )

    return {
        "user_id": target_user_id,
        "full_name": target_user.get("full_name", ""),
        "goals": progress_items,
    }


@api_router.get("/admin/weekly-progress-monitor")
async def get_admin_weekly_progress_monitor(admin: dict = Depends(get_admin_user)):
    _ = admin
    users = await db.users.find({"is_active": True, "role": {"$in": ["DEFAULT", "USER"]}}).to_list(length=None)
    now = datetime.now(timezone.utc)
    monday_anchor = now - timedelta(days=now.weekday())
    mondays = [(monday_anchor - timedelta(days=7 * idx)).date() for idx in range(4)]
    week_labels = [f"Semana {idx}" for idx in range(1, 5)]

    rows = []
    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
        logs = await db.goal_reminders_log.find({"user_id": user_id}).sort("timestamp", -1).to_list(length=50)
        week_data = []
        for monday_date in mondays:
            status_for_week = "not_sent"
            for log in logs:
                ts = log.get("timestamp")
                if not isinstance(ts, datetime):
                    continue
                if ts.date() >= monday_date and ts.date() <= (monday_date + timedelta(days=6)):
                    if log.get("status") == "failed":
                        status_for_week = "failed"
                    elif log.get("link_sent") is True:
                        status_for_week = "success"
                    else:
                        status_for_week = "not_sent"
                    break
            week_data.append({"week_start": monday_date.isoformat(), "status": status_for_week})

        rows.append(
            {
                "user_id": user_id,
                "full_name": user.get("full_name", "Sem nome"),
                "weeks": week_data,
            }
        )

    return {"columns": week_labels, "rows": rows}


@api_router.get("/admin/weekly-progress-cycle/{user_id}")
async def get_admin_weekly_progress_cycle(user_id: str, admin: dict = Depends(get_admin_user)):
    _ = admin
    logs = await db.goal_reminders_log.find({"user_id": user_id}).sort("timestamp", 1).to_list(length=500)
    cycle_data = []
    for log in logs:
        snapshot = log.get("snapshot_data") or {}
        cycle_data.append(
            {
                "timestamp": log.get("timestamp"),
                "status": log.get("status"),
                "link_sent": bool(log.get("link_sent")),
                "medias_calculadas": snapshot.get("medias_calculadas", {}),
                "meta_naves": snapshot.get("meta_naves", []),
            }
        )
    return {"user_id": user_id, "history": cycle_data}

# ---- AI ROUTES ----

@api_router.post("/ai/analyze")
async def analyze_response(data: AnalyzeResponseRequest):
    """Analyze a form response with AI (real-time during form filling)"""
    response = await analyze_form_response(data.pillar, data.question, data.answer)
    return response.model_dump()

@api_router.post("/ai/chat")
async def chat(data: ChatMessage, user: dict = Depends(get_current_user)):
    """Chat with ELIOS"""
    response = await chat_with_elios(
        user["id"], 
        data.message, 
        data.context,
        data.pillar,
        user.get("role")
    )
    return {"response": response}

@api_router.get("/ai/chat/history")
async def get_chat_history(user: dict = Depends(get_current_user)):
    """Get user's chat history"""
    history = await db.chat_history.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    
    history.reverse()
    return history

@api_router.delete("/ai/chat/history")
async def clear_chat_history(user: dict = Depends(get_current_user)):
    """Clear user's chat history"""
    await db.chat_history.delete_many({"user_id": user["id"]})
    return {"message": "Histórico limpo com sucesso"}

# ---- AI KNOWLEDGE ROUTES (ADMIN) ----

@api_router.get("/admin/ai/knowledge", response_model=List[AIKnowledgeResponse])
async def list_ai_knowledge(admin: dict = Depends(get_admin_user)):
    """List all AI knowledge entries"""
    knowledge = await db.ai_knowledge.find({}, {"_id": 0}).sort("priority", -1).to_list(100)
    return [AIKnowledgeResponse(**k) for k in knowledge]

@api_router.post("/admin/ai/knowledge", response_model=AIKnowledgeResponse)
async def add_ai_knowledge(data: AIKnowledgeCreate, admin: dict = Depends(get_admin_user)):
    """Add new knowledge to AI"""
    knowledge_doc = {
        "id": str(uuid.uuid4()),
        **data.model_dump(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin["id"]
    }
    
    await db.ai_knowledge.insert_one(knowledge_doc)
    return AIKnowledgeResponse(**knowledge_doc)

@api_router.delete("/admin/ai/knowledge/{knowledge_id}")
async def delete_ai_knowledge(knowledge_id: str, admin: dict = Depends(get_admin_user)):
    """Delete AI knowledge entry"""
    result = await db.ai_knowledge.delete_one({"id": knowledge_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")
    
    return {"message": "Conhecimento removido com sucesso"}

# ---- SYSTEM PROMPT ROUTES (ADMIN) ----

@api_router.get("/admin/ai/prompt")
async def get_elios_prompt(admin: dict = Depends(get_admin_user)):
    """Get the current ELIOS system prompt"""
    prompt = await get_system_prompt()
    return {"prompt": prompt, "is_default": prompt == DEFAULT_ELIOS_PROMPT}

@api_router.put("/admin/ai/prompt")
async def update_elios_prompt(data: SystemPromptUpdate, admin: dict = Depends(get_admin_user)):
    """Update the ELIOS system prompt"""
    await db.system_config.update_one(
        {"key": "elios_prompt"},
        {
            "$set": {
                "key": "elios_prompt",
                "value": data.prompt,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": admin["id"]
            }
        },
        upsert=True
    )
    return {"message": "Prompt atualizado com sucesso"}

@api_router.post("/admin/ai/prompt/reset")
async def reset_elios_prompt(admin: dict = Depends(get_admin_user)):
    """Reset ELIOS prompt to default"""
    await db.system_config.delete_one({"key": "elios_prompt"})
    return {"message": "Prompt resetado para o padrão", "prompt": DEFAULT_ELIOS_PROMPT}


@api_router.post("/admin/whatsapp/sync-contacts")
async def trigger_whatsapp_contacts_sync(
    background_tasks: BackgroundTasks,
    admin: dict = Depends(get_admin_user),
):
    _ = admin
    background_tasks.add_task(_run_whatsapp_identity_sync_task)
    return {"message": "Sincronização de contatos do WhatsApp iniciada em background."}

# ---- DASHBOARD ROUTES ----

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(
    user_id: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user),
):
    """Get dashboard statistics for the user"""
    target_user_id = user["id"]
    if user_id and user_id != user["id"]:
        if user.get("role") != "ADMIN":
            raise HTTPException(status_code=403, detail="Acesso negado.")
        target_user_id = user_id
    
    # Get goals count by pillar
    pipeline = [
        {"$match": {"user_id": target_user_id, "is_deleted": False}},
        {"$group": {"_id": "$pillar", "count": {"$sum": 1}, "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}}}
    ]
    goals_by_pillar = await db.goals.aggregate(pipeline).to_list(20)
    
    # Get form responses for radar chart
    responses = await db.form_responses.find(
        {"user_id": target_user_id},
        {"_id": 0}
    ).to_list(100)
    
    pillar_data = {}
    for resp in responses:
        question = await db.questions.find_one({"id": resp["question_id"]}, {"_id": 0})
        pillar = (question or {}).get("pillar")
        if pillar:
            if pillar not in pillar_data:
                pillar_data[pillar] = {"filled": True, "goals_count": 0, "completed": 0}
    
    # Add goals count to pillar data
    for g in goals_by_pillar:
        pillar = g["_id"]
        if pillar in pillar_data:
            pillar_data[pillar]["goals_count"] = g["count"]
            pillar_data[pillar]["completed"] = g["completed"]
        else:
            pillar_data[pillar] = {"filled": False, "goals_count": g["count"], "completed": g["completed"]}
    
    # Calculate progress percentage for radar chart (based on completed goals)
    radar_data = []
    pillars_order = [
        "ESPIRITUALIDADE", "CUIDADOS COM A SAÚDE", "EQUILÍBRIO EMOCIONAL",
        "LAZER", "GESTÃO DO TEMPO E ORGANIZAÇÃO", "DESENVOLVIMENTO INTELECTUAL",
        "IMAGEM PESSOAL", "FAMÍLIA", "CRESCIMENTO PROFISSIONAL",
        "FINANÇAS", "NETWORKING E CONTRIBUIÇÃO", "META MAGNUS"
    ]
    
    for pillar in pillars_order:
        data = pillar_data.get(pillar, {"filled": False, "goals_count": 0, "completed": 0})
        total = data["goals_count"]
        completed = data["completed"]
        progress = (completed / total * 100) if total > 0 else (50 if data["filled"] else 0)
        radar_data.append({
            "pillar": pillar,
            "shortName": pillar[:3],
            "progress": round(progress),
            "goals": total,
            "completed": completed
        })

    filled_pillars = sum(1 for p in pillars_order if pillar_data.get(p, {}).get("filled"))
    
    return {
        "pillars": pillar_data,
        "radar_data": radar_data,
        "filled_pillars": filled_pillars,
        "total_pillars": len(pillars_order),
        "total_goals": sum(g["count"] for g in goals_by_pillar),
        "completed_goals": sum(g["completed"] for g in goals_by_pillar)
    }

# ---- INIT DEFAULT DATA ----

@api_router.post("/init/questions")
async def init_default_questions(setup_token: Optional[str] = None):
    """Initialize default questions (run once)"""
    ensure_init_route_allowed(setup_token)
    existing = await db.questions.count_documents({})
    if existing > 0:
        return {"message": "Perguntas já existem", "count": existing}
    
    default_questions = [
        {"pillar": "ESPIRITUALIDADE", "title": "Espiritualidade", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 1},
        {"pillar": "CUIDADOS COM A SAÚDE", "title": "Cuidados com a Saúde", "description": "Como estou e como desejo estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 2},
        {"pillar": "EQUILÍBRIO EMOCIONAL", "title": "Equilíbrio Emocional", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 3},
        {"pillar": "LAZER", "title": "Lazer", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 4},
        {"pillar": "GESTÃO DO TEMPO E ORGANIZAÇÃO", "title": "Gestão do Tempo e Organização", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 5},
        {"pillar": "DESENVOLVIMENTO INTELECTUAL", "title": "Desenvolvimento Intelectual", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 6},
        {"pillar": "IMAGEM PESSOAL", "title": "Imagem Pessoal", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 7},
        {"pillar": "FAMÍLIA", "title": "Família", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 8},
        {"pillar": "CRESCIMENTO PROFISSIONAL", "title": "Crescimento Profissional", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 9},
        {"pillar": "FINANÇAS", "title": "Finanças", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 10},
        {"pillar": "NETWORKING E CONTRIBUIÇÃO", "title": "Networking e Contribuição", "description": "Como estou e como desejo claramente estar em 12 meses? (Lembrar de também listar comportamentos necessários para o atingimento da meta)", "order": 11},
        {"pillar": "META MAGNUS", "title": "Meta Magnus", "description": "A MAIOR E MAIS IMPORTANTE META PARA ATINGIR EM 12 MESES. (Seja específico e claro)", "order": 12}
    ]
    
    for q in default_questions:
        q["id"] = str(uuid.uuid4())
        q["is_active"] = True
        await db.questions.insert_one(q)
    
    return {"message": "Perguntas criadas com sucesso", "count": len(default_questions)}

@api_router.post("/init/admin")
async def init_admin(setup_token: Optional[str] = None):
    """Initialize admin user (run once)"""
    ensure_init_route_allowed(setup_token)
    existing = await db.users.find_one({"role": "ADMIN"})
    if existing:
        return {"message": "Admin já existe", "email": existing["email"]}
    
    admin_doc = {
        "id": str(uuid.uuid4()),
        "full_name": "Administrador ELIOS",
        "email": "admin@hutooeducacao.com",
        "password_hash": hash_password("Admin@123"),
        "role": "ADMIN",
        "is_active": True,
        "form_completed": True,
        "elios_summary": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(admin_doc)
    
    return {
        "message": "Admin criado com sucesso",
        "email": "admin@hutooeducacao.com"
    }

def _build_nps_query(nps_id: str) -> Dict[str, Any]:
    try:
        return {"_id": ObjectId(nps_id)}
    except (InvalidId, TypeError):
        return {"_id": nps_id}


def _serialize_nps_record(doc: Dict[str, Any]) -> Dict[str, Any]:
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@nps_router.get("/history/{user_id}", response_model=List[NPSRecord])
async def get_nps_history(user_id: str):
    records = await db.nps_records.find({"user_id": user_id}).sort("send_date", -1).to_list(200)
    return [NPSRecord(**_serialize_nps_record(record)) for record in records]


@nps_router.get("/history", response_model=List[NPSHistoryItem])
async def get_my_nps_history(current_user: dict = Depends(get_current_user)):
    records = await db.nps_records.find({"user_id": current_user["id"]}).sort("cycle", 1).to_list(200)
    history = []
    for record in records:
        evaluations = record.get("evaluations", [])
        scores = [evaluation.get("score") for evaluation in evaluations if isinstance(evaluation.get("score"), (int, float))]
        average_score = round(sum(scores) / len(scores), 2) if scores else None
        history.append(
            NPSHistoryItem(
                id=str(record.get("_id")),
                send_date=record.get("send_date"),
                fill_date=record.get("fill_date"),
                status=record.get("status", "pending"),
                average_score=average_score,
                cycle=int(record.get("cycle", 1)),
            )
        )
    return history


@api_router.get("/admin/nps-overview", response_model=List[AdminNPSOverviewItem])
async def get_admin_nps_overview(admin: dict = Depends(get_admin_user)):
    _ = admin
    users = await db.users.find({"is_active": True, "role": "DEFAULT"}).to_list(length=None)
    overview: List[AdminNPSOverviewItem] = []

    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
        latest_nps = await db.nps_records.find_one({"user_id": user_id}, sort=[("send_date", -1)])
        overview.append(
            AdminNPSOverviewItem(
                user_id=user_id,
                full_name=user.get("full_name", "Sem nome"),
                email=user.get("email", ""),
                last_nps_status=latest_nps.get("status") if latest_nps else None,
                last_nps_date=latest_nps.get("send_date") if latest_nps else None,
            )
        )

    return overview


@nps_router.get("/link/{nps_id}", response_model=NPSRecord)
async def get_pending_nps_link(nps_id: str):
    nps_doc = await db.nps_records.find_one({**_build_nps_query(nps_id), "status": "pending"})
    if not nps_doc:
        raise HTTPException(status_code=404, detail="NPS pendente não encontrado.")

    user_id = nps_doc.get("user_id")
    evaluations = nps_doc.get("evaluations", [])
    goal_ids = [evaluation.get("goal_id") for evaluation in evaluations if evaluation.get("goal_id")]

    goals_by_id: Dict[str, Dict[str, Any]] = {}
    if user_id and goal_ids:
        goals = await db.goals.find(
            {"user_id": user_id, "id": {"$in": goal_ids}, "is_deleted": {"$ne": True}},
            {"_id": 0, "id": 1, "title": 1, "description": 1, "pillar": 1},
        ).to_list(length=None)
        goals_by_id = {goal.get("id"): goal for goal in goals if goal.get("id")}

    for evaluation in evaluations:
        goal_id = evaluation.get("goal_id")
        goal = goals_by_id.get(goal_id)
        if not goal:
            continue
        evaluation["goal_title"] = goal.get("title") or evaluation.get("goal_title") or "Meta sem título"
        evaluation["goal_description"] = goal.get("description") or evaluation.get("goal_description") or ""
        evaluation["goal_pillar"] = goal.get("pillar") or evaluation.get("goal_pillar") or ""

    return NPSRecord(**_serialize_nps_record(nps_doc))


@nps_router.post("/submit/{nps_id}", response_model=NPSRecord)
async def submit_nps(nps_id: str, submission: NPSSubmission):
    query = {**_build_nps_query(nps_id), "status": "pending"}
    nps_doc = await db.nps_records.find_one(query)
    if not nps_doc:
        raise HTTPException(status_code=404, detail="NPS pendente não encontrado para submissão.")

    score_map = {item.goal_id: item.score for item in submission.evaluations}
    merged_evaluations: List[Dict[str, Any]] = []
    for evaluation in nps_doc.get("evaluations", []):
        goal_id = evaluation.get("goal_id")
        is_completed = bool(evaluation.get("is_completed"))
        if is_completed:
            evaluation["score"] = 10
        else:
            if goal_id not in score_map:
                raise HTTPException(
                    status_code=400,
                    detail=f"Score não informado para meta ativa: {goal_id}.",
                )
            evaluation["score"] = score_map[goal_id]
        merged_evaluations.append(evaluation)

    await db.nps_records.update_one(
        _build_nps_query(nps_id),
        {
            "$set": {
                "evaluations": merged_evaluations,
                "status": "completed",
                "fill_date": datetime.now(timezone.utc),
            }
        },
    )

    updated_doc = await db.nps_records.find_one(_build_nps_query(nps_id))
    if not updated_doc:
        raise HTTPException(status_code=404, detail="NPS não encontrado após atualização.")
    return NPSRecord(**_serialize_nps_record(updated_doc))


@nps_router.post("/trigger/{user_id}")
async def trigger_nps_for_user(
    user_id: str,
    force: bool = Query(default=False),
    admin: dict = Depends(get_admin_user),
):
    _ = admin
    await process_nps_cycles(db, target_user_id=user_id, force=force)
    return {"message": "Processamento manual de NPS executado com sucesso para o utilizador.", "force": force}


@nps_router.post("/trigger-reminders")
async def trigger_nps_reminders(admin: dict = Depends(get_admin_user)):
    _ = admin
    await process_nps_reminders(db)
    return {"message": "Processamento manual de lembretes NPS executado com sucesso."}


# Include the router in the main app
app.include_router(api_router)
app.include_router(nps_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_scheduler():
    scheduler.add_job(
        process_nps_cycles,
        "cron",
        day=22,
        hour=8,
        minute=0,
        timezone="America/Sao_Paulo",
        args=[db],
        id="nps_daily_cron",
        replace_existing=True,
    )
    scheduler.add_job(
        process_nps_reminders,
        "cron",
        hour=8,
        minute=0,
        timezone="America/Sao_Paulo",
        args=[db],
        id="nps_reminders_daily_cron",
        replace_existing=True,
    )
    scheduler.add_job(
        process_weekly_goal_reminders,
        "cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        timezone="America/Sao_Paulo",
        args=[db],
        id="goals_weekly_cron",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
async def shutdown_db_client():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    client.close()
