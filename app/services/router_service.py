"""
Huawei iMaster NCE OLT/ONU integration.

Replaces the previous mock implementation. Falls back to a stub mode when
HUAWEI_OLT_PASSWORD is not configured (development convenience).
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NetworkDevice
from app.services.cache_service import cache_service
from config.settings import settings
from config.rbac import SIGNAL_QUALITY


def _classify_signal(rx_power_dbm: Optional[float]) -> str:
    if rx_power_dbm is None:
        return "unknown"
    rx = float(rx_power_dbm)
    if rx < SIGNAL_QUALITY["los"]["threshold"]:
        return "los"
    if rx < SIGNAL_QUALITY["critical"]["min"]:
        return "critical"
    if rx < SIGNAL_QUALITY["weak"]["min"]:
        return "weak"
    return "good"


class HuaweiIMasterService:
    """Real Huawei iMaster NCE-FAN API client.

    In stub mode (no password configured), it returns reasonable simulated
    data based on what is stored in the local NetworkDevice rows so that the
    voice bot and dashboards remain operational during development.
    """

    def __init__(self):
        self._session_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    @property
    def stub_mode(self) -> bool:
        return not settings.huawei_olt_password

    async def authenticate(self) -> Optional[str]:
        if self.stub_mode:
            return "stub-token"
        if self._session_token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._session_token
        try:
            async with httpx.AsyncClient(timeout=settings.huawei_olt_timeout, verify=False) as client:
                r = await client.post(
                    f"{settings.huawei_olt_base_url}/controller/v2/tokens",
                    json={
                        "grantType": "password",
                        "userName": settings.huawei_olt_username,
                        "value": settings.huawei_olt_password,
                    },
                )
                r.raise_for_status()
                data = r.json()
                self._session_token = data.get("accessSession") or data.get("token")
                self._token_expires_at = datetime.utcnow().replace(microsecond=0)
                return self._session_token
        except Exception as e:
            logger.warning(f"Huawei auth failed (fallback to stub): {e}")
            return None

    async def _get(self, path: str, params: dict = None) -> Optional[dict]:
        if self.stub_mode:
            return None
        token = await self.authenticate()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=settings.huawei_olt_timeout, verify=False) as client:
                r = await client.get(
                    f"{settings.huawei_olt_base_url}{path}",
                    params=params or {},
                    headers={"X-Auth-Token": token},
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.warning(f"Huawei GET {path} failed: {e}")
            return None

    async def get_onu_status(self, db: AsyncSession, device_id: UUID) -> dict:
        cached = await cache_service.get_device_status(str(device_id))
        if cached:
            return cached
        device = (await db.execute(
            select(NetworkDevice).where(NetworkDevice.id == device_id)
        )).scalar_one_or_none()
        if device is None:
            return {"status": "unknown", "error": "device not found"}

        result = {
            "device_id": str(device.id),
            "serial_number": device.serial_number,
            "mac_address": device.mac_address,
            "status": device.status,
            "rx_power_dbm": float(device.rx_power_dbm) if device.rx_power_dbm is not None else None,
            "tx_power_dbm": float(device.tx_power_dbm) if device.tx_power_dbm is not None else None,
            "signal_quality": device.signal_quality,
            "uptime_seconds": device.uptime_seconds,
            "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        }

        if not self.stub_mode and device.serial_number:
            live = await self._get(f"/restconf/v2/data/huawei-onu/onu/{device.serial_number}")
            if live:
                onu = live.get("onu", {})
                device.status = onu.get("runState", device.status)
                device.rx_power_dbm = onu.get("rxPower", device.rx_power_dbm)
                device.tx_power_dbm = onu.get("txPower", device.tx_power_dbm)
                device.signal_quality = _classify_signal(device.rx_power_dbm)
                device.last_seen_at = datetime.utcnow()
                await db.commit()
                result.update({
                    "status": device.status,
                    "rx_power_dbm": float(device.rx_power_dbm) if device.rx_power_dbm is not None else None,
                    "tx_power_dbm": float(device.tx_power_dbm) if device.tx_power_dbm is not None else None,
                    "signal_quality": device.signal_quality,
                })

        await cache_service.set_device_status(str(device_id), result)
        return result

    async def reboot_onu(self, db: AsyncSession, device_id: UUID) -> bool:
        device = (await db.execute(
            select(NetworkDevice).where(NetworkDevice.id == device_id)
        )).scalar_one_or_none()
        if device is None:
            return False
        if self.stub_mode:
            logger.info(f"[STUB] Rebooting ONU {device.serial_number}")
            return True
        token = await self.authenticate()
        if not token:
            return False
        try:
            async with httpx.AsyncClient(timeout=settings.huawei_olt_timeout, verify=False) as client:
                r = await client.post(
                    f"{settings.huawei_olt_base_url}/restconf/v2/operations/huawei-onu:reset",
                    headers={"X-Auth-Token": token},
                    json={"input": {"onuSn": device.serial_number}},
                )
                ok = r.status_code in (200, 204)
                if ok:
                    logger.info(f"ONU reboot sent: {device.serial_number}")
                return ok
        except Exception as e:
            logger.warning(f"Huawei reboot error: {e}")
            return False

    async def get_pppoe_session(self, db: AsyncSession, pppoe_username: str) -> dict:
        if self.stub_mode:
            device = (await db.execute(
                select(NetworkDevice).where(NetworkDevice.pppoe_username == pppoe_username)
            )).scalar_one_or_none()
            return {
                "active": device is not None and device.status == "online",
                "username": pppoe_username,
                "ip_address": str(device.ip_address) if device and device.ip_address else None,
                "uptime_seconds": device.uptime_seconds if device else 0,
            }
        data = await self._get(f"/restconf/v2/data/huawei-bras/pppoe-sessions/{pppoe_username}") or {}
        return data.get("session", {"active": False})

    async def get_all_offline_onus(self, db: AsyncSession) -> List[NetworkDevice]:
        result = await db.execute(
            select(NetworkDevice).where(
                NetworkDevice.device_type == "onu",
                NetworkDevice.status == "offline",
            )
        )
        return list(result.scalars())


router_service = HuaweiIMasterService()
huawei_service = router_service  # legacy alias
