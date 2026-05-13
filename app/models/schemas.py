"""
Pydantic request/response schemas for all domains.
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Any
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal


# ════════════════════════════════════════════════════════════════════════════
# Voice / Chat (preserved from MVP)
# ════════════════════════════════════════════════════════════════════════════

class TextChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    language: Optional[str] = None


class TextChatResponse(BaseModel):
    session_id: str
    user_message: str
    response: str
    language: str
    has_audio: bool = False


class CallSummary(BaseModel):
    id: str
    session_id: str
    customer_id: Optional[str] = None
    customer_phone: Optional[str] = None
    language: str
    started_at: Optional[str]
    duration_seconds: float
    turn_count: int
    status: str
    resolved: bool


class DashboardMetrics(BaseModel):
    total_calls: int = 0
    active_calls: int = 0
    completed_calls: int = 0
    handoff_calls: int = 0
    avg_duration: float = 0.0
    avg_turns: float = 0.0
    nepali_calls: int = 0
    english_calls: int = 0
    resolution_rate: float = 0.0


class HealthStatus(BaseModel):
    status: str
    version: str = "2.0.0"
    stt_status: str = "unknown"
    tts_status: str = "unknown"
    llm_status: str = "unknown"
    database_status: str = "unknown"
    redis_status: str = "unknown"
    elasticsearch_status: str = "unknown"
    uptime_seconds: float = 0.0


# ════════════════════════════════════════════════════════════════════════════
# Auth
# ════════════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=200)
    otp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: str
    role: str
    requires_mfa: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)


class MFASetupResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: List[str] = []


class MFAVerifyRequest(BaseModel):
    otp_code: str = Field(..., min_length=6, max_length=6)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_name: str
    is_active: bool
    is_mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=12)
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_name: str = "support_agent"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role_name: Optional[str] = None
    is_active: Optional[bool] = None


# ════════════════════════════════════════════════════════════════════════════
# Customer
# ════════════════════════════════════════════════════════════════════════════

class AddressBase(BaseModel):
    address_type: str = "installation"
    street_address: str
    ward: Optional[str] = None
    municipality: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    service_area_id: Optional[UUID] = None
    is_primary: bool = False


class AddressResponse(AddressBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    customer_id: UUID
    created_at: datetime


class CustomerCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    phone_primary: str
    phone_secondary: Optional[str] = None
    email: Optional[EmailStr] = None
    national_id: Optional[str] = None
    date_of_birth: Optional[date] = None
    preferred_language: str = "ne"
    address: Optional[AddressBase] = None


class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[EmailStr] = None
    national_id: Optional[str] = None
    preferred_language: Optional[str] = None
    loyalty_tier: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_code: str
    full_name: str
    phone_primary: str
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    kyc_verified: bool
    account_status: str
    credit_score: int
    loyalty_tier: str
    preferred_language: str
    created_at: datetime
    updated_at: datetime


class Customer360(CustomerResponse):
    """Full Customer 360° profile."""
    addresses: List[AddressResponse] = []
    active_subscription: Optional[dict] = None
    devices: List[dict] = []
    recent_tickets: List[dict] = []
    recent_calls: List[dict] = []
    outstanding_invoices: List[dict] = []


# ════════════════════════════════════════════════════════════════════════════
# Package & Billing
# ════════════════════════════════════════════════════════════════════════════

class PackageBase(BaseModel):
    package_code: str
    name: str
    description: Optional[str] = None
    service_type: str = "fiber"
    speed_download_mbps: int
    speed_upload_mbps: int
    monthly_quota_gb: Optional[int] = None
    validity_days: int = 30
    price_monthly: Decimal
    price_quarterly: Optional[Decimal] = None
    price_annually: Optional[Decimal] = None
    setup_fee: Decimal = Decimal("0")
    is_active: bool = True


class PackageCreate(PackageBase):
    pass


class PackageResponse(PackageBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    invoice_number: str
    customer_id: UUID
    billing_period_start: date
    billing_period_end: date
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    due_date: date
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime


class PaymentCreate(BaseModel):
    invoice_id: UUID
    amount: Decimal
    payment_method: str
    gateway_transaction_id: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# Network
# ════════════════════════════════════════════════════════════════════════════

class NetworkDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    device_type: str
    serial_number: str
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    rx_power_dbm: Optional[Decimal] = None
    tx_power_dbm: Optional[Decimal] = None
    signal_quality: Optional[str] = None
    uptime_seconds: int
    last_seen_at: Optional[datetime] = None


class OutageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    severity: str
    status: str
    affected_customer_count: int
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    estimated_resolution: Optional[datetime] = None


# ════════════════════════════════════════════════════════════════════════════
# Ticket
# ════════════════════════════════════════════════════════════════════════════

class TicketCreate(BaseModel):
    customer_id: UUID
    category: str
    subcategory: Optional[str] = None
    priority: str = "medium"
    title: str = Field(..., max_length=500)
    description: str
    field_visit_required: bool = False
    call_record_id: Optional[UUID] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent_id: Optional[UUID] = None
    assigned_vendor_id: Optional[UUID] = None
    field_visit_required: Optional[bool] = None
    field_visit_scheduled_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class TicketCommentCreate(BaseModel):
    content: str
    is_internal: bool = False


class TicketCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ticket_id: UUID
    author_user_id: Optional[UUID] = None
    author_type: str
    content: str
    is_internal: bool
    created_at: datetime


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ticket_number: str
    customer_id: UUID
    category: str
    subcategory: Optional[str] = None
    priority: str
    status: str
    title: str
    description: str
    sla_deadline: datetime
    breached_sla: bool
    assigned_agent_id: Optional[UUID] = None
    field_visit_required: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ════════════════════════════════════════════════════════════════════════════
# Vendor
# ════════════════════════════════════════════════════════════════════════════

class VendorCreate(BaseModel):
    vendor_code: str
    company_name: str
    vendor_type: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    address: Optional[str] = None
    sla_response_hours: int = 4
    sla_resolution_hours: int = 24


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vendor_code: str
    company_name: str
    vendor_type: str
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    rating: Decimal
    is_active: bool
    created_at: datetime


# ════════════════════════════════════════════════════════════════════════════
# Pagination wrapper
# ════════════════════════════════════════════════════════════════════════════

class Paginated(BaseModel):
    items: List[Any]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False
