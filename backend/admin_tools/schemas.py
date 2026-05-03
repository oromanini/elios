
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

class AdminIntent(str, Enum):
    SEND_MESSAGE_TO_USER = "SEND_MESSAGE_TO_USER"
    GET_USERS_COUNT = "GET_USERS_COUNT"
    GET_NPS_CURRENT_CYCLE_STATUS = "GET_NPS_CURRENT_CYCLE_STATUS"
    LIST_USERS_WITH_GOAL_SCORE_BELOW = "LIST_USERS_WITH_GOAL_SCORE_BELOW"
    BROADCAST_TO_ACTIVE_USERS = "BROADCAST_TO_ACTIVE_USERS"
    CONFIRM_BROADCAST = "CONFIRM_BROADCAST"
    UNKNOWN = "UNKNOWN"

@dataclass
class AdminRouterResult:
    handled: bool
    response: str
    send_whatsapp: bool = True

@dataclass
class UsersCountParams:
    status: str = "all"

@dataclass
class GoalScoreParams:
    target: str
    score: int = 7

@dataclass
class SendMessageParams:
    identifier: str
    message_instruction: str

@dataclass
class BroadcastParams:
    event_description: str
    message_instruction: str

@dataclass
class ConfirmBroadcastParams:
    broadcast_id: str
