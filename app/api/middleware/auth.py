"""
JWT + RBAC auth — replaces legacy HTTP Basic auth.
Re-exports the get_current_user / require_permission dependencies.
"""

from app.utils.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_role,
    oauth2_scheme,
)

# Legacy alias kept for backward-compatibility with existing routes
verify_agent = get_current_user

__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    "require_role",
    "oauth2_scheme",
    "verify_agent",
]
