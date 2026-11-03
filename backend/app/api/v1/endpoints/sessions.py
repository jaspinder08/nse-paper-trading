"""Intraday Trading Session endpoints."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.trading_session import TradingSession
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.trading import TradingSessionResponse
from shared.market_time import now_ist

router = APIRouter(prefix="/sessions", tags=["Trading Sessions"])


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[TradingSessionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Trading Sessions",
)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[TradingSessionResponse]]:
    stmt = select(TradingSession).order_by(desc(TradingSession.session_date))
    count_stmt = select(func.count()).select_from(TradingSession)
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    sessions = (await db.execute(paginated_stmt)).scalars().all()

    items = [
        TradingSessionResponse(
            id=s.id,
            session_date=s.session_date,
            status=s.status,
            market_open_time=s.market_open_time,
            market_close_time=s.market_close_time,
            is_paper=s.is_paper,
            initial_capital=float(s.initial_capital),
            realized_pnl=float(s.realized_pnl),
            unrealized_pnl=float(s.unrealized_pnl),
            total_trades=s.total_trades,
            winning_trades=s.winning_trades,
            losing_trades=s.losing_trades,
            notes=s.notes,
        )
        for s in sessions
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
    "/current",
    response_model=ApiResponse[Optional[TradingSessionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Current Trading Session",
)
async def get_current_session(db: AsyncSession = Depends(get_db)) -> ApiResponse[Optional[TradingSessionResponse]]:
    today = now_ist().date()
    stmt = select(TradingSession).where(TradingSession.session_date == today)
    session = (await db.execute(stmt)).scalar_one_or_none()

    if not session:
        # Create virtual today session view if none persisted yet
        return ApiResponse(
            success=True,
            data=TradingSessionResponse(
                id=0,
                session_date=today,
                status="SCHEDULED",
                market_open_time=None,
                market_close_time=None,
                is_paper=True,
                initial_capital=settings.PAPER_INITIAL_CAPITAL,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                notes="Virtual Session Initialized",
            ),
        )

    return ApiResponse(
        success=True,
        data=TradingSessionResponse(
            id=session.id,
            session_date=session.session_date,
            status=session.status,
            market_open_time=session.market_open_time,
            market_close_time=session.market_close_time,
            is_paper=session.is_paper,
            initial_capital=float(session.initial_capital),
            realized_pnl=float(session.realized_pnl),
            unrealized_pnl=float(session.unrealized_pnl),
            total_trades=session.total_trades,
            winning_trades=session.winning_trades,
            losing_trades=session.losing_trades,
            notes=session.notes,
        ),
    )
