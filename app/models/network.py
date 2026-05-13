"""
Network device, device metrics (TimescaleDB), outage models.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, Text, Numeric, BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.models.database import Base


class NetworkDevice(Base):
    __tablename__ = "network_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_type = Column(String(20), nullable=False, index=True)
    # olt, onu, ont, router, switch, cmts
    device_model = Column(String(100), nullable=True)
    serial_number = Column(String(100), unique=True, nullable=False, index=True)
    mac_address = Column(String(17), nullable=True, index=True)
    ip_address = Column(INET, nullable=True, index=True)
    firmware_version = Column(String(50), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True, index=True)
    service_area_id = Column(UUID(as_uuid=True), ForeignKey("service_areas.id"), nullable=True)
    olt_id = Column(UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=True)
    pon_port = Column(String(20), nullable=True)
    onu_id = Column(Integer, nullable=True)
    pppoe_username = Column(String(100), nullable=True, index=True)
    status = Column(String(20), default="offline", nullable=False, index=True)
    # online, offline, degraded, maintenance
    last_seen_at = Column(DateTime, nullable=True)
    rx_power_dbm = Column(Numeric(5, 2), nullable=True)
    tx_power_dbm = Column(Numeric(5, 2), nullable=True)
    signal_quality = Column(String(20), nullable=True)
    # good, weak, critical, los
    uptime_seconds = Column(BigInteger, default=0, nullable=False)
    installed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    customer = relationship("Customer", back_populates="devices")


class DeviceMetric(Base):
    """TimescaleDB hypertable: partitioned by `time` column."""
    __tablename__ = "device_metrics"

    time = Column(DateTime, nullable=False, primary_key=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=False, primary_key=True)
    rx_power_dbm = Column(Numeric(5, 2), nullable=True)
    tx_power_dbm = Column(Numeric(5, 2), nullable=True)
    bandwidth_down_mbps = Column(Numeric(10, 2), nullable=True)
    bandwidth_up_mbps = Column(Numeric(10, 2), nullable=True)
    latency_ms = Column(Numeric(8, 2), nullable=True)
    packet_loss_percent = Column(Numeric(5, 2), nullable=True)
    uptime_seconds = Column(BigInteger, nullable=True)
    session_count = Column(Integer, nullable=True)
    temperature_celsius = Column(Numeric(5, 2), nullable=True)


class NetworkOutage(Base):
    __tablename__ = "network_outages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    outage_type = Column(String(50), default="unplanned", nullable=False)
    # planned, unplanned, partial, full
    severity = Column(String(20), default="medium", nullable=False, index=True)
    # low, medium, high, critical
    affected_device_id = Column(UUID(as_uuid=True), ForeignKey("network_devices.id"), nullable=True)
    affected_area_id = Column(UUID(as_uuid=True), ForeignKey("service_areas.id"), nullable=True)
    affected_customer_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="detected", nullable=False, index=True)
    # detected, investigating, mitigating, resolved
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    estimated_resolution = Column(DateTime, nullable=True)
    root_cause = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
