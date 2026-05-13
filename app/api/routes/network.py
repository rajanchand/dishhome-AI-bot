"""Network routes — devices, metrics, outages, health map."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import NetworkDeviceResponse, OutageResponse, Paginated
from app.services.network_service import network_service
from app.services.router_service import router_service
from app.utils.dependencies import require_permission
from app.utils.pagination import PaginationParams, get_pagination

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/devices", response_model=Paginated)
async def list_devices(
    pagination: PaginationParams = Depends(get_pagination),
    device_type: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "read")),
):
    items, total = await network_service.list_devices(
        db, device_type=device_type, status_filter=status_filter,
        offset=pagination.offset, limit=pagination.limit,
    )
    return Paginated(
        items=[NetworkDeviceResponse.model_validate(d).model_dump() for d in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
        has_more=(pagination.offset + len(items)) < total,
    )


@router.get("/health-map")
async def health_map(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "read")),
):
    return {"items": await network_service.get_network_health_map(db)}


@router.get("/outages")
async def list_outages(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "read")),
):
    items = await network_service.list_outages(db, active_only=active_only)
    return {"items": [OutageResponse.model_validate(o).model_dump() for o in items]}


@router.post("/outages", response_model=OutageResponse, status_code=status.HTTP_201_CREATED)
async def create_outage(
    title: str = Query(...),
    severity: str = Query("medium"),
    description: Optional[str] = None,
    affected_area_id: Optional[UUID] = None,
    affected_device_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("network", "write")),
):
    outage = await network_service.create_outage(db, {
        "title": title, "severity": severity, "description": description,
        "affected_area_id": affected_area_id, "affected_device_id": affected_device_id,
    }, created_by=current_user.id)
    return OutageResponse.model_validate(outage)


@router.put("/outages/{outage_id}/resolve")
async def resolve_outage(
    outage_id: UUID,
    notes: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "write")),
):
    outage = await network_service.resolve_outage(db, outage_id, notes=notes)
    if outage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Outage not found")
    return {"detail": "Outage resolved"}


@router.get("/devices/{device_id}", response_model=NetworkDeviceResponse)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "read")),
):
    device = await network_service.get_device(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    return NetworkDeviceResponse.model_validate(device)


@router.get("/devices/{device_id}/metrics")
async def device_metrics(
    device_id: UUID,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "read")),
):
    return {"items": await network_service.get_device_history(db, device_id, hours=hours)}


@router.get("/devices/{device_id}/status")
async def device_live_status(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "read")),
):
    return await router_service.get_onu_status(db, device_id)


@router.post("/devices/{device_id}/reboot")
async def reboot_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "write")),
):
    ok = await router_service.reboot_onu(db, device_id)
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Reboot command failed")
    return {"detail": "Reboot command sent"}


@router.post("/poll")
async def poll_all(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("network", "write")),
):
    return await network_service.poll_all_devices(db)
