"""
Conversation Manager — hybrid in-memory + Redis persistence.

State is held in-memory for the lifetime of a WS connection, and mirrored to
Redis on every turn so other replicas (agent dashboards, AI coaching) can
observe the conversation in real time and survive process restarts.
"""

import asyncio
import uuid
import time
from typing import Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str
    language: str
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.0


@dataclass
class ConversationState:
    session_id: str
    started_at: float = field(default_factory=time.time)
    language: str = "ne"
    turns: list = field(default_factory=list)
    customer_context: Optional[dict] = None
    intent_history: list = field(default_factory=list)
    is_active: bool = True
    needs_handoff: bool = False
    handoff_reason: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.started_at

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def add_turn(self, role: str, content: str, language: str, confidence: float = 0.0) -> None:
        self.turns.append(ConversationTurn(
            role=role, content=content, language=language, confidence=confidence,
        ))
        if role == "user":
            self.language = language

    def get_history(self, max_turns: int = 10) -> list[dict]:
        recent = self.turns[-max_turns:]
        return [{"role": t.role, "content": t.content} for t in recent]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "language": self.language,
            "turn_count": self.turn_count,
            "is_active": self.is_active,
            "needs_handoff": self.needs_handoff,
            "handoff_reason": self.handoff_reason,
            "customer_context": self.customer_context,
            "intent_history": self.intent_history,
            "turns": [
                {
                    "role": t.role, "content": t.content,
                    "language": t.language, "timestamp": t.timestamp,
                    "confidence": t.confidence,
                }
                for t in self.turns
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        state = cls(
            session_id=data["session_id"],
            started_at=data.get("started_at", time.time()),
            language=data.get("language", "ne"),
            customer_context=data.get("customer_context"),
            intent_history=data.get("intent_history", []),
            is_active=data.get("is_active", True),
            needs_handoff=data.get("needs_handoff", False),
            handoff_reason=data.get("handoff_reason"),
        )
        for t in data.get("turns", []):
            state.turns.append(ConversationTurn(
                role=t["role"], content=t["content"], language=t.get("language", "ne"),
                timestamp=t.get("timestamp", time.time()),
                confidence=t.get("confidence", 0.0),
            ))
        return state


class ConversationManager:
    def __init__(self):
        self._sessions: dict[str, ConversationState] = {}

    def _schedule_persist(self, state: ConversationState) -> None:
        try:
            from app.services.cache_service import cache_service
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(cache_service.set_session(state.session_id, state.to_dict()))
        except Exception as e:
            logger.debug(f"Session persist skipped: {e}")

    def create_session(self, session_id: Optional[str] = None) -> ConversationState:
        sid = session_id or str(uuid.uuid4())
        state = ConversationState(session_id=sid)
        self._sessions[sid] = state
        self._schedule_persist(state)
        logger.info(f"Conversation session created: {sid}")
        return state

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        return self._sessions.get(session_id)

    async def get_or_restore_session(self, session_id: str) -> Optional[ConversationState]:
        if session_id in self._sessions:
            return self._sessions[session_id]
        try:
            from app.services.cache_service import cache_service
            data = await cache_service.get_session(session_id)
            if data:
                state = ConversationState.from_dict(data)
                self._sessions[session_id] = state
                return state
        except Exception as e:
            logger.debug(f"Session restore failed: {e}")
        return None

    def end_session(self, session_id: str) -> Optional[ConversationState]:
        state = self._sessions.get(session_id)
        if state:
            state.is_active = False
            self._schedule_persist(state)
            logger.info(f"Session ended {session_id}: {state.turn_count} turns, {state.duration_seconds:.1f}s")
        return state

    def get_active_sessions(self) -> list[ConversationState]:
        return [s for s in self._sessions.values() if s.is_active]

    def get_all_sessions(self) -> list[ConversationState]:
        return list(self._sessions.values())

    def request_handoff(self, session_id: str, reason: str) -> bool:
        state = self._sessions.get(session_id)
        if state:
            state.needs_handoff = True
            state.handoff_reason = reason
            self._schedule_persist(state)
            logger.warning(f"Handoff requested for {session_id}: {reason}")
            return True
        return False

    def persist(self, session_id: str) -> None:
        state = self._sessions.get(session_id)
        if state:
            self._schedule_persist(state)


conversation_manager = ConversationManager()
