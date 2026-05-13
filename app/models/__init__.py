"""Models package — explicit imports so Alembic discovers all tables."""

from app.models.database import Base, metadata, get_db, init_db, close_db, engine, AsyncSessionLocal, async_session
from app.models.user import User, Role, Permission, PortalUser, role_permissions
from app.models.customer import Customer, CustomerAddress, ServiceArea, ContactInteraction
from app.models.package import Package, CustomerPackage
from app.models.billing import Invoice, InvoiceItem, Payment
from app.models.network import NetworkDevice, DeviceMetric, NetworkOutage
from app.models.ticket import Ticket, TicketComment, TicketAttachment
from app.models.vendor import Vendor, VendorContract, RMARequest
from app.models.audit import AuditLog
from app.models.call import CallRecord

__all__ = [
    "Base", "metadata", "get_db", "init_db", "close_db", "engine", "AsyncSessionLocal", "async_session",
    "User", "Role", "Permission", "PortalUser", "role_permissions",
    "Customer", "CustomerAddress", "ServiceArea", "ContactInteraction",
    "Package", "CustomerPackage",
    "Invoice", "InvoiceItem", "Payment",
    "NetworkDevice", "DeviceMetric", "NetworkOutage",
    "Ticket", "TicketComment", "TicketAttachment",
    "Vendor", "VendorContract", "RMARequest",
    "AuditLog",
    "CallRecord",
]
