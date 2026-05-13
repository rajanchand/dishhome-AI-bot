"""Offset-based pagination helper."""

from typing import Optional
from fastapi import Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 50

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
