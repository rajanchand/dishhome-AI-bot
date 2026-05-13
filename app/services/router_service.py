import uuid
from typing import Dict, List, Optional
from loguru import logger

class HuaweiRouterService:
    """Mock service for Huawei Router API integration."""
    
    def __init__(self):
        # Mock database of customer routers
        # Key: Customer ID or Phone
        self.routers = {
            "9841234567": {"status": "online", "signal": "good", "rx_power": "-18dBm", "mac": "00:1A:2B:3C:4D:5E"},
            "9841112222": {"status": "offline", "signal": "lost", "rx_power": "N/A", "mac": "00:1A:2B:3C:4D:5F"},
            "9841999999": {"status": "online", "signal": "weak", "rx_power": "-32dBm", "mac": "00:1A:2B:3C:4D:60"} # red light / LOS
        }
        
        # Tickets DB
        self.tickets = {}

    def get_router_status(self, customer_identifier: str) -> Dict:
        """Fetch router status from Huawei OLT/API."""
        logger.info(f"Huawei API: Fetching status for {customer_identifier}")
        return self.routers.get(customer_identifier, {"status": "unknown"})

    def create_ticket(self, customer_identifier: str, issue_type: str, description: str) -> str:
        """Create a network issue ticket."""
        ticket_id = f"TK-{str(uuid.uuid4())[:8].upper()}"
        self.tickets[ticket_id] = {
            "customer": customer_identifier,
            "issue": issue_type,
            "description": description,
            "status": "open",
            "assigned_technician": None
        }
        logger.info(f"Huawei API: Created ticket {ticket_id} for {customer_identifier}")
        return ticket_id
        
    def check_existing_ticket(self, customer_identifier: str) -> Optional[Dict]:
        """Check if customer already has an open ticket."""
        for t_id, t in self.tickets.items():
            if t["customer"] == customer_identifier and t["status"] == "open":
                return {"ticket_id": t_id, **t}
        return None

    def close_ticket(self, ticket_id: str) -> bool:
        if ticket_id in self.tickets:
            self.tickets[ticket_id]["status"] = "closed"
            logger.info(f"Ticket {ticket_id} closed.")
            return True
        return False

router_service = HuaweiRouterService()
