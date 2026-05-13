"""
Ticket, TicketComment, TicketAttachment models with SLA management.
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.database import Base
from config.rbac import SLA_HOURS


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True)
    call_record_id = Column(UUID(as_uuid=True), ForeignKey("call_records.id"), nullable=True)
    category = Column(String(50), nullable=False, index=True)
    # connectivity, billing, hardware, new_connection, inquiry
    subcategory = Column(String(100), nullable=True)
    priority = Column(String(20), default="medium", nullable=False, index=True)
    # low, medium, high, critical
    status = Column(String(20), default="open", nullable=False, index=True)
    # open, in_progress, pending_customer, resolved, closed
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    sla_deadline = Column(DateTime, nullable=False, index=True)
    breached_sla = Column(Boolean, default=False, nullable=False, index=True)
    breached_at = Column(DateTime, nullable=True)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    assigned_vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    field_visit_required = Column(Boolean, default=False, nullable=False)
    field_visit_scheduled_at = Column(DateTime, nullable=True)
    network_device_id = Column(UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by_ai = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketComment.created_at")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")

    @staticmethod
    def compute_sla_deadline(priority: str, from_time: datetime | None = None) -> datetime:
        hours = SLA_HOURS.get(priority, 24)
        base = from_time or datetime.utcnow()
        return base + timedelta(hours=hours)


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    author_type = Column(String(20), default="agent", nullable=False)
    # agent, customer, system, ai
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="comments")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    storage_url = Column(Text, nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ticket = relationship("Ticket", back_populates="attachments")
