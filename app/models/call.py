"""
CallRecord model — enhanced with customer/agent FKs and search integration.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Text, Boolean, ForeignKey, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.database import Base


class CallRecord(Base):
    """Persistent record of each call/conversation."""
    __tablename__ = "call_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)
    customer_phone = Column(String(20), nullable=True, index=True)
    customer_name = Column(String(200), nullable=True)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    pbx_call_id = Column(String(100), nullable=True, index=True)
    language = Column(String(5), default="ne", nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Numeric(10, 2), default=0.0, nullable=False)
    turn_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False, index=True)
    # active, completed, handoff, abandoned, missed
    handoff_reason = Column(Text, nullable=True)
    transcript = Column(JSONB, nullable=True)
    sentiment = Column(String(20), nullable=True)
    # positive, neutral, negative, angry
    sentiment_score = Column(Numeric(3, 2), nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    ai_resolution_confidence = Column(Numeric(3, 2), nullable=True)
    recording_url = Column(Text, nullable=True)
    transcript_es_id = Column(String(100), nullable=True)
    agent_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "session_id": self.session_id,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "customer_phone": self.customer_phone,
            "customer_name": self.customer_name,
            "assigned_agent_id": str(self.assigned_agent_id) if self.assigned_agent_id else None,
            "language": self.language,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": float(self.duration_seconds or 0),
            "turn_count": self.turn_count,
            "status": self.status,
            "handoff_reason": self.handoff_reason,
            "transcript": self.transcript,
            "sentiment": self.sentiment,
            "sentiment_score": float(self.sentiment_score) if self.sentiment_score is not None else None,
            "resolved": self.resolved,
            "ai_resolution_confidence": float(self.ai_resolution_confidence) if self.ai_resolution_confidence is not None else None,
            "recording_url": self.recording_url,
            "agent_notes": self.agent_notes,
        }
