"""Simulated Positions and Portfolio Management REST router."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.position import Position
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.trading import (
    PortfolioSummaryResponse,
    PositionResponse,
)

router = APIRouter(tags=["Portfolio & Positions"])


@router.get(
    "/positions",
    response_model=ApiResponse[PaginatedResponse[PositionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Paper Positions",
    description="Retrieve paginated simulated positions filtered by status (OPEN, CLOSED).",
)
@router.get(
    "/portfolio/positions",
    response_model=ApiResponse[PaginatedResponse[PositionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Paper Positions (Alias)",
    description="Alias for retrieving paginated simulated positions.",
)
async def list_positions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[PositionResponse]]:
    stmt = (
        select(Position, Instrument.symbol)
        .join(Instrument, Position.instrument_id == Instrument.id)
        .order_by(desc(Position.entry_time))
    )
    if status_filter:
        stmt = stmt.where(Position.status == status_filter.upper())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(paginated_stmt)).all()

    items = []
    for pos, sym in rows:
        items.append(
            PositionResponse(
                id=pos.id,
                session_id=pos.session_id,
                instrument_id=pos.instrument_id,
                symbol=sym,
                side=pos.side,
                quantity=pos.quantity,
                average_entry_price=float(pos.average_entry_price),
                current_price=float(pos.current_price),
                stop_loss=float(pos.stop_loss),
                target=float(pos.target),
                realized_pnl=float(pos.realized_pnl),
                unrealized_pnl=float(pos.unrealized_pnl),
                status=pos.status,
                is_paper=pos.is_paper,
                entry_time=pos.entry_time,
                exit_time=pos.exit_time,
            )
        )

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
    "/positions/{position_id}",
    response_model=ApiResponse[PositionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Position by ID",
)
async def get_position(position_id: int, db: AsyncSession = Depends(get_db)) -> ApiResponse[PositionResponse]:
    stmt = (
        select(Position, Instrument.symbol)
        .join(Instrument, Position.instrument_id == Instrument.id)
        .where(Position.id == position_id)
    )
    res = (await db.execute(stmt)).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    pos, sym = res
    return ApiResponse(
        success=True,
        data=PositionResponse(
            id=pos.id,
            session_id=pos.session_id,
            instrument_id=pos.instrument_id,
            symbol=sym,
            side=pos.side,
            quantity=pos.quantity,
            average_entry_price=float(pos.average_entry_price),
            current_price=float(pos.current_price),
            stop_loss=float(pos.stop_loss),
            target=float(pos.target),
            realized_pnl=float(pos.realized_pnl),
            unrealized_pnl=float(pos.unrealized_pnl),
            status=pos.status,
            is_paper=pos.is_paper,
            entry_time=pos.entry_time,
            exit_time=pos.exit_time,
        ),
    )


@router.get(
    "/portfolio/summary",
    response_model=ApiResponse[PortfolioSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Account Portfolio Summary",
    description="Returns virtual equity, 10% cash reserve, available margin, and total P&L.",
)
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)) -> ApiResponse[PortfolioSummaryResponse]:
    stmt = select(Position).where(Position.status == "OPEN")
    open_positions = (await db.execute(stmt)).scalars().all()

    total_cap = settings.PAPER_INITIAL_CAPITAL
    cash_reserve = total_cap * settings.CASH_RESERVE_PCT

    utilized_margin = sum(float(p.average_entry_price) * p.quantity for p in open_positions)
    realized = sum(float(p.realized_pnl) for p in open_positions)
    unrealized = sum(float(p.unrealized_pnl) for p in open_positions)

    available_margin = max(0.0, total_cap - utilized_margin - cash_reserve)
    net_equity = total_cap + realized + unrealized

    return ApiResponse(
        success=True,
        data=PortfolioSummaryResponse(
            total_capital=total_cap,
            available_margin=round(available_margin, 2),
            utilized_margin=round(utilized_margin, 2),
            cash_reserve=round(cash_reserve, 2),
            realized_pnl=round(realized, 2),
            unrealized_pnl=round(unrealized, 2),
            net_equity=round(net_equity, 2),
            open_positions_count=len(open_positions),
            is_paper=True,
        ),
    )
