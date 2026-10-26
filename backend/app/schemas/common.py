from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper."""
    success: bool = Field(default=True)
    message: Optional[str] = Field(default=None)
    data: Optional[T] = Field(default=None)


class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized pagination response structure."""
    items: List[T] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=50)
    total_pages: int = Field(default=0)
