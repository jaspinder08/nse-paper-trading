"""Pydantic v2 schemas for paper trading, orders, positions, risk, and backtesting."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -------------------------------------------------------------------------
# Scanner & Signal Schemas
# -------------------------------------------------------------------------

class SignalItemResponse(BaseModel):
    id: int
    instrument_id: int
    symbol: Optional[str] = None
    strategy_name: str
    signal_type: str
    trigger_price: float
    stop_loss: float
    target_price: float
    status: str
    rejection_reason: Optional[str] = None
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanCandidateResponse(BaseModel):
    symbol: str
    status: str  # TRIGGERED, PENDING_BREAKOUT, RANGE_FORMING, REJECTED_VOLUME, NO_DATA
    current_price: float
    orb_high: Optional[float] = None
    orb_low: Optional[float] = None
    orb_range_pct: Optional[float] = None
    distance_to_high_pct: Optional[float] = None
    volume_ratio: Optional[float] = None
    signal: Optional[Dict[str, Any]] = None
    reason: str
    last_candle_time: Optional[str] = None


class ScannerSummaryResponse(BaseModel):
    timestamp: datetime
    universe_size: int
    triggered_count: int
    pending_count: int
    forming_count: int
    candidates: List[ScanCandidateResponse] = Field(default_factory=list)


# -------------------------------------------------------------------------
# Order & Position Schemas
# -------------------------------------------------------------------------

class PaperOrderResponse(BaseModel):
    id: int
    session_id: Optional[int] = None
    instrument_id: int
    symbol: Optional[str] = None
    order_type: str
    transaction_type: str
    quantity: int
    requested_price: float
    executed_price: Optional[float] = None
    status: str
    is_paper: bool = True
    executed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PositionResponse(BaseModel):
    id: int
    session_id: Optional[int] = None
    instrument_id: int
    symbol: Optional[str] = None
    side: str
    quantity: int
    average_entry_price: float
    current_price: float
    stop_loss: float
    target: float
    realized_pnl: float
    unrealized_pnl: float
    status: str
    is_paper: bool = True
    entry_time: datetime
    exit_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioSummaryResponse(BaseModel):
    total_capital: float
    available_margin: float
    utilized_margin: float
    cash_reserve: float
    realized_pnl: float
    unrealized_pnl: float
    net_equity: float
    open_positions_count: int
    is_paper: bool = True


# -------------------------------------------------------------------------
# Session Schemas
# -------------------------------------------------------------------------

class TradingSessionResponse(BaseModel):
    id: int
    session_date: date
    status: str
    market_open_time: Optional[datetime] = None
    market_close_time: Optional[datetime] = None
    is_paper: bool = True
    initial_capital: float
    realized_pnl: float
    unrealized_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Risk Engine Schemas
# -------------------------------------------------------------------------

class RiskStatusResponse(BaseModel):
    circuit_breaker_active: bool
    max_daily_loss: float
    current_daily_pnl: float
    daily_loss_utilization_pct: float
    trades_today: int
    max_trades_per_day: int
    trades_remaining: int
    events_today: int
    max_events_per_day: int
    open_positions_count: int
    max_open_positions: int
    planned_open_risk: float
    cash_reserve_preserved: float


class RiskValidationRequest(BaseModel):
    symbol: str
    signal_type: str = "LONG"
    entry_price: float
    stop_loss: float
    target_price: Optional[float] = None
    lot_size: int = 1


class RiskValidationResponse(BaseModel):
    approved: bool
    reason: str
    adjusted_quantity: int
    total_rupee_risk: float
    position_value: float
    limiting_factor: Optional[str] = None
    circuit_breaker_active: bool


# -------------------------------------------------------------------------
# Journal & Audit Log Schemas
# -------------------------------------------------------------------------

class TradeLogResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    position_id: Optional[int] = None
    instrument_id: int
    symbol: Optional[str] = None
    action: str
    quantity: int
    price: float
    pnl: Optional[float] = None
    is_paper: bool = True
    log_timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskLogResponse(BaseModel):
    id: int
    session_id: Optional[int] = None
    signal_id: Optional[int] = None
    check_name: str
    passed: bool
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SystemLogResponse(BaseModel):
    id: int
    level: str
    module: str
    message: str
    details: Optional[str] = None
    logged_at: datetime

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------------------
# Backtesting Schemas
# -------------------------------------------------------------------------

class BacktestRequest(BaseModel):
    strategy_name: str = "ORB_STRATEGY"
    symbols: List[str] = Field(default_factory=lambda: ["RELIANCE", "TCS", "INFY"])
    start_date: date
    end_date: date
    initial_capital: float = 5000.0
    timeframe: str = "5m"


class BacktestRunResponse(BaseModel):
    id: int
    strategy_name: str
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    total_trades: int
    win_rate: float
    profit_factor: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BacktestTradeResponse(BaseModel):
    id: Optional[int] = None
    symbol: str
    entry_time: str
    exit_time: str
    side: str
    quantity: int
    entry_price: float
    exit_price: float
    gross_pnl: float
    total_charges: float
    slippage_cost: float
    net_pnl: float
    return_pct: float
    exit_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BacktestRunDetailResponse(BacktestRunResponse):
    net_pnl: float = 0.0
    return_pct: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    total_charges: float = 0.0
    total_slippage: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    payoff_ratio: float = 0.0
    expectancy: float = 0.0
    max_drawdown_amount: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    trades: List[BacktestTradeResponse] = Field(default_factory=list)

