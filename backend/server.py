from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
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
from emergentintegrations.llm.chat import LlmChat, UserMessage

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

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

# SMTP Configuration
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

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
    responses: List[FormResponseCreate]

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
                body {{ font-family: Arial, sans-serif; background-color: #0a1628; color: #f8fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px; background-color: #112240; border-radius: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #0ea5e9; }}
                .credentials {{ background-color: #1e293b; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .field {{ margin: 10px 0; }}
                .label {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; }}
                .value {{ color: #f8fafc; font-size: 18px; font-weight: bold; }}
                .warning {{ background-color: #f59e0b20; border-left: 4px solid #f59e0b; padding: 15px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #94a3b8; font-size: 12px; }}
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

async def get_elios_system_message(user_id: Optional[str] = None) -> str:
    """Build ELIOS system message with knowledge base"""
    
    # Get AI knowledge from database
    knowledge_docs = await db.ai_knowledge.find({"is_active": True}, {"_id": 0}).sort("priority", -1).to_list(100)
    knowledge_text = "\n".join([f"- {doc['content']}" for doc in knowledge_docs])
    
    # Get user context if available
    user_context = ""
    if user_id:
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user:
            user_context = f"\nUsuário atual: {user.get('full_name', 'Desconhecido')}"
        
        # Get user's form responses
        responses = await db.form_responses.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        if responses:
            user_context += "\n\nRespostas do formulário do usuário:"
            for resp in responses:
                question = await db.questions.find_one({"id": resp["question_id"]}, {"_id": 0})
                if question:
                    user_context += f"\n- {question['pillar']}: {resp['answer']}"
        
        # Get user's goals
        goals = await db.goals.find({"user_id": user_id, "is_deleted": False}, {"_id": 0}).to_list(100)
        if goals:
            user_context += "\n\nMetas do usuário:"
            for goal in goals:
                user_context += f"\n- [{goal['pillar']}] {goal['title']}: {goal['description']}"
    
    system_message = f"""Você é ELIOS, o Assistente de Performance da Elite do programa HUTOO EDUCAÇÃO.

Sua personalidade:
- Você é um estrategista de alta performance, direto e motivador
- Usa linguagem profissional mas acessível
- Sempre busca ajudar o usuário a melhorar em seus 11 pilares de vida
- Oferece sugestões práticas e acionáveis
- Celebra conquistas e progresso
- Quando necessário, desafia o usuário a pensar maior

Os 11 Pilares + Meta Magnus que você trabalha:
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
12. META MAGNUS - A maior meta para os próximos 12 meses

Conhecimento adicional do programa:
{knowledge_text}

{user_context}

Diretrizes de resposta:
- Seja conciso mas completo
- Ofereça no máximo 3 sugestões por vez
- Use emojis com moderação para tornar a conversa mais amigável
- Sempre relacione suas sugestões com os pilares quando relevante
- Se o usuário compartilhar uma meta vaga, ajude a torná-la SMART (Específica, Mensurável, Alcançável, Relevante, Temporal)
"""
    
    return system_message

async def analyze_form_response(pillar: str, question: str, answer: str) -> str:
    """Analyze a form response and provide feedback"""
    
    if not OPENAI_API_KEY:
        return "Configure a chave da API OpenAI para habilitar análises."
    
    system_message = f"""Você é ELIOS, analisando a resposta de um usuário no formulário de performance.

Pilar: {pillar}
Pergunta: {question}

Sua tarefa:
1. Analisar se a resposta é específica e bem definida
2. Se for vaga, sugerir como melhorar
3. Se for boa, parabenizar brevemente
4. Sugerir micro-objetivos se a meta for muito ambiciosa
5. Manter resposta curta (máximo 2-3 frases)

Tom: Motivador e direto. Use "Boa!" ou "Excelente!" para respostas boas.
"""
    
    try:
        chat = LlmChat(
            api_key=OPENAI_API_KEY,
            session_id=f"form-analysis-{uuid.uuid4()}",
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        user_message = UserMessage(text=f"Resposta do usuário: {answer}")
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        logger.error(f"Error analyzing response: {e}")
        return "Não foi possível analisar sua resposta no momento."

async def chat_with_elios(user_id: str, message: str, context: Optional[str] = None) -> str:
    """Chat with ELIOS"""
    
    if not OPENAI_API_KEY:
        return "Configure a chave da API OpenAI para habilitar o chat."
    
    system_message = await get_elios_system_message(user_id)
    
    # Get chat history from database
    history = await db.chat_history.find(
        {"user_id": user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    history.reverse()  # Put in chronological order
    
    try:
        chat = LlmChat(
            api_key=OPENAI_API_KEY,
            session_id=f"elios-chat-{user_id}",
            system_message=system_message
        ).with_model("openai", "gpt-5.2")
        
        # Build context from history
        context_text = ""
        for msg in history:
            context_text += f"\nUsuário: {msg['user_message']}\nELIOS: {msg['assistant_message']}"
        
        full_message = message
        if context:
            full_message = f"[Contexto: {context}]\n\n{message}"
        if context_text:
            full_message = f"Histórico recente da conversa:{context_text}\n\nNova mensagem do usuário: {full_message}"
        
        user_message = UserMessage(text=full_message)
        response = await chat.send_message(user_message)
        
        # Save to chat history
        chat_entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "user_message": message,
            "assistant_message": response,
            "context": context,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.chat_history.insert_one(chat_entry)
        
        return response
    except Exception as e:
        logger.error(f"Error chatting with ELIOS: {e}")
        return "Desculpe, não consegui processar sua mensagem no momento. Tente novamente."

# ==================== ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "ELIOS API - Sistema de Performance Elite"}

# ---- AUTH ROUTES ----

@api_router.post("/auth/register")
async def register_user(user: UserCreate):
    """Register a new user (admin only creates users with password)"""
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    password = user.password or generate_password()
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": user.full_name,
        "email": user.email,
        "password_hash": hash_password(password),
        "role": user.role,
        "is_active": True if user.role == "ADMIN" else False,
        "form_completed": False,
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
            "form_completed": user.get("form_completed", False)
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
        form_completed=user.get("form_completed", False)
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
async def submit_form(submission: FormSubmission):
    """Submit the complete form and create user"""
    # Check if email already exists
    existing = await db.users.find_one({"email": submission.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado. Faça login ou use outro email.")
    
    # Generate password and create user
    password = generate_password()
    user_id = str(uuid.uuid4())
    
    user_doc = {
        "id": user_id,
        "full_name": submission.full_name,
        "email": submission.email,
        "password_hash": hash_password(password),
        "role": "DEFAULT",
        "is_active": False,  # Inactive until admin approves
        "form_completed": True,
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
    response = await chat_with_elios(user["id"], data.message, data.context)
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
