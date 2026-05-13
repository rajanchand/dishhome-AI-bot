"""Package catalog routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_db, User
from app.models.schemas import PackageCreate, PackageResponse
from app.services.package_service import package_service
from app.utils.dependencies import require_permission

router = APIRouter(prefix="/api/packages", tags=["packages"])


@router.get("")
async def list_packages(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    items = await package_service.list_packages(db, active_only=active_only)
    return {"items": [PackageResponse.model_validate(p).model_dump() for p in items]}


@router.post("", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
async def create_package(
    payload: PackageCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("packages", "write")),
):
    pkg = await package_service.create_package(db, payload.model_dump())
    return PackageResponse.model_validate(pkg)


@router.get("/{package_id}", response_model=PackageResponse)
async def get_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    pkg = await package_service.get_package(db, package_id)
    if pkg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    return PackageResponse.model_validate(pkg)


@router.put("/{package_id}", response_model=PackageResponse)
async def update_package(
    package_id: UUID,
    payload: PackageCreate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("packages", "write")),
):
    pkg = await package_service.update_package(db, package_id, payload.model_dump(exclude_unset=True))
    if pkg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Package not found")
    return PackageResponse.model_validate(pkg)
