"""
DishHome AI Voice Bot - Call Model
SQLAlchemy model for call records and transcripts.
"""

import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON
from app.models.database import Base


class CallRecord(Base):
    """Persistent record of each call/conversation."""
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    customer_phone = Column(String(20), nullable=True)
    customer_name = Column(String(100), nullable=True)
    language = Column(String(5), default="en")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    turn_count = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active, completed, handoff
    handoff_reason = Column(Text, nullable=True)
    transcript = Column(JSON, nullable=True)
    sentiment = Column(String(20), nullable=True)
    resolved = Column(Boolean, default=False)
    agent_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "customer_phone": self.customer_phone,
            "customer_name": self.customer_name,
            "language": self.language,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_seconds": self.duration_seconds,
            "turn_count": self.turn_count,
            "status": self.status,
            "handoff_reason": self.handoff_reason,
            "transcript": self.transcript,
            "sentiment": self.sentiment,
            "resolved": self.resolved,
            "agent_notes": self.agent_notes,
        }
