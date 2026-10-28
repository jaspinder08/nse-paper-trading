"""Pydantic schemas for Market Data, Instruments, and Ingestion APIs."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str
    exchange: str
    token: Optional[str] = None
    segment: str
    instrument_type: str
    lot_size: int
    tick_size: float
    is_tradable: bool
    data_source: str
    last_verified_at: Optional[datetime] = None


class MarketCalendarItem(BaseModel):
    date: date
    is_trading_day: bool
    session_type: str
    market_open_time: Optional[datetime] = None
    market_close_time: Optional[datetime] = None
    description: Optional[str] = None
    holiday_reason: Optional[str] = None


class MarketStatusResponse(BaseModel):
    current_time_ist: str
    is_market_open: bool
    session_type: str
    session_description: str
    current_date: str
    next_open: Optional[str] = None
    next_close: Optional[str] = None
    data_source: str
    last_verified_at: str


class CandleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candle_timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: str


class IngestionJobCreateRequest(BaseModel):
    symbol: Optional[str] = Field(default=None, description="Specific symbol or null for Nifty 50 universe")
    start_date: date = Field(description="Start date for historical candles (YYYY-MM-DD)")
    end_date: date = Field(description="End date for historical candles (YYYY-MM-DD)")
    timeframe: str = Field(default="5m", description="Candle timeframe e.g. 5m, 15m")


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    symbol: Optional[str] = None
    timeframe: str
    start_date: date
    end_date: date
    status: str
    candles_ingested: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DataQualityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    check_type: str
    severity: str
    description: str
    candle_timestamp: Optional[datetime] = None
    detected_at: datetime
