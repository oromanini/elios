from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from io import BytesIO
import json
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import asyncio
import requests
from PIL import Image, UnidentifiedImageError

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-secret-key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

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

# Upload Configuration
ENV = os.environ.get('ENV', 'development').lower()
UPLOAD_DIR_LOCAL = Path(os.environ.get('UPLOAD_DIR_LOCAL', ROOT_DIR / 'uploads/profile_photos'))
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', '')
GCS_PUBLIC_BASE_URL = os.environ.get('GCS_PUBLIC_BASE_URL', '')

# Security
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI(title="ELIOS - Sistema de Performance Elite")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

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

class FormSubmission(BaseModel):
    full_name: str
    email: EmailStr
    date_of_birth: Optional[str] = None
    profile_photo: Optional[UploadFile] = None
    responses: List[FormResponseCreate]

    @classmethod
    def as_form(
        cls,
        full_name: str = Form(...),
        email: EmailStr = Form(...),
        date_of_birth: Optional[str] = Form(None),
        responses: str = Form(...),
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

        return cls(
            full_name=full_name,
            email=email,
            date_of_birth=date_of_birth,
            responses=response_items,
            profile_photo=profile_photo
        )

class GoalCreate(BaseModel):
    pillar: str
    title: str
    description: str
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
    description: str
    target_date: Optional[str] = None
    status: str = "active"
    created_at: str
    is_deleted: bool = False

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

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class SystemPromptUpdate(BaseModel):
    prompt: str

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
    """Upload optimized profile image to local storage or GCS based on ENV."""
    optimized_bytes = await optimize_profile_picture(file)
    filename = f"{user_id}_profile.jpg"

    if ENV == "development":
        UPLOAD_DIR_LOCAL.mkdir(parents=True, exist_ok=True)
        local_path = UPLOAD_DIR_LOCAL / filename
        with open(local_path, "wb") as local_file:
            local_file.write(optimized_bytes.getbuffer())
        return f"/uploads/profile_photos/{filename}"

    if ENV == "production":
        if not GCS_BUCKET_NAME:
            raise HTTPException(status_code=500, detail="GCS_BUCKET_NAME não configurado em produção.")

        try:
            from google.cloud import storage
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="Dependência google-cloud-storage não instalada.") from exc

        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        object_path = f"profile_photos/{filename}"
        blob = bucket.blob(object_path)

        blob.upload_from_file(optimized_bytes, content_type="image/jpeg")
        try:
            blob.make_public()
        except Exception as make_public_error:
            logger.warning(f"Não foi possível aplicar ACL pública no GCS: {make_public_error}")

        if GCS_PUBLIC_BASE_URL:
            return f"{GCS_PUBLIC_BASE_URL.rstrip('/')}/{object_path}"
        return blob.public_url

    raise HTTPException(status_code=500, detail="ENV inválido para upload de imagem.")

def create_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT token"""
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get the current authenticated user"""
    token = credentials.credentials
    payload = decode_token(token)
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Usuário inativo. Aguarde aprovação do administrador.")
    return user

async def get_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get the current user and verify they are an admin"""
    user = await get_current_user(credentials)
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
                body {{ font-family: Arial, sans-serif; background-color: #0d0d0d; color: #f8fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px; background-color: #141414; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #ffffff; }}
                .credentials {{ background-color: #1a1a1a; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .field {{ margin: 10px 0; }}
                .label {{ color: #888888; font-size: 12px; text-transform: uppercase; }}
                .value {{ color: #f8fafc; font-size: 18px; font-weight: bold; }}
                .warning {{ background-color: #f59e0b20; border-left: 4px solid #f59e0b; padding: 15px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ELIOS</div>
                    <p>Assistente de Performance da Elite</p>
                </div>
                
                <p>Olá, <strong>{full_name}</strong>!</p>
                
                <p>Parabéns por completar seu cadastro no programa Elite da HUTOO EDUCAÇÃO!</p>
                
                <p>Suas credenciais de acesso ao sistema ELIOS são:</p>
                
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
                
                <p>Recomendamos que você altere sua senha após o primeiro acesso.</p>
                
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
    max_tokens: int = 400
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
    
    try:
        response = await asyncio.to_thread(
            requests.post,
            f"{provider['base_url']}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": model or provider["model"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=60
        )

        if response.status_code != 200:
            logger.error(
                f"{provider['name']} API error: {response.status_code} - {response.text}"
            )
            return f"Erro na API: {response.status_code}. Tente novamente."

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except requests.Timeout:
        logger.error(f"{provider['name']} API timeout")
        return "A resposta demorou muito. Por favor, tente novamente."
    except Exception as e:
        logger.error(f"{provider['name']} API error: {e}")
        return f"Erro ao processar sua mensagem: {str(e)}"

async def chat_with_elios(user_id: str, message: str, context: str = None, pillar: str = None) -> str:
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
    response = await call_ai_provider(full_system_message, full_user_message, history)
    
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

async def analyze_form_response(pillar: str, question: str, answer: str) -> str:
    """Analyze a form response and provide feedback using configured AI provider"""
    normalized_answer = (answer or "").strip()
    evasive_answers = {"não sei", "nada", "...", "vazio"}
    if normalized_answer.lower() in evasive_answers or len(normalized_answer) < 5:
        return "Sem problemas! Tente refletir sobre o que falta para este pilar ser nota 10. Pode continuar preenchendo."

    provider = get_ai_provider_settings()
    if not provider["api_key"]:
        return "Configure a API para habilitar análises."
    
    system_message = """Você é o ELIOS, analisando uma resposta do formulário em tempo real.
REGRAS:

Máximo de 50 palavras.

Se o usuário for vago, incentive-o gentilmente a detalhar mais.

Se for específico, valide com entusiasmo.

Proibido saudações ou repetir o usuário."""

    user_message = f"Pilar: {pillar}\nPergunta: {question}\nResposta do usuário: {answer}"

    try:
        response = await call_ai_provider(
            system_message,
            user_message,
            model=GROQ_FORM_MODEL or provider["model"],
            temperature=0.3,
            max_tokens=150
        )
        if not response:
            return "Entendido. Continue o preenchimento, estou processando seu perfil geral."
        return response
    except Exception as e:
        logger.error(f"Error analyzing response: {e}")
        return ""

# ==================== ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "ELIOS API - Sistema de Performance Elite"}

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
async def login(credentials: UserLogin):
    """Login user"""
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Conta inativa. Aguarde aprovação do administrador.")
    
    token = create_token(user["id"], user["email"], user["role"])
    
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
            "form_completed": user.get("form_completed", False),
            "elios_summary": user.get("elios_summary")
        }
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
        elios_summary=user.get("elios_summary")
    )

@api_router.post("/auth/change-password")
async def change_password(data: PasswordChange, user: dict = Depends(get_current_user)):
    """Change user password"""
    if not verify_password(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    
    return {"message": "Senha alterada com sucesso"}

# ---- USERS ROUTES (ADMIN) ----

@api_router.get("/admin/users", response_model=List[UserResponse])
async def list_users(admin: dict = Depends(get_admin_user)):
    """List all users (admin only)"""
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return [UserResponse(**u) for u in users]

@api_router.put("/admin/users/{user_id}")
async def update_user(user_id: str, update: UserUpdate, admin: dict = Depends(get_admin_user)):
    """Update user (admin only)"""
    update_dict = {k: v for k, v in update.model_dump().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {"message": "Usuário atualizado com sucesso"}

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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": 1
        }
        await db.form_responses.insert_one(response_doc)

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
async def get_my_responses(user: dict = Depends(get_current_user)):
    """Get current user's form responses"""
    responses = await db.form_responses.find(
        {"user_id": user["id"]},
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
    return [GoalResponse(**g) for g in goals]

@api_router.get("/goals/pillar/{pillar}")
async def get_goals_by_pillar(pillar: str, user: dict = Depends(get_current_user)):
    """Get goals for a specific pillar"""
    goals = await db.goals.find(
        {"user_id": user["id"], "pillar": pillar, "is_deleted": False},
        {"_id": 0}
    ).to_list(100)
    return goals

@api_router.post("/goals", response_model=GoalResponse)
async def create_goal(goal: GoalCreate, user: dict = Depends(get_current_user)):
    """Create a new goal"""
    goal_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        **goal.model_dump(),
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

# ---- AI ROUTES ----

@api_router.post("/ai/analyze")
async def analyze_response(data: AnalyzeResponseRequest):
    """Analyze a form response with AI (real-time during form filling)"""
    response = await analyze_form_response(data.pillar, data.question, data.answer)
    return {"analysis": response}

@api_router.post("/ai/chat")
async def chat(data: ChatMessage, user: dict = Depends(get_current_user)):
    """Chat with ELIOS"""
    response = await chat_with_elios(
        user["id"], 
        data.message, 
        data.context,
        data.pillar
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

# ---- DASHBOARD ROUTES ----

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    """Get dashboard statistics for the user"""
    
    # Get goals count by pillar
    pipeline = [
        {"$match": {"user_id": user["id"], "is_deleted": False}},
        {"$group": {"_id": "$pillar", "count": {"$sum": 1}, "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}}}
    ]
    goals_by_pillar = await db.goals.aggregate(pipeline).to_list(20)
    
    # Get form responses for radar chart
    responses = await db.form_responses.find(
        {"user_id": user["id"]},
        {"_id": 0}
    ).to_list(100)
    
    pillar_data = {}
    for resp in responses:
        question = await db.questions.find_one({"id": resp["question_id"]}, {"_id": 0})
        if question:
            pillar = question["pillar"]
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
    
    return {
        "pillars": pillar_data,
        "radar_data": radar_data,
        "total_goals": sum(g["count"] for g in goals_by_pillar),
        "completed_goals": sum(g["completed"] for g in goals_by_pillar)
    }

# ---- INIT DEFAULT DATA ----

@api_router.post("/init/questions")
async def init_default_questions():
    """Initialize default questions (run once)"""
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
async def init_admin():
    """Initialize admin user (run once)"""
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
        "email": "admin@hutooeducacao.com",
        "password": "Admin@123"
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
