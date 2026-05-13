from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from loguru import logger

router = APIRouter(prefix="/api/admin", tags=["admin"])

FAQ_FILE = "app/knowledge/dishhome_faq.json"

class FAQEntry(BaseModel):
    category: str
    keywords: List[str]
    question_en: str
    question_ne: str
    answer_en: str
    answer_ne: str

class FAQList(BaseModel):
    faqs: List[FAQEntry]

def _read_faqs():
    if not os.path.exists(FAQ_FILE):
        return {"faqs": []}
    with open(FAQ_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _write_faqs(data):
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@router.get("/faqs", response_model=FAQList)
async def get_faqs():
    """Get all FAQs for the admin dashboard."""
    try:
        return _read_faqs()
    except Exception as e:
        logger.error(f"Error reading FAQs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/faqs")
async def add_faq(faq: FAQEntry):
    """Add a new FAQ."""
    try:
        data = _read_faqs()
        data["faqs"].append(faq.model_dump())
        _write_faqs(data)
        return {"status": "success", "message": "FAQ added successfully"}
    except Exception as e:
        logger.error(f"Error adding FAQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/faqs/{index}")
async def update_faq(index: int, faq: FAQEntry):
    """Update an existing FAQ."""
    try:
        data = _read_faqs()
        if index < 0 or index >= len(data["faqs"]):
            raise HTTPException(status_code=404, detail="FAQ not found")
        data["faqs"][index] = faq.model_dump()
        _write_faqs(data)
        return {"status": "success", "message": "FAQ updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating FAQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/faqs/{index}")
async def delete_faq(index: int):
    """Delete an FAQ."""
    try:
        data = _read_faqs()
        if index < 0 or index >= len(data["faqs"]):
            raise HTTPException(status_code=404, detail="FAQ not found")
        data["faqs"].pop(index)
        _write_faqs(data)
        return {"status": "success", "message": "FAQ deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting FAQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# In-memory users for demo
USERS_DB = [
    {"id": 1, "name": "Super Admin User", "role": "Super Admin", "status": "Active"},
    {"id": 2, "name": "Rajan Agent", "role": "Agent", "status": "Active"},
    {"id": 3, "name": "Support Manager", "role": "Manager", "status": "Offline"},
]

class UserEntry(BaseModel):
    name: str
    role: str
    status: str

@router.get("/users")
async def get_users():
    return {"users": USERS_DB}

@router.post("/users")
async def add_user(user: UserEntry):
    new_id = max([u["id"] for u in USERS_DB] + [0]) + 1
    new_user = {"id": new_id, "name": user.name, "role": user.role, "status": user.status}
    USERS_DB.append(new_user)
    return {"status": "success", "message": "User added"}

@router.put("/users/{user_id}")
async def update_user(user_id: int, user: UserEntry):
    for u in USERS_DB:
        if u["id"] == user_id:
            u["name"] = user.name
            u["role"] = user.role
            u["status"] = user.status
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="User not found")

@router.delete("/users/{user_id}")
async def delete_user(user_id: int):
    global USERS_DB
    USERS_DB = [u for u in USERS_DB if u["id"] != user_id]
    return {"status": "success"}

# Mock data for dashboard
MOCK_VENDORS = [
    {"area": "Kathmandu-01", "vendor": "Subisu Tech", "tech": "Ram Sharma", "status": "Active"},
    {"area": "Lalitpur-05", "vendor": "WorldLink Support", "tech": "Shyam Thapa", "status": "Active"}
]

MOCK_TICKETS = [
    {"id": "TK-8832", "customer": "9841999999", "issue": "Signal Issue (LOS)", "status": "Open"}
]

@router.get("/dashboard/stats")
async def get_stats():
    return {
        "active_calls": 5,
        "online_agents": 12,
        "open_tickets": len(MOCK_TICKETS),
        "avg_wait_time": "12s"
    }

@router.get("/vendors")
async def get_vendors():
    return {"vendors": MOCK_VENDORS}

@router.get("/tickets")
async def get_tickets():
    return {"tickets": MOCK_TICKETS}
