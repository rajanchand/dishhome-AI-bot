"""
AuditLog model — append-only audit trail.
PostgreSQL: REVOKE DELETE on this table from app_user.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from app.models.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    portal_user_id = Column(UUID(as_uuid=True), ForeignKey("portal_users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    # e.g. customer.create, ticket.update, user.login, payment.verify
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(Text, nullable=True)
    request_body = Column(JSONB, nullable=True)  # sanitized (passwords redacted)
    response_status = Column(Integer, nullable=True)
    changes_before = Column(JSONB, nullable=True)
    changes_after = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
