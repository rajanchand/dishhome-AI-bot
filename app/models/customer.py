"""
Customer, address, and service area models (Customer 360°).
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.database import Base


class ServiceArea(Base):
    __tablename__ = "service_areas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_name = Column(String(200), nullable=False)
    area_code = Column(String(20), unique=True, nullable=False, index=True)
    municipality = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    province = Column(String(50), nullable=True)
    olt_id = Column(UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=True)
    coverage_polygon = Column(JSONB, nullable=True)  # GeoJSON polygon
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    addresses = relationship("CustomerAddress", back_populates="service_area")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_code = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    phone_primary = Column(String(20), nullable=False, index=True)
    phone_secondary = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    national_id = Column(String(50), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    kyc_verified = Column(Boolean, default=False, nullable=False)
    kyc_verified_at = Column(DateTime, nullable=True)
    kyc_verified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    account_status = Column(String(20), default="active", nullable=False)
    # active, suspended, terminated, pending
    credit_score = Column(Integer, default=700, nullable=False)
    loyalty_tier = Column(String(20), default="bronze", nullable=False)
    preferred_language = Column(String(5), default="ne", nullable=False)
    portal_user_id = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    subscriptions = relationship("CustomerPackage", back_populates="customer", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
    devices = relationship("NetworkDevice", back_populates="customer")


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    address_type = Column(String(20), default="installation", nullable=False)
    # billing, installation, current
    street_address = Column(Text, nullable=False)
    ward = Column(String(10), nullable=True)
    municipality = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    province = Column(String(50), nullable=True)
    postal_code = Column(String(10), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    service_area_id = Column(UUID(as_uuid=True), ForeignKey("service_areas.id"), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="addresses")
    service_area = relationship("ServiceArea", back_populates="addresses")


class ContactInteraction(Base):
    """CRM interaction history (calls, SMS, email, chat)."""
    __tablename__ = "contact_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(20), nullable=False)  # call, sms, email, chat
    summary = Column(Text, nullable=False)
    outcome = Column(String(50), nullable=True)
    handled_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    related_call_id = Column(UUID(as_uuid=True), nullable=True)
    related_ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
