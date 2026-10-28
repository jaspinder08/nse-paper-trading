"""Instrument Master endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.models.instrument import Instrument
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.market_data import InstrumentResponse

router = APIRouter(prefix="/instruments", tags=["Instruments"])


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[InstrumentResponse]],
    summary="List instruments",
    description="Retrieve instruments from the instrument master with filtering and pagination.",
)
async def list_instruments(
    db: AsyncSession = Depends(get_db),
    exchange: str = Query(default="NSE", description="Exchange code"),
    symbol: Optional[str] = Query(default=None, description="Symbol filter (prefix or exact)"),
    is_tradable: Optional[bool] = Query(default=None, description="Filter tradable status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Page size"),
) -> ApiResponse[PaginatedResponse[InstrumentResponse]]:
    stmt = select(Instrument).where(Instrument.exchange == exchange)

    if symbol:
        stmt = stmt.where(Instrument.symbol.ilike(f"%{symbol}%"))
    if is_tradable is not None:
        stmt = stmt.where(Instrument.is_tradable == is_tradable)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Instrument.symbol.asc()).offset(offset).limit(page_size)
    res = await db.execute(stmt)
    items = list(res.scalars().all())

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=[InstrumentResponse.model_validate(it) for it in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/{instrument_id}",
    response_model=ApiResponse[InstrumentResponse],
    summary="Get instrument by ID",
    description="Retrieve details for a single instrument by its internal ID.",
)
async def get_instrument(
    instrument_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[InstrumentResponse]:
    stmt = select(Instrument).where(Instrument.id == instrument_id)
    res = await db.execute(stmt)
    inst = res.scalar_one_or_none()

    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument #{instrument_id} not found.",
        )

    return ApiResponse(
        success=True,
        data=InstrumentResponse.model_validate(inst),
    )
