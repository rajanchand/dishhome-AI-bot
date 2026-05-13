"""
LLM function/tool call dispatcher.

Maps LLM-emitted tool calls to actual service-layer methods, providing the
"hands and eyes" of the AI agent. Also encodes the 6 automated ISP workflows
via thin orchestration helpers callable from llm_engine.
"""

import random
import re
import string
from datetime import datetime, date
from typing import Any, Optional
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AsyncSessionLocal, Customer, NetworkDevice, Ticket, Package, ServiceArea, CustomerPackage,
)
from app.services.cache_service import cache_service
from app.services.customer_service import customer_service
from app.services.network_service import network_service
from app.services.router_service import router_service
from app.services.ticket_service import ticket_service
from app.services.package_service import package_service
from app.services.search_service import search_service
from app.services.notification_service import notification_service
from app.services.knowledge_base import KnowledgeBase
from app.services.vendor_service import vendor_service


def _gen_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


class FunctionCaller:
    """Dispatches LLM tool calls to real service methods."""

    def __init__(self) -> None:
        self.knowledge_base: Optional[KnowledgeBase] = None
        self._init_handlers()

    def _init_handlers(self):
        self.TOOL_MAP = {
            "get_customer_profile": self._get_customer_profile,
            "verify_customer_identity": self._verify_customer_identity,
            "send_otp_to_customer": self._send_otp_to_customer,
            "verify_otp": self._verify_otp,
            "update_customer_contact": self._update_customer_contact,
            "log_interaction": self._log_interaction,
            "get_complaint_history": self._get_complaint_history,
            "check_network_status": self._check_network_status,
            "check_area_outage": self._check_area_outage,
            "check_pppoe_session": self._check_pppoe_session,
            "get_signal_diagnostics": self._get_signal_diagnostics,
            "get_speed_test_data": self._get_speed_test_data,
            "get_bandwidth_usage": self._get_bandwidth_usage,
            "check_mac_registration": self._check_mac_registration,
            "reboot_customer_device": self._reboot_customer_device,
            "get_noc_alerts": self._get_noc_alerts,
            "get_billing_status": self._get_billing_status,
            "send_payment_reminder": self._send_payment_reminder,
            "get_package_info": self._get_package_info,
            "upgrade_package": self._upgrade_package,
            "get_renewal_options": self._get_renewal_options,
            "get_service_availability": self._get_service_availability,
            "create_support_ticket": self._create_support_ticket,
            "get_existing_tickets": self._get_existing_tickets,
            "escalate_ticket_priority": self._escalate_ticket_priority,
            "schedule_technician_visit": self._schedule_technician_visit,
            "get_technician_availability": self._get_technician_availability,
            "register_new_connection_lead": self._register_new_connection_lead,
            "request_human_agent": self._request_human_agent,
            "search_knowledge_base": self._search_knowledge_base,
        }

    async def call(self, name: str, arguments: dict, db: Optional[AsyncSession] = None) -> dict:
        handler = self.TOOL_MAP.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            if db is None:
                async with AsyncSessionLocal() as session:
                    result = await handler(session, **arguments)
            else:
                result = await handler(db, **arguments)
            return result if isinstance(result, dict) else {"result": result}
        except TypeError as e:
            return {"error": f"Invalid arguments for {name}: {e}"}
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"error": str(e), "tool": name}

    # ── Identity & CRM ────────────────────────────────────────────────────

    async def _get_customer_profile(self, db: AsyncSession, identifier: str, identifier_type: str) -> dict:
        if identifier_type == "phone":
            customer = await customer_service.get_customer_by_phone(db, identifier)
        else:
            customer = await customer_service.get_customer_by_code(db, identifier)
        if customer is None:
            return {"found": False, "message": "Customer not found"}
        return {"found": True, **(await customer_service.get_customer_360(db, customer.id) or {})}

    async def _verify_customer_identity(self, db: AsyncSession, customer_id: str,
                                          verification_type: str, verification_value: str) -> dict:
        customer = await customer_service.get_customer(db, UUID(customer_id))
        if customer is None:
            return {"verified": False}
        ok = False
        if verification_type == "phone_match":
            ok = (verification_value in {customer.phone_primary, customer.phone_secondary})
        elif verification_type == "dob":
            if customer.date_of_birth:
                ok = customer.date_of_birth.strftime("%Y-%m-%d") == verification_value
        elif verification_type == "address":
            for addr in customer.addresses:
                if verification_value.lower() in (addr.street_address or "").lower():
                    ok = True
                    break
        return {"verified": ok}

    async def _send_otp_to_customer(self, db: AsyncSession, customer_id: str, purpose: str) -> dict:
        customer = await customer_service.get_customer(db, UUID(customer_id))
        if customer is None:
            return {"sent": False, "reason": "Customer not found"}
        otp = _gen_otp()
        key = f"{customer_id}:{purpose}"
        await cache_service.store_otp(key, otp, ttl=300)
        await notification_service.send_sms(
            customer.phone_primary,
            f"Your DishHome OTP for {purpose} is: {otp}. Valid for 5 minutes.",
        )
        return {"sent": True, "expires_in": 300}

    async def _verify_otp(self, db: AsyncSession, customer_id: str, otp: str, purpose: str) -> dict:
        ok = await cache_service.verify_otp_stored(f"{customer_id}:{purpose}", otp)
        return {"verified": ok}

    async def _update_customer_contact(self, db: AsyncSession, customer_id: str,
                                         field: str, new_value: str) -> dict:
        customer = await customer_service.update_customer(db, UUID(customer_id), {field: new_value})
        if customer is None:
            return {"updated": False}
        return {"updated": True, "field": field, "new_value": new_value}

    async def _log_interaction(self, db: AsyncSession, customer_id: str,
                                interaction_type: str, summary: str, outcome: str) -> dict:
        await customer_service.log_interaction(
            db, UUID(customer_id), interaction_type, summary, outcome,
        )
        return {"logged": True}

    async def _get_complaint_history(self, db: AsyncSession, customer_id: str, limit: int = 5) -> dict:
        items, _ = await ticket_service.list_tickets(
            db, customer_id=UUID(customer_id), limit=limit,
        )
        return {
            "tickets": [
                {
                    "ticket_number": t.ticket_number, "category": t.category,
                    "priority": t.priority, "status": t.status,
                    "created_at": t.created_at.isoformat(),
                }
                for t in items
            ]
        }

    # ── Network ──────────────────────────────────────────────────────────

    async def _check_network_status(self, db: AsyncSession, customer_id: str) -> dict:
        result = await db.execute(
            select(NetworkDevice).where(
                NetworkDevice.customer_id == UUID(customer_id),
                NetworkDevice.device_type == "onu",
            )
        )
        device = result.scalar_one_or_none()
        if device is None:
            return {"status": "no_device", "message": "No registered ONU"}
        live = await router_service.get_onu_status(db, device.id)
        return live

    async def _check_area_outage(self, db: AsyncSession, customer_id: str) -> dict:
        outage = await network_service.get_customer_area_outage(db, UUID(customer_id))
        if outage is None:
            return {"has_outage": False}
        return {
            "has_outage": True,
            "outage_id": str(outage.id),
            "title": outage.title,
            "severity": outage.severity,
            "estimated_resolution": outage.estimated_resolution.isoformat() if outage.estimated_resolution else None,
        }

    async def _check_pppoe_session(self, db: AsyncSession, customer_id: str) -> dict:
        device = (await db.execute(
            select(NetworkDevice).where(
                NetworkDevice.customer_id == UUID(customer_id),
                NetworkDevice.device_type == "onu",
            )
        )).scalar_one_or_none()
        if device is None or not device.pppoe_username:
            return {"active": False, "reason": "No PPPoE username"}
        return await router_service.get_pppoe_session(db, device.pppoe_username)

    async def _get_signal_diagnostics(self, db: AsyncSession, customer_id: str) -> dict:
        device = (await db.execute(
            select(NetworkDevice).where(
                NetworkDevice.customer_id == UUID(customer_id),
                NetworkDevice.device_type == "onu",
            )
        )).scalar_one_or_none()
        if device is None:
            return {"available": False}
        return {
            "available": True,
            "rx_power_dbm": float(device.rx_power_dbm) if device.rx_power_dbm is not None else None,
            "tx_power_dbm": float(device.tx_power_dbm) if device.tx_power_dbm is not None else None,
            "signal_quality": device.signal_quality,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
            "issue": "los" if device.signal_quality == "los" else None,
        }

    async def _get_speed_test_data(self, db: AsyncSession, customer_id: str) -> dict:
        return {
            "available": False,
            "message": "No recent speed test on file. Customer can run one at portal.dishhome.com.np/speed-test",
        }

    async def _get_bandwidth_usage(self, db: AsyncSession, customer_id: str, period: str = "this_month") -> dict:
        # Stub: query last device_metrics rows to estimate
        history = await network_service.get_device_history(db, UUID(customer_id), hours=24 * 30)
        if not history:
            return {"period": period, "data_points": 0}
        return {
            "period": period,
            "data_points": len(history),
            "sample": history[-5:],
        }

    async def _check_mac_registration(self, db: AsyncSession, mac_address: str) -> dict:
        device = (await db.execute(
            select(NetworkDevice).where(NetworkDevice.mac_address == mac_address.upper())
        )).scalar_one_or_none()
        if device is None:
            return {"registered": False}
        customer = await customer_service.get_customer(db, device.customer_id) if device.customer_id else None
        return {
            "registered": True,
            "device_serial": device.serial_number,
            "customer_id": str(device.customer_id) if device.customer_id else None,
            "customer_name": customer.full_name if customer else None,
        }

    async def _reboot_customer_device(self, db: AsyncSession, customer_id: str, reason: str) -> dict:
        # OTP gate
        if not await cache_service.get(f"otp:verified:{customer_id}:reboot"):
            return {
                "rebooted": False,
                "requires_otp": True,
                "message": "OTP verification required before reboot.",
            }
        device = (await db.execute(
            select(NetworkDevice).where(
                NetworkDevice.customer_id == UUID(customer_id),
                NetworkDevice.device_type == "onu",
            )
        )).scalar_one_or_none()
        if device is None:
            return {"rebooted": False, "reason": "No device"}
        ok = await router_service.reboot_onu(db, device.id)
        return {"rebooted": ok, "reason": reason}

    async def _get_noc_alerts(self, db: AsyncSession, severity_filter: str = "all", limit: int = 10) -> dict:
        outages = await network_service.list_outages(db, active_only=True)
        if severity_filter != "all":
            outages = [o for o in outages if o.severity == severity_filter]
        return {
            "alerts": [
                {
                    "id": str(o.id), "title": o.title, "severity": o.severity,
                    "status": o.status, "detected_at": o.detected_at.isoformat(),
                }
                for o in outages[:limit]
            ]
        }

    # ── Billing & Packages ───────────────────────────────────────────────

    async def _get_billing_status(self, db: AsyncSession, customer_id: str,
                                    include_history: bool = False) -> dict:
        profile = await customer_service.get_customer_360(db, UUID(customer_id))
        if profile is None:
            return {"error": "Customer not found"}
        return {
            "outstanding_invoices": profile.get("outstanding_invoices", []),
            "active_subscription": profile.get("active_subscription"),
        }

    async def _send_payment_reminder(self, db: AsyncSession, customer_id: str,
                                       invoice_id: Optional[str] = None) -> dict:
        customer = await customer_service.get_customer(db, UUID(customer_id))
        if customer is None:
            return {"sent": False}
        await notification_service.send_sms(
            customer.phone_primary,
            "DishHome: Your bill is due. Pay via eSewa, Khalti, ConnectIPS or bank.",
        )
        return {"sent": True}

    async def _get_package_info(self, db: AsyncSession,
                                  package_id: Optional[str] = None,
                                  list_all: bool = False) -> dict:
        if list_all or package_id is None:
            pkgs = await package_service.list_packages(db, active_only=True)
            return {
                "packages": [
                    {
                        "id": str(p.id), "code": p.package_code, "name": p.name,
                        "speed_down_mbps": p.speed_download_mbps,
                        "speed_up_mbps": p.speed_upload_mbps,
                        "price_monthly": float(p.price_monthly),
                    }
                    for p in pkgs
                ]
            }
        pkg = await package_service.get_package(db, UUID(package_id))
        if pkg is None:
            return {"error": "Package not found"}
        return {
            "id": str(pkg.id), "name": pkg.name, "speed": pkg.speed_download_mbps,
            "price_monthly": float(pkg.price_monthly),
            "price_annually": float(pkg.price_annually) if pkg.price_annually else None,
        }

    async def _upgrade_package(self, db: AsyncSession, customer_id: str, new_package_id: str) -> dict:
        if not await cache_service.get(f"otp:verified:{customer_id}:package_change"):
            return {"upgraded": False, "requires_otp": True}
        active_sub = (await db.execute(
            select(CustomerPackage).where(
                CustomerPackage.customer_id == UUID(customer_id),
                CustomerPackage.status == "active",
            )
        )).scalar_one_or_none()
        if active_sub is None:
            return {"upgraded": False, "reason": "No active subscription"}
        new_sub = await package_service.upgrade_subscription(db, active_sub.id, UUID(new_package_id))
        return {"upgraded": True, "new_subscription_id": str(new_sub.id)}

    async def _get_renewal_options(self, db: AsyncSession, customer_id: str) -> dict:
        pkgs = await package_service.list_packages(db, active_only=True)
        return {
            "options": [
                {"id": str(p.id), "name": p.name, "price_monthly": float(p.price_monthly),
                 "price_annually": float(p.price_annually) if p.price_annually else None}
                for p in pkgs[:5]
            ]
        }

    async def _get_service_availability(self, db: AsyncSession, municipality: str,
                                          ward: Optional[str] = None) -> dict:
        result = await db.execute(
            select(ServiceArea).where(
                ServiceArea.municipality.ilike(f"%{municipality}%"),
                ServiceArea.is_active == True,  # noqa
            )
        )
        areas = list(result.scalars())
        return {"available": bool(areas), "matched_areas": [a.area_code for a in areas]}

    # ── Tickets ──────────────────────────────────────────────────────────

    async def _create_support_ticket(self, db: AsyncSession, customer_id: str, category: str,
                                       priority: str, title: str, description: str,
                                       field_visit_required: bool = False) -> dict:
        """Creates a ticket and auto-assigns vendor if needed."""
        # 1. Fetch customer to get service area
        customer = await customer_service.get_customer(db, UUID(customer_id))
        vendor_id = None
        if customer and field_visit_required:
            # 2. Get service area from primary address
            primary_addr = next((a for a in customer.addresses if a.is_primary), None)
            if primary_addr and primary_addr.service_area_id:
                # 3. Find best vendor for this area
                vendor = await vendor_service.get_vendor_by_area(db, primary_addr.service_area_id)
                if vendor:
                    vendor_id = vendor.id
                    logger.info(f"Auto-assigned vendor {vendor.company_name} to ticket for area {primary_addr.service_area_id}")

        ticket = await ticket_service.create_ticket(db, {
            "customer_id": UUID(customer_id), "category": category, "priority": priority,
            "title": title, "description": description,
            "field_visit_required": field_visit_required,
            "assigned_vendor_id": vendor_id,
        }, created_by_ai=True)
        return {
            "ticket_id": str(ticket.id), "ticket_number": ticket.ticket_number,
            "sla_deadline": ticket.sla_deadline.isoformat(),
            "assigned_vendor": vendor_id and str(vendor_id),
        }

    async def _get_existing_tickets(self, db: AsyncSession, customer_id: str,
                                      status_filter: Optional[list] = None) -> dict:
        statuses = status_filter or ["open", "in_progress"]
        items, _ = await ticket_service.list_tickets(
            db, customer_id=UUID(customer_id), limit=10,
        )
        filtered = [t for t in items if t.status in statuses]
        return {
            "tickets": [
                {"ticket_id": str(t.id), "ticket_number": t.ticket_number,
                 "status": t.status, "priority": t.priority, "title": t.title}
                for t in filtered
            ]
        }

    async def _escalate_ticket_priority(self, db: AsyncSession, ticket_id: str, reason: str) -> dict:
        ticket = await ticket_service.escalate_ticket(db, UUID(ticket_id), reason)
        if ticket is None:
            return {"escalated": False}
        return {"escalated": True, "new_priority": ticket.priority}

    async def _schedule_technician_visit(self, db: AsyncSession, customer_id: str, ticket_id: str,
                                           preferred_date: str, preferred_time_slot: str,
                                           issue_description: str = "") -> dict:
        scheduled = datetime.fromisoformat(preferred_date + "T09:00:00")
        await ticket_service.update_ticket(db, UUID(ticket_id), {
            "field_visit_required": True,
            "field_visit_scheduled_at": scheduled,
        })
        return {
            "scheduled": True, "ticket_id": ticket_id,
            "visit_date": preferred_date, "time_slot": preferred_time_slot,
        }

    async def _get_technician_availability(self, db: AsyncSession, area_id: str, date: str) -> dict:
        # Stub — real impl queries technician schedules
        return {
            "area_id": area_id, "date": date,
            "slots": [
                {"slot": "morning", "available": True, "available_count": 3},
                {"slot": "afternoon", "available": True, "available_count": 2},
                {"slot": "evening", "available": False, "available_count": 0},
            ],
        }

    async def _register_new_connection_lead(self, db: AsyncSession, full_name: str, phone: str,
                                              address: str, preferred_package_id: Optional[str] = None,
                                              notes: str = "") -> dict:
        # Create a "pending" customer + lead ticket
        customer = await customer_service.create_customer(db, {
            "full_name": full_name, "phone_primary": phone,
            "preferred_language": "ne",
            "address": {"street_address": address, "address_type": "installation"},
        })
        customer.account_status = "pending"
        await db.commit()
        ticket = await ticket_service.create_ticket(db, {
            "customer_id": customer.id, "category": "new_connection",
            "priority": "medium", "title": f"New connection lead: {full_name}",
            "description": f"Phone: {phone}\nAddress: {address}\nPreferred package: {preferred_package_id}\nNotes: {notes}",
        }, created_by_ai=True)
        return {
            "lead_registered": True, "customer_code": customer.customer_code,
            "ticket_number": ticket.ticket_number,
        }

    async def _request_human_agent(self, db: AsyncSession, session_id: str, reason: str,
                                     priority: str = "normal", summary: str = "") -> dict:
        await cache_service.publish_call_event("handoff_requested", {
            "session_id": session_id, "reason": reason,
            "priority": priority, "summary": summary,
            "requested_at": datetime.utcnow().isoformat(),
        })
        return {"queued": True, "estimated_wait_minutes": 2}

    async def _search_knowledge_base(self, db: AsyncSession, query: str, language: str = "ne") -> dict:
        # Try Elasticsearch first; fall back to KnowledgeBase JSON
        es_results = await search_service.search_faq(query, language=language, size=3)
        if es_results:
            return {"source": "elasticsearch", "results": es_results}
        if self.knowledge_base is None:
            return {"source": "none", "results": []}
        try:
            results = self.knowledge_base.search_faq(query, language=language)
            return {"source": "static", "results": results}
        except Exception as e:
            logger.warning(f"KB search failed: {e}")
            return {"source": "none", "results": []}


function_caller = FunctionCaller()
