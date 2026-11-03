"""Simulated Paper Orders REST router."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.models.instrument import Instrument
from backend.app.models.paper_order import PaperOrder
from backend.app.schemas.common import ApiResponse, PaginatedResponse
from backend.app.schemas.trading import PaperOrderResponse

router = APIRouter(prefix="/orders", tags=["Paper Orders"])


@router.get(
    "",
    response_model=ApiResponse[PaginatedResponse[PaperOrderResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Paper Orders",
    description="Retrieve paginated simulated paper orders with optional status or session filtering.",
)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    session_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[PaperOrderResponse]]:
    stmt = (
        select(PaperOrder, Instrument.symbol)
        .join(Instrument, PaperOrder.instrument_id == Instrument.id)
        .order_by(desc(PaperOrder.created_at))
    )
    if status_filter:
        stmt = stmt.where(PaperOrder.status == status_filter.upper())
    if session_id:
        stmt = stmt.where(PaperOrder.session_id == session_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    paginated_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(paginated_stmt)).all()

    items = []
    for order, sym in rows:
        items.append(
            PaperOrderResponse(
                id=order.id,
                session_id=order.session_id,
                instrument_id=order.instrument_id,
                symbol=sym,
                order_type=order.order_type,
                transaction_type=order.transaction_type,
                quantity=order.quantity,
                requested_price=float(order.requested_price),
                executed_price=float(order.executed_price) if order.executed_price else None,
                status=order.status,
                is_paper=order.is_paper,
                executed_at=order.executed_at,
                created_at=order.created_at,
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
    "/{order_id}",
    response_model=ApiResponse[PaperOrderResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Paper Order by ID",
)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)) -> ApiResponse[PaperOrderResponse]:
    stmt = (
        select(PaperOrder, Instrument.symbol)
        .join(Instrument, PaperOrder.instrument_id == Instrument.id)
        .where(PaperOrder.id == order_id)
    )
    res = (await db.execute(stmt)).first()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper order not found")

    order, sym = res
    return ApiResponse(
        success=True,
        data=PaperOrderResponse(
            id=order.id,
            session_id=order.session_id,
            instrument_id=order.instrument_id,
            symbol=sym,
            order_type=order.order_type,
            transaction_type=order.transaction_type,
            quantity=order.quantity,
            requested_price=float(order.requested_price),
            executed_price=float(order.executed_price) if order.executed_price else None,
            status=order.status,
            is_paper=order.is_paper,
            executed_at=order.executed_at,
            created_at=order.created_at,
        ),
    )
