
from __future__ import annotations
import asyncio, re, unicodedata

def normalize(s: str) -> str:
    s=(s or "").lower()
    s=unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c)!="Mn")

class AdminTools:
    def __init__(self, db, send_whatsapp_text, format_phone_for_whatsapp):
        self.db=db; self.send_whatsapp_text=send_whatsapp_text; self.format_phone_for_whatsapp=format_phone_for_whatsapp

    async def get_users_count(self, status: str):
        q={} if status=="all" else {"is_active": status=="active"}
        return await self.db.users.count_documents(q)

    async def get_current_nps_status(self, mode: str):
        users = await self.db.users.find({"is_active": True, "role": {"$in": ["DEFAULT", "USER"]}}, {"_id":0,"id":1,"full_name":1}).to_list(5000)
        completed=[]; pending=[]; no_record=[]
        for u in users:
            rec=await self.db.nps_records.find_one({"user_id":u["id"]},{"_id":0,"status":1},sort=[("send_date",-1)])
            if not rec: no_record.append(u)
            elif rec.get("status")=="completed": completed.append(u)
            elif rec.get("status")=="pending": pending.append(u)
        return {"completed": completed, "pending": pending, "no_record": no_record}

    async def list_users_with_goal_score_below(self, target: str, score: int):
        users = await self.db.users.find({"is_active": True, "role": {"$in": ["DEFAULT", "USER"]}}, {"_id":0,"id":1,"full_name":1,"whatsapp":1}).to_list(5000)
        target_n=normalize(target); out=[]
        for u in users:
            rec=await self.db.nps_records.find_one({"user_id":u["id"],"status":"completed"},{"_id":0,"evaluations":1},sort=[("send_date",-1)])
            for ev in (rec or {}).get("evaluations", []):
                sc=ev.get("score")
                if isinstance(sc,(int,float)) and sc < score:
                    hay=normalize(f"{ev.get('goal_pillar','')} {ev.get('goal_title','')}")
                    if target_n in hay:
                        out.append({"full_name":u.get("full_name"),"whatsapp":u.get("whatsapp"),"goal_title":ev.get("goal_title"),"goal_pillar":ev.get("goal_pillar"),"score":sc})
                        if len(out)>=30: return out
        return out

    async def find_users_by_identifier(self, identifier: str):
        ident=identifier.strip(); digits=re.sub(r"\D","",ident)
        ors=[{"full_name":{"$regex":re.escape(ident),"$options":"i"}},{"email":{"$regex":f"^{re.escape(ident)}$","$options":"i"}}]
        if digits:
            ors.extend([{"whatsapp":{"$regex":digits}},{"phone":{"$regex":digits}}])
        return await self.db.users.find({"$or":ors},{"_id":0,"id":1,"full_name":1,"whatsapp":1,"phone":1,"email":1,"is_active":1,"role":1,"elios_summary":1}).limit(5).to_list(5)

    async def send_message_to_user(self, user: dict, message: str):
        phone = user.get("whatsapp") or user.get("phone")
        formatted=self.format_phone_for_whatsapp(phone)
        if not formatted: return False
        await self.send_whatsapp_text(formatted, message)
        return True
