"""Market status, calendar, and candlestick query endpoints."""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.market_candle import MarketCandle
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.market_data import (
    CandleResponse,
    MarketCalendarItem,
    MarketStatusResponse,
)
from trading_engine.market_data.calendar import MarketCalendarService
from shared.market_time import IST_ZONE, to_utc

router = APIRouter(prefix="/market", tags=["Market"])


@router.get(
    "/status",
    response_model=ApiResponse[MarketStatusResponse],
    summary="Get current market status",
    description="Check whether the NSE equity market is open right now, session type, and next open/close.",
)
async def get_market_status() -> ApiResponse[MarketStatusResponse]:
    status_info = MarketCalendarService.get_market_status()
    return ApiResponse(
        success=True,
        data=MarketStatusResponse(**status_info),
    )


@router.get(
    "/calendar",
    response_model=ApiResponse[List[MarketCalendarItem]],
    summary="Get market calendar",
    description="Retrieve trading days, holidays, and special sessions for a date range.",
)
async def get_market_calendar(
    start_date: date = Query(description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(description="End date (YYYY-MM-DD)"),
) -> ApiResponse[List[MarketCalendarItem]]:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date.",
        )
    if (end_date - start_date).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum query range is 1 year (366 days).",
        )

    entries = MarketCalendarService.get_calendar_range(start_date, end_date)
    items = [
        MarketCalendarItem(
            date=e["date"],
            is_trading_day=e["is_trading_day"],
            session_type=e["session_type"],
            market_open_time=e["market_open_time"],
            market_close_time=e["market_close_time"],
            description=e["description"],
            holiday_reason=e["holiday_reason"],
        )
        for e in entries
    ]
    return ApiResponse(success=True, data=items)


@router.get(
    "/candles",
    response_model=ApiResponse[List[CandleResponse]],
    summary="Query historical market candles",
    description="Fetch stored intraday candlesticks for a specific instrument and timeframe.",
)
async def get_market_candles(
    db: AsyncSession = Depends(get_db),
    symbol: Optional[str] = Query(default=None, description="Trading symbol (e.g. INFY, TCS)"),
    instrument_id: Optional[int] = Query(default=None, description="Internal instrument ID"),
    timeframe: str = Query(default="5m", description="Candle timeframe e.g. 5m, 15m"),
    from_date: Optional[datetime] = Query(default=None, description="Filter from timestamp"),
    to_date: Optional[datetime] = Query(default=None, description="Filter to timestamp"),
    limit: int = Query(default=500, ge=1, le=5000, description="Max candle records to return"),
) -> ApiResponse[List[CandleResponse]]:
    if not symbol and not instrument_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either 'symbol' or 'instrument_id'.",
        )

    target_id = instrument_id
    if not target_id:
        stmt_inst = select(Instrument.id).where(Instrument.symbol == symbol, Instrument.exchange == "NSE")
        res_inst = await db.execute(stmt_inst)
        target_id = res_inst.scalar_one_or_none()
        if not target_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument '{symbol}' not found.",
            )

    stmt = select(MarketCandle).where(
        MarketCandle.instrument_id == target_id,
        MarketCandle.timeframe == timeframe,
    )

    if from_date:
        stmt = stmt.where(MarketCandle.candle_timestamp >= to_utc(from_date))
    if to_date:
        stmt = stmt.where(MarketCandle.candle_timestamp <= to_utc(to_date))

    stmt = stmt.order_by(MarketCandle.candle_timestamp.asc()).limit(limit)
    res = await db.execute(stmt)
    candles = list(res.scalars().all())

    return ApiResponse(
        success=True,
        data=[CandleResponse.model_validate(c) for c in candles],
    )
