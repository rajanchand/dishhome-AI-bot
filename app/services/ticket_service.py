"""
Enterprise ticketing service — SLA management, assignment, escalation, comments.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Ticket, TicketComment, TicketAttachment, Customer
from app.services.cache_service import cache_service


class TicketService:
    async def _generate_ticket_number(self, db: AsyncSession) -> str:
        year = datetime.utcnow().year
        result = await db.execute(
            select(func.count(Ticket.id)).where(Ticket.ticket_number.like(f"TK-{year}-%"))
        )
        count = (result.scalar() or 0) + 1
        return f"TK-{year}-{count:06d}"

    async def create_ticket(self, db: AsyncSession, data: dict,
                             created_by: Optional[UUID] = None,
                             created_by_ai: bool = False) -> Ticket:
        ticket = Ticket(
            id=uuid4(),
            ticket_number=await self._generate_ticket_number(db),
            customer_id=data["customer_id"],
            call_record_id=data.get("call_record_id"),
            category=data["category"],
            subcategory=data.get("subcategory"),
            priority=data.get("priority", "medium"),
            status="open",
            title=data["title"],
            description=data["description"],
            sla_deadline=Ticket.compute_sla_deadline(data.get("priority", "medium")),
            field_visit_required=data.get("field_visit_required", False),
            network_device_id=data.get("network_device_id"),
            created_by_user_id=created_by,
            created_by_ai=created_by_ai,
        )
        db.add(ticket)
        await db.commit()
        await db.refresh(ticket)
        await cache_service.publish_ticket_event("created", {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "customer_id": str(ticket.customer_id),
            "priority": ticket.priority,
            "title": ticket.title,
        })
        logger.info(f"Ticket created: {ticket.ticket_number} ({ticket.priority})")
        return ticket

    async def get_ticket(self, db: AsyncSession, ticket_id: UUID) -> Optional[Ticket]:
        stmt = (
            select(Ticket)
            .options(selectinload(Ticket.comments), selectinload(Ticket.attachments))
            .where(Ticket.id == ticket_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tickets(
        self, db: AsyncSession, offset: int = 0, limit: int = 50,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        agent_id: Optional[UUID] = None,
        customer_id: Optional[UUID] = None,
    ) -> tuple[list, int]:
        stmt = select(Ticket)
        count_stmt = select(func.count(Ticket.id))
        conditions = []
        if status_filter:
            conditions.append(Ticket.status == status_filter)
        if priority_filter:
            conditions.append(Ticket.priority == priority_filter)
        if agent_id:
            conditions.append(Ticket.assigned_agent_id == agent_id)
        if customer_id:
            conditions.append(Ticket.customer_id == customer_id)
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        stmt = stmt.order_by(desc(Ticket.created_at)).offset(offset).limit(limit)
        items = (await db.execute(stmt)).scalars().all()
        total = (await db.execute(count_stmt)).scalar() or 0
        return list(items), int(total)

    async def update_ticket(self, db: AsyncSession, ticket_id: UUID, data: dict) -> Optional[Ticket]:
        ticket = await self.get_ticket(db, ticket_id)
        if ticket is None:
            return None
        for k, v in data.items():
            if v is not None and hasattr(ticket, k):
                setattr(ticket, k, v)
        # If priority changed, recompute SLA
        if data.get("priority") and ticket.status not in {"resolved", "closed"}:
            ticket.sla_deadline = Ticket.compute_sla_deadline(ticket.priority, ticket.created_at)
            ticket.breached_sla = False
        ticket.updated_at = datetime.utcnow()
        await db.commit()
        await cache_service.publish_ticket_event("updated", {
            "ticket_id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
        })
        return ticket

    async def assign_agent(self, db: AsyncSession, ticket_id: UUID, agent_id: UUID) -> Optional[Ticket]:
        ticket = await self.update_ticket(db, ticket_id, {
            "assigned_agent_id": agent_id,
            "status": "in_progress",
        })
        return ticket

    async def assign_vendor(self, db: AsyncSession, ticket_id: UUID, vendor_id: UUID) -> Optional[Ticket]:
        return await self.update_ticket(db, ticket_id, {"assigned_vendor_id": vendor_id})

    async def add_comment(self, db: AsyncSession, ticket_id: UUID, content: str,
                           author_user_id: Optional[UUID] = None,
                           author_type: str = "agent",
                           is_internal: bool = False) -> TicketComment:
        comment = TicketComment(
            id=uuid4(),
            ticket_id=ticket_id,
            author_user_id=author_user_id,
            author_type=author_type,
            content=content,
            is_internal=is_internal,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment

    async def escalate_ticket(self, db: AsyncSession, ticket_id: UUID, reason: str) -> Optional[Ticket]:
        ticket = await self.get_ticket(db, ticket_id)
        if ticket is None:
            return None
        priority_ladder = ["low", "medium", "high", "critical"]
        current_idx = priority_ladder.index(ticket.priority) if ticket.priority in priority_ladder else 1
        new_priority = priority_ladder[min(current_idx + 1, len(priority_ladder) - 1)]
        ticket.priority = new_priority
        ticket.sla_deadline = Ticket.compute_sla_deadline(new_priority, datetime.utcnow())
        ticket.breached_sla = False
        await self.add_comment(
            db, ticket_id,
            content=f"Ticket escalated to {new_priority}: {reason}",
            author_type="system",
            is_internal=True,
        )
        await db.commit()
        await cache_service.publish_ticket_event("escalated", {
            "ticket_id": str(ticket.id),
            "new_priority": new_priority,
            "reason": reason,
        })
        return ticket

    async def resolve_ticket(self, db: AsyncSession, ticket_id: UUID,
                              resolution_notes: str,
                              agent_id: Optional[UUID] = None) -> Optional[Ticket]:
        ticket = await self.update_ticket(db, ticket_id, {
            "status": "resolved",
            "resolution_notes": resolution_notes,
            "resolved_at": datetime.utcnow(),
        })
        if ticket and agent_id:
            await self.add_comment(db, ticket_id, f"Resolved: {resolution_notes}",
                                    author_user_id=agent_id, author_type="agent")
        return ticket

    async def close_ticket(self, db: AsyncSession, ticket_id: UUID) -> Optional[Ticket]:
        return await self.update_ticket(db, ticket_id, {
            "status": "closed", "closed_at": datetime.utcnow(),
        })

    async def check_sla_breaches(self, db: AsyncSession) -> List[Ticket]:
        now = datetime.utcnow()
        stmt = (
            select(Ticket)
            .where(
                Ticket.status.notin_(["resolved", "closed"]),
                Ticket.sla_deadline < now,
                Ticket.breached_sla == False,  # noqa
            )
        )
        result = await db.execute(stmt)
        breached: List[Ticket] = list(result.scalars())
        for ticket in breached:
            ticket.breached_sla = True
            ticket.breached_at = now
            await cache_service.publish_ticket_event("sla_breach", {
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "priority": ticket.priority,
                "deadline": ticket.sla_deadline.isoformat(),
            })
            logger.warning(f"SLA breach: {ticket.ticket_number}")
        if breached:
            await db.commit()
        return breached

    async def get_sla_dashboard(self, db: AsyncSession) -> dict:
        now = datetime.utcnow()
        total = (await db.execute(select(func.count(Ticket.id)))).scalar() or 0
        open_count = (await db.execute(
            select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress"]))
        )).scalar() or 0
        breached = (await db.execute(
            select(func.count(Ticket.id)).where(Ticket.breached_sla == True)  # noqa
        )).scalar() or 0
        at_risk = (await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.status.in_(["open", "in_progress"]),
                Ticket.sla_deadline < now,
            )
        )).scalar() or 0
        return {
            "total_tickets": int(total),
            "open_tickets": int(open_count),
            "breached_sla": int(breached),
            "at_risk": int(at_risk),
            "compliance_rate": round(
                ((total - breached) / total * 100) if total else 100.0, 2
            ),
        }


ticket_service = TicketService()
