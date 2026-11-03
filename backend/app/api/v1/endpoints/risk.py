"""Risk Gatekeeper REST endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.logs import RiskLog
from backend.app.models.position import Position
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.trading import (
    RiskLogResponse,
    RiskStatusResponse,
    RiskValidationRequest,
    RiskValidationResponse,
)
from trading_engine.risk.sizing import PositionSizer
from trading_engine.risk.validator import RiskValidator

router = APIRouter(prefix="/risk", tags=["Risk Management"])
_validator = RiskValidator(
    max_daily_loss=settings.MAX_DAILY_LOSS_INR,
    max_open_positions=settings.MAX_OPEN_POSITIONS,
    max_trades_per_day=settings.MAX_TRADES_PER_DAY,
    max_events_per_day=settings.MAX_EVENTS_PER_DAY,
    min_reward_risk=settings.MIN_REWARD_RISK,
    position_sizer=PositionSizer(
        max_risk_per_trade_inr=settings.MAX_RISK_PER_TRADE_INR,
        cash_reserve_pct=settings.CASH_RESERVE_PCT,
        max_position_pct=settings.MAX_POSITION_PCT,
    ),
)


@router.get(
    "/status",
    response_model=ApiResponse[RiskStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Current Risk Gatekeeper Status",
    description="Returns daily circuit breaker status, daily loss utilization, trades/events quotas, and cash reserve.",
)
async def get_risk_status(db: AsyncSession = Depends(get_db)) -> ApiResponse[RiskStatusResponse]:
    # Query current open positions
    stmt = select(Position).where(Position.status == "OPEN")
    open_positions = (await db.execute(stmt)).scalars().all()

    realized_daily_pnl = sum(float(p.realized_pnl) for p in open_positions)
    open_risk = sum(abs(float(p.average_entry_price) - float(p.stop_loss)) * p.quantity for p in open_positions)

    circuit_breaker = realized_daily_pnl <= -settings.MAX_DAILY_LOSS_INR
    trades_today = len(open_positions)  # Or query today's trades
    trades_rem = max(0, settings.MAX_TRADES_PER_DAY - trades_today)
    loss_util = round((abs(min(0.0, realized_daily_pnl)) / settings.MAX_DAILY_LOSS_INR) * 100.0, 1)

    return ApiResponse(
        success=True,
        data=RiskStatusResponse(
            circuit_breaker_active=circuit_breaker,
            max_daily_loss=settings.MAX_DAILY_LOSS_INR,
            current_daily_pnl=round(realized_daily_pnl, 2),
            daily_loss_utilization_pct=loss_util,
            trades_today=trades_today,
            max_trades_per_day=settings.MAX_TRADES_PER_DAY,
            trades_remaining=trades_rem,
            events_today=trades_today * 2,
            max_events_per_day=settings.MAX_EVENTS_PER_DAY,
            open_positions_count=len(open_positions),
            max_open_positions=settings.MAX_OPEN_POSITIONS,
            planned_open_risk=round(open_risk, 2),
            cash_reserve_preserved=round(settings.PAPER_INITIAL_CAPITAL * settings.CASH_RESERVE_PCT, 2),
        ),
    )


@router.post(
    "/validate",
    response_model=ApiResponse[RiskValidationResponse],
    status_code=status.HTTP_200_OK,
    summary="Dry-Run Risk Validation",
    description="Validate an arbitrary breakout signal candidate against all 9 risk gatekeeper checks.",
)
async def validate_candidate_signal(
    request: RiskValidationRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[RiskValidationResponse]:
    stmt = select(Position).where(Position.status == "OPEN")
    open_positions = (await db.execute(stmt)).scalars().all()
    pos_map = {p.instrument_id: p for p in open_positions}

    utilized = sum(float(p.average_entry_price) * p.quantity for p in open_positions)
    realized = sum(float(p.realized_pnl) for p in open_positions)
    avail_cash = max(0.0, settings.PAPER_INITIAL_CAPITAL - utilized)

    verdict = _validator.validate_candidate(
        signal=request.model_dump(),
        equity=settings.PAPER_INITIAL_CAPITAL,
        available_cash=avail_cash,
        current_daily_pnl=realized,
        open_positions=pos_map,
        trades_today_count=len(open_positions),
    )

    return ApiResponse(
        success=True,
        data=RiskValidationResponse(
            approved=verdict.approved,
            reason=verdict.reason,
            adjusted_quantity=verdict.adjusted_quantity,
            total_rupee_risk=verdict.sizing.total_rupee_risk if verdict.sizing else 0.0,
            position_value=verdict.sizing.position_value if verdict.sizing else 0.0,
            limiting_factor=verdict.sizing.limiting_factor if verdict.sizing else None,
            circuit_breaker_active=verdict.circuit_breaker_active,
        ),
    )


@router.get(
    "/logs",
    response_model=ApiResponse[PaginatedResponse[RiskLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Risk Gatekeeper Audit Logs",
)
async def list_risk_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[RiskLogResponse]]:
    stmt = select(RiskLog).order_by(desc(RiskLog.created_at))
    count_stmt = select(func.count()).select_from(RiskLog)
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    logs = (await db.execute(paginated_stmt)).scalars().all()

    items = [
        RiskLogResponse(
            id=log.id,
            session_id=log.session_id,
            signal_id=log.signal_id,
            check_name=log.check_name,
            passed=log.passed,
            reason=log.reason,
            created_at=log.created_at,
        )
        for log in logs
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
