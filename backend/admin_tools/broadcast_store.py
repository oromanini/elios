
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import uuid

class BroadcastStore:
    def __init__(self, db):
        self.db = db

    async def create_pending(self, admin_user_id: str, recipient_count: int, message_template: str, event_description: str, recipients_preview: list[dict]):
        doc = {
            "id": str(uuid.uuid4()), "admin_user_id": admin_user_id, "status": "pending", "audience": "active_users",
            "recipient_count": recipient_count, "message_template": message_template, "event_description": event_description,
            "created_at": datetime.now(timezone.utc).isoformat(), "expires_at": (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(),
            "recipients_preview": recipients_preview[:5], "sent_count": 0, "failed_count": 0,
        }
        await self.db.admin_broadcasts.insert_one(doc)
        return doc

    async def get_pending(self, broadcast_id: str, admin_user_id: str):
        return await self.db.admin_broadcasts.find_one({"id": broadcast_id, "admin_user_id": admin_user_id, "status": "pending"}, {"_id": 0})

    async def finish(self, broadcast_id: str, status: str, sent_count: int, failed_count: int):
        await self.db.admin_broadcasts.update_one({"id": broadcast_id}, {"$set": {"status": status, "sent_count": sent_count, "failed_count": failed_count}})
