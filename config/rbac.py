"""
Role-Based Access Control (RBAC) permission matrix.
Defines which roles have access to which resources and actions.
"""

from typing import Dict, List, Set

# Permission format: "resource:action"
# "*:*" means wildcard (all resources, all actions)
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "superadmin": ["*:*"],
    "admin": [
        "customers:read", "customers:write", "customers:delete",
        "tickets:read", "tickets:write", "tickets:delete", "tickets:escalate",
        "billing:read", "billing:write",
        "network:read", "network:write",
        "vendors:read", "vendors:write",
        "users:read", "users:write",
        "roles:read",
        "analytics:read",
        "audit_logs:read",
        "system_config:read",
        "ai_settings:read",
        "packages:read", "packages:write",
        "calls:read",
        "faqs:read", "faqs:write", "faqs:delete",
        "agent:read",
    ],
    "support_agent": [
        "customers:read",
        "tickets:read", "tickets:write", "tickets:escalate",
        "billing:read",
        "network:read",
        "calls:read", "calls:write",
        "packages:read",
        "faqs:read",
        "agent:read", "agent:write",
        "analytics:read",
    ],
    "technician": [
        "tickets:read", "tickets:update_status",
        "network:read", "network:write",
        "customers:read",
        "agent:read",
    ],
    "customer": [
        "portal:read", "portal:write",
    ],
}

# SLA response deadlines by ticket priority (in hours)
SLA_HOURS: Dict[str, int] = {
    "critical": 4,
    "high": 8,
    "medium": 24,
    "low": 72,
}

# Ticket categories and subcategories
TICKET_CATEGORIES = {
    "connectivity": ["no_internet", "slow_speed", "wifi_issue", "pppoe_issue", "los_signal"],
    "billing": ["payment_issue", "invoice_query", "package_renewal", "overcharge", "refund"],
    "hardware": ["router_faulty", "ont_issue", "cable_damage", "device_replacement"],
    "new_connection": ["residential", "commercial", "relocation"],
    "inquiry": ["package_info", "coverage_check", "service_hours", "general"],
}

# Customer loyalty tiers and their upgrade thresholds (months of active service)
LOYALTY_TIERS = {
    "bronze": {"min_months": 0, "discount_percent": 0},
    "silver": {"min_months": 6, "discount_percent": 5},
    "gold": {"min_months": 12, "discount_percent": 8},
    "platinum": {"min_months": 24, "discount_percent": 12},
}

# VAT rate for Nepal
VAT_PERCENT = 13.0

# Network thresholds for outage detection
OUTAGE_THRESHOLD_PERCENT = 30  # If >30% ONUs in area are offline → outage

# Signal quality thresholds (dBm)
SIGNAL_QUALITY = {
    "good": {"min": -25.0, "max": -8.0},
    "weak": {"min": -28.0, "max": -25.0},
    "critical": {"min": -30.0, "max": -28.0},
    "los": {"threshold": -30.0},  # Loss of Signal
}


def get_role_permissions(role_name: str) -> Set[str]:
    """Return the set of permissions for a given role name."""
    perms = ROLE_PERMISSIONS.get(role_name, [])
    if "*:*" in perms:
        return {"*:*"}
    return set(perms)


def has_permission(role_permissions: Set[str], resource: str, action: str) -> bool:
    """Check if a set of permissions allows a resource:action."""
    if "*:*" in role_permissions:
        return True
    if f"{resource}:{action}" in role_permissions:
        return True
    if f"{resource}:*" in role_permissions:
        return True
    return False
