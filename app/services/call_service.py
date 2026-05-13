"""
DishHome AI Voice Bot - Call Service
Business logic for managing call records.
"""

import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.call import CallRecord
from app.models.database import async_session


class CallService:
    """Service layer for call record CRUD operations."""

    async def create_call(self, session_id: str, language: str = "en",
                          customer_phone: Optional[str] = None) -> CallRecord:
        async with async_session() as db:
            record = CallRecord(
                session_id=session_id,
                language=language,
                customer_phone=customer_phone,
                status="active",
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            logger.info(f"Created call record: {session_id}")
            return record

    async def end_call(self, session_id: str, transcript: list,
                       turn_count: int, duration: float) -> Optional[CallRecord]:
        async with async_session() as db:
            result = await db.execute(
                select(CallRecord).where(CallRecord.session_id == session_id)
            )
            record = result.scalar_one_or_none()
            if record:
                record.status = "completed"
                record.ended_at = datetime.datetime.utcnow()
                record.duration_seconds = duration
                record.turn_count = turn_count
                record.transcript = transcript
                await db.commit()
                logger.info(f"Ended call: {session_id} ({duration:.1f}s)")
            return record

    async def get_call(self, session_id: str) -> Optional[CallRecord]:
        async with async_session() as db:
            result = await db.execute(
                select(CallRecord).where(CallRecord.session_id == session_id)
            )
            return result.scalar_one_or_none()

    async def list_calls(self, limit: int = 50, offset: int = 0,
                         status: Optional[str] = None) -> list[CallRecord]:
        async with async_session() as db:
            query = select(CallRecord).order_by(CallRecord.created_at.desc())
            if status:
                query = query.where(CallRecord.status == status)
            query = query.limit(limit).offset(offset)
            result = await db.execute(query)
            return list(result.scalars().all())

    async def get_dashboard_metrics(self) -> dict:
        async with async_session() as db:
            total = await db.scalar(select(func.count(CallRecord.id)))
            active = await db.scalar(
                select(func.count(CallRecord.id)).where(CallRecord.status == "active")
            )
            completed = await db.scalar(
                select(func.count(CallRecord.id)).where(CallRecord.status == "completed")
            )
            handoff = await db.scalar(
                select(func.count(CallRecord.id)).where(CallRecord.status == "handoff")
            )
            avg_dur = await db.scalar(
                select(func.avg(CallRecord.duration_seconds)).where(
                    CallRecord.duration_seconds > 0
                )
            )
            avg_turns = await db.scalar(
                select(func.avg(CallRecord.turn_count)).where(
                    CallRecord.turn_count > 0
                )
            )
            nepali = await db.scalar(
                select(func.count(CallRecord.id)).where(CallRecord.language == "ne")
            )
            english = await db.scalar(
                select(func.count(CallRecord.id)).where(CallRecord.language == "en")
            )
            resolved = await db.scalar(
                select(func.count(CallRecord.id)).where(CallRecord.resolved == True)
            )

            return {
                "total_calls": total or 0,
                "active_calls": active or 0,
                "completed_calls": completed or 0,
                "handoff_calls": handoff or 0,
                "avg_duration": round(avg_dur or 0, 1),
                "avg_turns": round(avg_turns or 0, 1),
                "nepali_calls": nepali or 0,
                "english_calls": english or 0,
                "resolution_rate": round(
                    (resolved / total * 100) if total else 0, 1
                ),
            }


call_service = CallService()
