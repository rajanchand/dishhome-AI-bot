"""
Network service — device polling, outage detection, health map, area status.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    NetworkDevice, DeviceMetric, NetworkOutage, ServiceArea, Customer,
)
from app.services.cache_service import cache_service
from app.services.router_service import router_service
from config.rbac import OUTAGE_THRESHOLD_PERCENT


class NetworkService:
    async def list_devices(
        self, db: AsyncSession, device_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        offset: int = 0, limit: int = 100,
    ) -> tuple[list, int]:
        stmt = select(NetworkDevice)
        count_stmt = select(func.count(NetworkDevice.id))
        conds = []
        if device_type:
            conds.append(NetworkDevice.device_type == device_type)
        if status_filter:
            conds.append(NetworkDevice.status == status_filter)
        if conds:
            stmt = stmt.where(and_(*conds))
            count_stmt = count_stmt.where(and_(*conds))
        stmt = stmt.order_by(desc(NetworkDevice.last_seen_at)).offset(offset).limit(limit)
        items = list((await db.execute(stmt)).scalars())
        total = (await db.execute(count_stmt)).scalar() or 0
        return items, int(total)

    async def get_device(self, db: AsyncSession, device_id: UUID) -> Optional[NetworkDevice]:
        return (await db.execute(
            select(NetworkDevice).where(NetworkDevice.id == device_id)
        )).scalar_one_or_none()

    async def get_device_history(
        self, db: AsyncSession, device_id: UUID, hours: int = 24,
    ) -> List[dict]:
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await db.execute(
            select(DeviceMetric).where(
                DeviceMetric.device_id == device_id,
                DeviceMetric.time >= since,
            ).order_by(DeviceMetric.time)
        )
        return [
            {
                "time": m.time.isoformat(),
                "rx_power_dbm": float(m.rx_power_dbm) if m.rx_power_dbm is not None else None,
                "tx_power_dbm": float(m.tx_power_dbm) if m.tx_power_dbm is not None else None,
                "bandwidth_down_mbps": float(m.bandwidth_down_mbps) if m.bandwidth_down_mbps is not None else None,
                "bandwidth_up_mbps": float(m.bandwidth_up_mbps) if m.bandwidth_up_mbps is not None else None,
                "latency_ms": float(m.latency_ms) if m.latency_ms is not None else None,
                "packet_loss_percent": float(m.packet_loss_percent) if m.packet_loss_percent is not None else None,
            }
            for m in result.scalars()
        ]

    async def detect_outage_for_area(self, db: AsyncSession, area_id: UUID) -> Optional[NetworkOutage]:
        """Create an outage record if >threshold% of ONUs in area are offline."""
        total = (await db.execute(
            select(func.count(NetworkDevice.id)).where(
                NetworkDevice.service_area_id == area_id,
                NetworkDevice.device_type == "onu",
            )
        )).scalar() or 0
        if total == 0:
            return None
        offline = (await db.execute(
            select(func.count(NetworkDevice.id)).where(
                NetworkDevice.service_area_id == area_id,
                NetworkDevice.device_type == "onu",
                NetworkDevice.status == "offline",
            )
        )).scalar() or 0
        ratio = (offline / total) * 100
        if ratio < OUTAGE_THRESHOLD_PERCENT:
            return None
        # Check if active outage already exists
        existing = (await db.execute(
            select(NetworkOutage).where(
                NetworkOutage.affected_area_id == area_id,
                NetworkOutage.status.notin_(["resolved"]),
            )
        )).scalar_one_or_none()
        if existing:
            return existing
        area = (await db.execute(select(ServiceArea).where(ServiceArea.id == area_id))).scalar_one()
        outage = NetworkOutage(
            id=uuid4(),
            title=f"Auto-detected outage in {area.area_name}",
            description=f"{offline}/{total} ONUs offline ({ratio:.1f}%)",
            outage_type="unplanned",
            severity="high" if ratio < 70 else "critical",
            affected_area_id=area_id,
            affected_customer_count=offline,
            status="detected",
            detected_at=datetime.utcnow(),
        )
        db.add(outage)
        await db.commit()
        await db.refresh(outage)
        await cache_service.publish_network_event("outage_detected", {
            "outage_id": str(outage.id),
            "area_name": area.area_name,
            "severity": outage.severity,
            "affected_count": offline,
        })
        logger.warning(f"Outage detected: {area.area_name} ({offline}/{total})")
        return outage

    async def get_network_health_map(self, db: AsyncSession) -> List[dict]:
        """Per-service-area health snapshot for the heatmap."""
        cached = await cache_service.get("network:health_map")
        if cached:
            return cached
        areas = (await db.execute(select(ServiceArea).where(ServiceArea.is_active == True))).scalars()  # noqa
        out = []
        for area in areas:
            total = (await db.execute(
                select(func.count(NetworkDevice.id)).where(
                    NetworkDevice.service_area_id == area.id,
                    NetworkDevice.device_type == "onu",
                )
            )).scalar() or 0
            online = (await db.execute(
                select(func.count(NetworkDevice.id)).where(
                    NetworkDevice.service_area_id == area.id,
                    NetworkDevice.device_type == "onu",
                    NetworkDevice.status == "online",
                )
            )).scalar() or 0
            health = (online / total * 100) if total else 100.0
            out.append({
                "area_id": str(area.id),
                "area_code": area.area_code,
                "area_name": area.area_name,
                "municipality": area.municipality,
                "total_devices": int(total),
                "online_devices": int(online),
                "health_score": round(health, 1),
                "status": "healthy" if health >= 95 else "degraded" if health >= 70 else "critical",
            })
        await cache_service.set("network:health_map", out, ttl=300)
        return out

    async def list_outages(self, db: AsyncSession, active_only: bool = True) -> List[NetworkOutage]:
        stmt = select(NetworkOutage).order_by(desc(NetworkOutage.detected_at))
        if active_only:
            stmt = stmt.where(NetworkOutage.status != "resolved")
        return list((await db.execute(stmt)).scalars())

    async def create_outage(self, db: AsyncSession, data: dict, created_by: Optional[UUID] = None) -> NetworkOutage:
        outage = NetworkOutage(
            id=uuid4(),
            title=data["title"],
            description=data.get("description"),
            outage_type=data.get("outage_type", "unplanned"),
            severity=data.get("severity", "medium"),
            affected_device_id=data.get("affected_device_id"),
            affected_area_id=data.get("affected_area_id"),
            status="detected",
            detected_at=datetime.utcnow(),
            created_by_user_id=created_by,
        )
        db.add(outage)
        await db.commit()
        await db.refresh(outage)
        await cache_service.publish_network_event("outage_created", {
            "outage_id": str(outage.id), "title": outage.title, "severity": outage.severity,
        })
        return outage

    async def resolve_outage(self, db: AsyncSession, outage_id: UUID, notes: str = "") -> Optional[NetworkOutage]:
        outage = (await db.execute(select(NetworkOutage).where(NetworkOutage.id == outage_id))).scalar_one_or_none()
        if outage is None:
            return None
        outage.status = "resolved"
        outage.resolved_at = datetime.utcnow()
        outage.resolution_notes = notes
        await db.commit()
        await cache_service.publish_network_event("outage_resolved", {"outage_id": str(outage_id)})
        return outage

    async def get_customer_area_outage(self, db: AsyncSession, customer_id: UUID) -> Optional[NetworkOutage]:
        # Look up customer's primary service area, then check active outages
        from app.models import CustomerAddress
        address = (await db.execute(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_primary == True,  # noqa
            )
        )).scalar_one_or_none()
        if address is None or address.service_area_id is None:
            return None
        outage = (await db.execute(
            select(NetworkOutage).where(
                NetworkOutage.affected_area_id == address.service_area_id,
                NetworkOutage.status.notin_(["resolved"]),
            ).order_by(desc(NetworkOutage.detected_at))
        )).scalar_one_or_none()
        return outage

    async def poll_all_devices(self, db: AsyncSession) -> dict:
        """Iterate all online ONUs, refresh status via Huawei API, store metric."""
        devices = (await db.execute(
            select(NetworkDevice).where(NetworkDevice.device_type == "onu")
        )).scalars().all()
        polled = 0
        for device in devices:
            try:
                status = await router_service.get_onu_status(db, device.id)
                metric = DeviceMetric(
                    time=datetime.utcnow(),
                    device_id=device.id,
                    rx_power_dbm=device.rx_power_dbm,
                    tx_power_dbm=device.tx_power_dbm,
                    uptime_seconds=device.uptime_seconds,
                )
                db.add(metric)
                polled += 1
            except Exception as e:
                logger.warning(f"Poll {device.serial_number}: {e}")
        await db.commit()
        # Sweep outage detection across areas
        areas = (await db.execute(select(ServiceArea).where(ServiceArea.is_active == True))).scalars()  # noqa
        for area in areas:
            await self.detect_outage_for_area(db, area.id)
        return {"polled": polled, "total_devices": len(devices)}


network_service = NetworkService()
