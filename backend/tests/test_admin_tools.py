import asyncio
import os
import sys

sys.path.append(os.path.abspath("backend"))

from admin_tools.intent_detector import detect_admin_intent
from admin_tools.schemas import AdminIntent
from admin_tools.router import AdminCommandRouter


class FakeCursor:
    def __init__(self, docs): self.docs = docs
    def limit(self, n): self.docs = self.docs[:n]; return self
    async def to_list(self, _n): return list(self.docs)


class FakeUsers:
    def __init__(self, docs): self.docs = docs; self.last_count_query = None
    async def count_documents(self, q): self.last_count_query = q; return len([d for d in self.docs if all(d.get(k)==v for k,v in q.items())]) if q else len(self.docs)
    def find(self, q=None, *_args, **_kwargs):
        q = q or {}
        docs = self.docs
        if "is_active" in q: docs = [d for d in docs if d.get("is_active") == q["is_active"]]
        if "role" in q and "$in" in q["role"]: docs = [d for d in docs if d.get("role") in q["role"]["$in"]]
        return FakeCursor(docs)


class FakeNPS:
    def __init__(self, docs): self.docs = docs
    async def find_one(self, q, *_args, **kwargs):
        rows = [d for d in self.docs if d.get("user_id") == q.get("user_id")]
        if "status" in q: rows = [d for d in rows if d.get("status") == q["status"]]
        return rows[0] if rows else None


class FakeBroadcasts:
    def __init__(self): self.docs=[]
    async def insert_one(self, d): self.docs.append(d)
    async def find_one(self, q, *_args, **_kwargs):
        for d in self.docs:
            if all(d.get(k)==v for k,v in q.items()): return d
        return None
    async def update_one(self, q, u):
        for d in self.docs:
            if d.get("id")==q.get("id"): d.update(u["$set"])


class FakeDB:
    def __init__(self, users, nps):
        self.users = FakeUsers(users)
        self.nps_records = FakeNPS(nps)
        self.admin_broadcasts = FakeBroadcasts()


async def _noop_send(*_args, **_kwargs): return None

def _fmt_phone(p): return p


def test_intents_and_priority():
    assert detect_admin_intent("quantos usuários temos?") == AdminIntent.GET_USERS_COUNT
    assert detect_admin_intent("quantos usuários ativos temos?") == AdminIntent.GET_USERS_COUNT
    assert detect_admin_intent("quantos usuários inativos temos?") == AdminIntent.GET_USERS_COUNT
    assert detect_admin_intent("quais usuários ainda não preencheram o NPS?") == AdminIntent.GET_NPS_CURRENT_CYCLE_STATUS
    assert detect_admin_intent("quais usuários já preencheram o NPS?") == AdminIntent.GET_NPS_CURRENT_CYCLE_STATUS
    assert detect_admin_intent("mande mensagem para todos os usuários ativos") == AdminIntent.BROADCAST_TO_ACTIVE_USERS


def test_non_admin_not_handled():
    db = FakeDB([], [])
    router = AdminCommandRouter(db, _noop_send, _fmt_phone)
    out = asyncio.run(router.handle({"id": "1", "role": "DEFAULT"}, "quantos usuários temos?"))
    assert out.handled is False


def test_count_queries():
    db = FakeDB([{"is_active": True}, {"is_active": False}], [])
    router = AdminCommandRouter(db, _noop_send, _fmt_phone)
    asyncio.run(router.handle({"id": "a", "role": "ADMIN"}, "quantos usuários ativos temos?"))
    assert db.users.last_count_query == {"is_active": True}
    asyncio.run(router.handle({"id": "a", "role": "ADMIN"}, "quantos usuários inativos temos?"))
    assert db.users.last_count_query == {"is_active": False}


def test_broadcast_pending_without_send():
    db = FakeDB([{"id":"u1","full_name":"Joao","is_active":True,"role":"DEFAULT","whatsapp":"5511"}], [])
    router = AdminCommandRouter(db, _noop_send, _fmt_phone)
    out = asyncio.run(router.handle({"id": "a", "role": "ADMIN"}, "mande para todos os usuários ativos lembrete"))
    assert out.handled is True
    assert len(db.admin_broadcasts.docs) == 1
    assert db.admin_broadcasts.docs[0]["status"] == "pending"
