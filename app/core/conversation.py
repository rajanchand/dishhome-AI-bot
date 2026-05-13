"""
DishHome AI Voice Bot - Conversation Manager
Manages dialog state, context, and history for each call session.
"""

import uuid
import time
from typing import Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ConversationTurn:
    """A single turn in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    language: str
    timestamp: float = field(default_factory=time.time)
    confidence: float = 0.0


@dataclass
class ConversationState:
    """Full state of an active conversation."""
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

    def add_turn(self, role: str, content: str, language: str,
                 confidence: float = 0.0) -> None:
        self.turns.append(ConversationTurn(
            role=role, content=content, language=language,
            confidence=confidence,
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
            "turns": [
                {
                    "role": t.role,
                    "content": t.content,
                    "language": t.language,
                    "timestamp": t.timestamp,
                }
                for t in self.turns
            ],
        }


class ConversationManager:
    """Manages all active conversations."""

    def __init__(self):
        self._sessions: dict[str, ConversationState] = {}

    def create_session(self, session_id: Optional[str] = None) -> ConversationState:
        sid = session_id or str(uuid.uuid4())
        state = ConversationState(session_id=sid)
        self._sessions[sid] = state
        logger.info(f"Created conversation session: {sid}")
        return state

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> Optional[ConversationState]:
        state = self._sessions.get(session_id)
        if state:
            state.is_active = False
            logger.info(
                f"Ended session {session_id}: "
                f"{state.turn_count} turns, {state.duration_seconds:.1f}s"
            )
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
            logger.warning(f"Handoff requested for {session_id}: {reason}")
            return True
        return False


conversation_manager = ConversationManager()
