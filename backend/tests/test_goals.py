import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.abspath("backend"))
from goals_scheduler import build_goal_snapshot, process_weekly_goal_reminders


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self.docs)
        return list(self.docs)[:length]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.inserted = []

    def find(self, query=None, *_args, **_kwargs):
        query = query or {}
        matched = []
        for doc in self.docs:
            ok = True
            for key, value in query.items():
                if isinstance(value, dict) and "$ne" in value:
                    if doc.get(key) == value["$ne"]:
                        ok = False
                        break
                elif doc.get(key) != value:
                    ok = False
                    break
            if ok:
                matched.append(doc)
        return FakeCursor(matched)

    async def insert_one(self, doc):
        self.inserted.append(doc)


class FakeDB:
    def __init__(self, users, goals, nps_records):
        self.users = FakeCollection(users)
        self.goals = FakeCollection(goals)
        self.nps_records = FakeCollection(nps_records)
        self.goal_reminders_log = FakeCollection([])


def test_average_with_1_2_and_3_months():
    goals = [
        {"id": "g1", "title": "Meta 1", "pillar": "Saúde"},
        {"id": "g2", "title": "Meta 2", "pillar": "Finanças"},
        {"id": "g3", "title": "Meta 3", "pillar": "Família"},
    ]
    nps_records = [
        {"evaluations": [{"goal_id": "g1", "score": 6.0}, {"goal_id": "g2", "score": 9.0}, {"goal_id": "g3", "score": 7.0}]},
        {"evaluations": [{"goal_id": "g2", "score": 8.0}, {"goal_id": "g3", "score": 8.0}]},
        {"evaluations": [{"goal_id": "g3", "score": 9.0}]},
    ]

    snapshot = build_goal_snapshot(goals, nps_records)
    assert snapshot["medias_calculadas"]["g1"] == 6.0  # 1 mês
    assert snapshot["medias_calculadas"]["g2"] == 8.5  # 2 meses
    assert snapshot["medias_calculadas"]["g3"] == 8.0  # 3 meses


def test_block_send_for_admin(monkeypatch):
    fake_db = FakeDB(
        users=[{"id": "admin-1", "role": "ADMIN", "is_active": True, "whatsapp": "+5511999999999"}],
        goals=[{"id": "g1", "user_id": "admin-1", "title": "Meta", "pillar": "Saúde"}],
        nps_records=[
            {
                "user_id": "admin-1",
                "status": "completed",
                "send_date": datetime.now(timezone.utc),
                "evaluations": [{"goal_id": "g1", "score": 5.0}],
            }
        ],
    )

    sent = {"count": 0}

    async def fake_send(*_args, **_kwargs):
        sent["count"] += 1

    monkeypatch.setattr("goals_scheduler.send_whatsapp_text", fake_send)
    asyncio.run(process_weekly_goal_reminders(fake_db))

    assert sent["count"] == 0
    assert len(fake_db.goal_reminders_log.inserted) == 0


def test_audit_log_generation(monkeypatch):
    fake_db = FakeDB(
        users=[{"id": "user-1", "role": "USER", "is_active": True, "whatsapp": "+5511999999999"}],
        goals=[{"id": "g1", "user_id": "user-1", "title": "Meta", "pillar": "Saúde"}],
        nps_records=[
            {
                "user_id": "user-1",
                "status": "completed",
                "send_date": datetime.now(timezone.utc),
                "evaluations": [{"goal_id": "g1", "score": 5.0}],
            }
        ],
    )

    async def fake_send(*_args, **_kwargs):
        return None

    monkeypatch.setattr("goals_scheduler.send_whatsapp_text", fake_send)
    asyncio.run(process_weekly_goal_reminders(fake_db))

    assert len(fake_db.goal_reminders_log.inserted) == 1
    saved = fake_db.goal_reminders_log.inserted[0]
    assert saved["user_id"] == "user-1"
    assert saved["status"] == "success"
    assert saved["link_sent"] is True
    assert "meta_naves" in saved["snapshot_data"]
    assert "medias_calculadas" in saved["snapshot_data"]
