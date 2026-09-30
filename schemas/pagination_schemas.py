from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field
import math

class PaginationRequest(BaseModel):
    page: int = Field(ge=1, default=1)
    limit: int = Field(ge=1, le= 100, default=20)

T = TypeVar('T')

class PaginationResponse(PaginationRequest, Generic[T]):
    items: List[T]
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: List[T], total_count: int, page: int, limit: int):
        total_pages = math.ceil(total_count/limit) if total_count > 0 else 0
        return cls(
            items=items,
            total_count=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next= page < total_pages,
            has_prev= page > 1
        )
    