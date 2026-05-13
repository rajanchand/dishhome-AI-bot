"""
Vendor, contract, RMA models.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Numeric, Date,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_code = Column(String(20), unique=True, nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    vendor_type = Column(String(50), nullable=False, index=True)
    # isp_partner, hardware_supplier, field_contractor, noc_support
    contact_person = Column(String(200), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    service_areas = Column(JSONB, nullable=True)  # list of service_area_ids
    sla_response_hours = Column(Integer, default=4, nullable=False)
    sla_resolution_hours = Column(Integer, default=24, nullable=False)
    rating = Column(Numeric(3, 2), default=5.0, nullable=False)
    total_assignments = Column(Integer, default=0, nullable=False)
    completed_assignments = Column(Integer, default=0, nullable=False)
    sla_breaches = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contracts = relationship("VendorContract", back_populates="vendor", cascade="all, delete-orphan")
    rma_requests = relationship("RMARequest", back_populates="vendor")


class VendorContract(Base):
    __tablename__ = "vendor_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    contract_number = Column(String(50), nullable=False)
    contract_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    monthly_value = Column(Numeric(12, 2), nullable=True)
    terms = Column(Text, nullable=True)
    document_url = Column(Text, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    # active, expired, terminated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="contracts")


class RMARequest(Base):
    """Return Merchandise Authorization for faulty hardware."""
    __tablename__ = "rma_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rma_number = Column(String(30), unique=True, nullable=False, index=True)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    device_serial = Column(String(100), nullable=False)
    device_model = Column(String(100), nullable=True)
    issue_description = Column(Text, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    status = Column(String(20), default="initiated", nullable=False)
    # initiated, shipped, received, replaced, refunded, rejected, closed
    shipped_at = Column(DateTime, nullable=True)
    replacement_serial = Column(String(100), nullable=True)
    received_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="rma_requests")
