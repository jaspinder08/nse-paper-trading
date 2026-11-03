"""Trade Journal and System Audit Logging REST endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.logs import SystemLog, TradeLog
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.trading import SystemLogResponse, TradeLogResponse

router = APIRouter(tags=["Trade Journal & System Logs"])


@router.get(
    "/journal",
    response_model=ApiResponse[PaginatedResponse[TradeLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Trade Journal Entries",
    description="Retrieve chronological trade execution audit logs with prices, actions, and P&L.",
)
async def list_trade_journal(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[TradeLogResponse]]:
    stmt = (
        select(TradeLog, Instrument.symbol)
        .join(Instrument, TradeLog.instrument_id == Instrument.id)
        .order_by(desc(TradeLog.log_timestamp))
    )
    if action:
        stmt = stmt.where(TradeLog.action == action.upper())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(paginated_stmt)).all()

    items = [
        TradeLogResponse(
            id=log.id,
            order_id=log.order_id,
            position_id=log.position_id,
            instrument_id=log.instrument_id,
            symbol=sym,
            action=log.action,
            quantity=log.quantity,
            price=float(log.price),
            pnl=float(log.pnl) if log.pnl is not None else None,
            is_paper=log.is_paper,
            log_timestamp=log.log_timestamp,
        )
        for log, sym in rows
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/logs/system",
    response_model=ApiResponse[PaginatedResponse[SystemLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="List System Operational Logs",
)
async def list_system_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[SystemLogResponse]]:
    stmt = select(SystemLog).order_by(desc(SystemLog.logged_at))
    if level:
        stmt = stmt.where(SystemLog.level == level.upper())

    count_stmt = select(func.count()).select_from(SystemLog)
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    logs = (await db.execute(paginated_stmt)).scalars().all()

    items = [
        SystemLogResponse(
            id=l.id,
            level=l.level,
            module=l.module,
            message=l.message,
            details=l.details,
            logged_at=l.logged_at,
        )
        for l in logs
    ]

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
