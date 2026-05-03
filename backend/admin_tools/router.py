from __future__ import annotations
import re, logging, os, asyncio
from datetime import datetime, timezone
from .schemas import AdminIntent, AdminRouterResult
from .intent_detector import detect_admin_intent, normalize_text
from .tools import AdminTools
from .broadcast_store import BroadcastStore
from .message_generator import call_groq_json, call_groq_text

logger=logging.getLogger(__name__)

class AdminCommandRouter:
    def __init__(self, db, send_whatsapp_text, format_phone_for_whatsapp):
        self.db=db
        self.tools=AdminTools(db, send_whatsapp_text, format_phone_for_whatsapp)
        self.broadcast_store=BroadcastStore(db)
        self.base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.api_key=os.environ.get("GROQ_API_KEY", "")
        self.model=os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    async def handle(self, admin_user: dict, text: str) -> AdminRouterResult:
        if admin_user.get("role") != "ADMIN":
            return AdminRouterResult(False, "")
        intent=detect_admin_intent(text)
        logger.info("admin_router intent=%s admin_user_id=%s", intent.value, admin_user.get("id"))
        if intent == AdminIntent.UNKNOWN:
            return AdminRouterResult(False, "")
        if intent == AdminIntent.GET_USERS_COUNT:
            t=normalize_text(text)
            status="all"
            if any(k in t for k in ["inativos","inativo","desativados","nao ativos"]): status="inactive"
            elif any(k in t for k in ["ativos","ativo","ativas"]): status="active"
            count=await self.tools.get_users_count(status)
            msg={"all":f"Temos {count} usuários no total.","active":f"Temos {count} usuários ativos.","inactive":f"Temos {count} usuários inativos."}[status]
            return AdminRouterResult(True,msg)
        if intent == AdminIntent.GET_NPS_CURRENT_CYCLE_STATUS:
            t=normalize_text(text); mode="summary"
            if any(k in t for k in ["nao preencheram","pendentes","pendente","nao respondeu"]): mode="pending"
            elif any(k in t for k in ["ja preencheram","respondeu","preencheram"]): mode="completed"
            data=await self.tools.get_current_nps_status(mode)
            if mode=="summary":
                return AdminRouterResult(True,f"No ciclo atual, {len(data['completed'])} usuários já preencheram o NPS, {len(data['pending'])} estão pendentes e {len(data['no_record'])} ainda não possuem NPS gerado.")
            chosen=data[mode]
            if not chosen: return AdminRouterResult(True,"Não encontrei usuários para esse filtro de NPS.")
            names="\n".join([f"{i+1}. {u.get('full_name','Sem nome')}" for i,u in enumerate(chosen[:30])])
            return AdminRouterResult(True,f"Encontrei {len(chosen)} usuários:\n{names}")
        if intent == AdminIntent.LIST_USERS_WITH_GOAL_SCORE_BELOW:
            t=normalize_text(text)
            m=re.search(r"(abaixo de|menor que)\s*(\d+)", t); score=int(m.group(2)) if m else 7
            target=t
            for p in ["quais usuarios estao com", "quem esta com", "listar usuarios com", "meta de", "abaixo de", "menor que", str(score)]: target=target.replace(p," ")
            target=" ".join(target.split()) or "saude"
            rows=await self.tools.list_users_with_goal_score_below(target, score)
            if not rows: return AdminRouterResult(True,f"Não encontrei usuários ativos com {target} abaixo de {score}.")
            items="\n".join([f"{i+1}. {r['full_name']} — {r.get('goal_title') or r.get('goal_pillar')} — nota {r['score']}" for i,r in enumerate(rows)])
            return AdminRouterResult(True,f"Encontrei {len(rows)} usuários com {target} abaixo de {score}:\n{items}")
        if intent == AdminIntent.SEND_MESSAGE_TO_USER:
            m=re.search(r"(?:para|avise)\s+(.+?)(?:\s+(?:avisando|sobre|que|uma|mensagem)\s+|$)", text, re.I)
            identifier=(m.group(1).strip() if m else "")
            instruction=text
            users=await self.tools.find_users_by_identifier(identifier) if identifier else []
            if not users: return AdminRouterResult(True,"Não encontrei nenhum usuário com esse identificador.")
            if len(users)>1:
                return AdminRouterResult(True,"Encontrei mais de um usuário. Especifique melhor:\n"+"\n".join([f"- {u.get('full_name')} ({u.get('email','sem email')})" for u in users]))
            user=users[0]
            if not (user.get("whatsapp") or user.get("phone")): return AdminRouterResult(True,"Esse usuário não possui telefone/WhatsApp válido para envio.")
            prompt=f"Escreva uma mensagem curta de WhatsApp para o usuário.\nDestinatário: {user.get('full_name')}\nInstrução do admin: {instruction}\nContexto opcional: {user.get('elios_summary') or ''}\nRegras: Português brasileiro. Máximo 450 caracteres. Retorne somente a mensagem final."
            text_msg=call_groq_text(self.base_url,self.api_key,self.model,prompt,max_tokens=220) if self.api_key else instruction
            ok=await self.tools.send_message_to_user(user,text_msg)
            return AdminRouterResult(True, f"Mensagem enviada para {user.get('full_name')}." if ok else "Não foi possível enviar a mensagem: telefone inválido.")
        if intent == AdminIntent.BROADCAST_TO_ACTIVE_USERS:
            users=await self.db.users.find({"is_active":True,"role":{"$in":["DEFAULT","USER"]},"$or":[{"whatsapp":{"$exists":True,"$ne":None}},{"phone":{"$exists":True,"$ne":None}}]},{"_id":0,"id":1,"full_name":1,"whatsapp":1,"phone":1}).to_list(5000)
            event_description=text
            prompt=f"Escreva uma mensagem curta de WhatsApp para todos os usuários ativos. Evento/instrução: {event_description}. Use {{nome}} como placeholder. Máximo 450 caracteres."
            template=call_groq_text(self.base_url,self.api_key,self.model,prompt,max_tokens=220) if self.api_key else "Olá {{nome}}, lembrete do evento de hoje."
            doc=await self.broadcast_store.create_pending(admin_user.get("id"), len(users), template, event_description, users[:5])
            return AdminRouterResult(True, f"Encontrei {len(users)} usuários ativos com WhatsApp.\nPrévia:\n{template}\nPara confirmar o envio, responda: confirmar envio {doc['id']}")
        if intent == AdminIntent.CONFIRM_BROADCAST:
            m=re.search(r"confirmar envio\s+([a-f0-9\-]{8,})", normalize_text(text)); bid=m.group(1) if m else ""
            doc=await self.broadcast_store.get_pending(bid, admin_user.get("id"))
            if not doc: return AdminRouterResult(True,"Broadcast não encontrado, expirado ou sem permissão.")
            users=await self.db.users.find({"is_active":True,"role":{"$in":["DEFAULT","USER"]},"$or":[{"whatsapp":{"$exists":True,"$ne":None}},{"phone":{"$exists":True,"$ne":None}}]},{"_id":0,"full_name":1,"whatsapp":1,"phone":1}).to_list(5000)
            sent=0; failed=0
            for u in users:
                name=(u.get("full_name") or "").split()[0] or ""
                msg=doc.get("message_template","").replace("{{nome}}", name)
                ok=await self.tools.send_message_to_user(u,msg)
                sent += 1 if ok else 0; failed += 0 if ok else 1
                await asyncio.sleep(0.5)
            status="sent" if failed==0 else "partial_failed"
            await self.broadcast_store.finish(bid,status,sent,failed)
            return AdminRouterResult(True, f"Envio concluído: {sent} enviados, {failed} falharam.")
        return AdminRouterResult(False,"")
