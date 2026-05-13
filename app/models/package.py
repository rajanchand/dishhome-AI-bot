"""
Package catalog and customer subscription models.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.database import Base


class Package(Base):
    __tablename__ = "packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    service_type = Column(String(20), default="fiber", nullable=False)
    # fiber, wireless, combo
    speed_download_mbps = Column(Integer, nullable=False)
    speed_upload_mbps = Column(Integer, nullable=False)
    monthly_quota_gb = Column(Integer, nullable=True)  # NULL = unlimited
    validity_days = Column(Integer, default=30, nullable=False)
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_quarterly = Column(Numeric(10, 2), nullable=True)
    price_annually = Column(Numeric(10, 2), nullable=True)
    setup_fee = Column(Numeric(10, 2), default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    subscriptions = relationship("CustomerPackage", foreign_keys="CustomerPackage.package_id", back_populates="package")


class CustomerPackage(Base):
    """Customer's active subscription to a package."""
    __tablename__ = "customer_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    billing_cycle_day = Column(Integer, default=1, nullable=False)  # 1-28
    status = Column(String(20), default="active", nullable=False)
    # active, expired, suspended, cancelled
    auto_renew = Column(Boolean, default=True, nullable=False)
    renewal_count = Column(Integer, default=0, nullable=False)
    previous_package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id"), nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="subscriptions")
    package = relationship("Package", foreign_keys=[package_id], back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
