"""Historical data ingestion management and quality audit endpoints."""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import AsyncSessionLocal, get_db
from backend.app.models.data_quality import DataQualityLog
from backend.app.models.ingestion import DataIngestionJob
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.market_data import (
    DataQualityLogResponse,
    IngestionJobCreateRequest,
    IngestionJobResponse,
)
from trading_engine.market_data.ingestion import HistoricalCandleIngestionService
from trading_engine.market_data.mock_provider import MockMarketDataProvider

router = APIRouter(prefix="/market-data", tags=["Market Data Ingestion"])


async def _run_background_ingestion(job_id: int) -> None:
    """Execute ingestion job in background task with dedicated session."""
    async with AsyncSessionLocal() as session:
        # For Phase 2 local development, default to MockMarketDataProvider
        # Angel One provider can be selected when environment credentials are provided
        service = HistoricalCandleIngestionService(MockMarketDataProvider())
        try:
            await service.execute_job(session, job_id)
        except Exception:
            pass  # Exception state already logged to job by service


@router.post(
    "/ingestion",
    response_model=ApiResponse[IngestionJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger historical market data ingestion",
    description="Enqueue a background job to fetch and validate historical intraday candles.",
)
async def trigger_ingestion(
    request: IngestionJobCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IngestionJobResponse]:
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be greater than or equal to start_date.",
        )

    job = DataIngestionJob(
        job_type="HISTORICAL_CANDLES",
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        status="PENDING",
        candles_ingested=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to background task
    background_tasks.add_task(_run_background_ingestion, job.id)

    return ApiResponse(
        success=True,
        message=f"Ingestion job #{job.id} enqueued successfully.",
        data=IngestionJobResponse.model_validate(job),
    )


@router.get(
    "/ingestion/{job_id}",
    response_model=ApiResponse[IngestionJobResponse],
    summary="Get ingestion job status",
    description="Query current status and progress of a historical data ingestion job.",
)
async def get_ingestion_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[IngestionJobResponse]:
    stmt = select(DataIngestionJob).where(DataIngestionJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job #{job_id} not found.",
        )

    return ApiResponse(
        success=True,
        data=IngestionJobResponse.model_validate(job),
    )


@router.get(
    "/quality",
    response_model=ApiResponse[PaginatedResponse[DataQualityLogResponse]],
    summary="Query data quality logs",
    description="Retrieve data quality audit logs (missing intervals, invalid OHLC, out-of-session anomalies).",
)
async def get_data_quality_logs(
    db: AsyncSession = Depends(get_db),
    symbol: Optional[str] = Query(default=None, description="Filter by symbol"),
    check_type: Optional[str] = Query(default=None, description="Filter by check type"),
    severity: Optional[str] = Query(default=None, description="Filter by severity (INFO, WARNING, ERROR)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=500, description="Page size"),
) -> ApiResponse[PaginatedResponse[DataQualityLogResponse]]:
    stmt = select(DataQualityLog)

    if symbol:
        stmt = stmt.where(DataQualityLog.symbol == symbol)
    if check_type:
        stmt = stmt.where(DataQualityLog.check_type == check_type)
    if severity:
        stmt = stmt.where(DataQualityLog.severity == severity)

    # Count total
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(DataQualityLog.detected_at.desc()).offset(offset).limit(page_size)
    res = await db.execute(stmt)
    logs = list(res.scalars().all())

    total_pages = (total + page_size - 1) // page_size

    return ApiResponse(
        success=True,
        data=PaginatedResponse(
            items=[DataQualityLogResponse.model_validate(l) for l in logs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )
