"""
DishHome AI Voice Bot - Auth Middleware
Basic authentication for agent dashboard.
"""

import secrets
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from config.settings import settings

security = HTTPBasic()


async def verify_agent(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify agent credentials for dashboard access."""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        settings.agent_username.encode("utf8"),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        settings.agent_password.encode("utf8"),
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
