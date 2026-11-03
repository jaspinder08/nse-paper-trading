"""Opening Range Breakout (ORB) strategy implementation for NSE Indian Equities.

Strict Phase 1 / Phase 2 Rules (from Project Specification):
- Timeframe: 5-minute completed OHLCV candles
- Opening Range: First three completed 5-minute bars (09:15:00 to 09:30:00 IST)
  * Bar 1: 09:15 to 09:20 IST
  * Bar 2: 09:20 to 09:25 IST
  * Bar 3: 09:25 to 09:30 IST
- Range bounds:
  * orb_high = max(highs)
  * orb_low  = min(lows)
  * orb_volume_avg = mean(volumes)
- Trigger: Completed 5-minute bar closes strictly above orb_high
- Volume filter: Breakout bar volume >= volume_multiplier * orb_volume_avg
- Stop Loss: Set at orb_low (strictly positive initial risk)
- Target: entry_price + (reward_risk_ratio * initial_risk), default 1.5:1
- Entry Cutoff: Configurable cutoff time (default 14:30 IST), no new entries after cutoff
- Position handling: Long-only, strictly one signal per symbol per trading day
- Calculations: Deterministic, exact Decimal arithmetic for price levels
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
import logging
from typing import Any, Dict, List, Optional, Union

from shared.market_time import IST_ZONE, to_ist
from trading_engine.market_data.types import HistoricalCandle
from trading_engine.strategy.base import BaseStrategy

logger = logging.getLogger("orb_strategy")


def _to_decimal(value: Union[Decimal, float, int, str]) -> Decimal:
    """Helper to convert numeric values to Decimal with clean precision."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class OpeningRange:
    """Represents the 09:15-09:30 IST opening range for an instrument."""
    session_date: date
    high: Decimal
    low: Decimal
    avg_volume: float
    bar_count: int
    is_valid: bool
    invalid_reason: Optional[str] = None

    @property
    def range_size(self) -> Decimal:
        return self.high - self.low


@dataclass(frozen=True)
class ORBSignal:
    """Structured, explainable Opening Range Breakout signal."""
    symbol: str
    signal_type: str  # Strictly "LONG"
    timestamp: datetime
    entry_price: Decimal
    stop_loss: Decimal
    target_price: Decimal
    initial_risk: Decimal
    reward_risk_ratio: float
    orb_high: Decimal
    orb_low: Decimal
    candle_close: Decimal
    candle_volume: int
    orb_avg_volume: float
    volume_ratio: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert signal to serializable dictionary."""
        data = asdict(self)
        # Format timestamps and Decimals
        data["timestamp"] = self.timestamp.isoformat()
        data["entry_price"] = float(self.entry_price)
        data["stop_loss"] = float(self.stop_loss)
        data["target_price"] = float(self.target_price)
        data["initial_risk"] = float(self.initial_risk)
        data["orb_high"] = float(self.orb_high)
        data["orb_low"] = float(self.orb_low)
        data["candle_close"] = float(self.candle_close)
        return data


class ORBStrategy(BaseStrategy):
    """High-reliability, deterministic Opening Range Breakout (ORB) strategy."""

    RANGE_START_TIME = time(9, 15, 0)
    RANGE_END_TIME = time(9, 30, 0)

    def __init__(
        self,
        range_minutes: int = 15,
        timeframe_minutes: int = 5,
        volume_multiplier: float = 1.0,
        reward_risk_ratio: float = 1.5,
        entry_cutoff_time: time = time(14, 30, 0),
        min_range_pct: float = 0.0005,  # 0.05% minimum range to filter flat lines
    ) -> None:
        super().__init__(name="ORB_STRATEGY")
        self.range_minutes = range_minutes
        self.timeframe_minutes = timeframe_minutes
        self.expected_range_bars = range_minutes // timeframe_minutes  # 15 // 5 = 3
        self.volume_multiplier = volume_multiplier
        self.reward_risk_ratio = reward_risk_ratio
        self.entry_cutoff_time = entry_cutoff_time
        self.min_range_pct = min_range_pct

    def _normalize_candle(self, c: Union[HistoricalCandle, Dict[str, Any]]) -> Dict[str, Any]:
        """Normalize candle representation to standard dictionary format."""
        if isinstance(c, HistoricalCandle):
            dt = to_ist(c.timestamp)
            return {
                "timestamp": dt,
                "open": _to_decimal(c.open),
                "high": _to_decimal(c.high),
                "low": _to_decimal(c.low),
                "close": _to_decimal(c.close),
                "volume": int(c.volume),
                "complete": bool(c.complete),
            }
        
        # Dict format
        ts = c["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        dt = to_ist(ts)
        return {
            "timestamp": dt,
            "open": _to_decimal(c["open"]),
            "high": _to_decimal(c["high"]),
            "low": _to_decimal(c["low"]),
            "close": _to_decimal(c["close"]),
            "volume": int(c["volume"]),
            "complete": bool(c.get("complete", True)),
        }

    def calculate_opening_range(
        self,
        candles: List[Union[HistoricalCandle, Dict[str, Any]]],
        target_date: Optional[date] = None,
    ) -> OpeningRange:
        """Calculate high, low, and average volume from the first three 5m bars (09:15-09:30 IST)."""
        if not candles:
            return OpeningRange(
                session_date=target_date or date.today(),
                high=Decimal("0"),
                low=Decimal("0"),
                avg_volume=0.0,
                bar_count=0,
                is_valid=False,
                invalid_reason="No candles provided.",
            )

        normalized = [self._normalize_candle(c) for c in candles]
        
        # Resolve target session date
        if target_date is None:
            target_date = normalized[0]["timestamp"].date()

        # Filter strictly for the target session's 09:15:00 to 09:29:59 IST bars
        # For 5-minute bars starting at 09:15, 09:20, and 09:25:
        range_bars: List[Dict[str, Any]] = []
        for c in normalized:
            dt = c["timestamp"]
            if dt.date() != target_date:
                continue

            # Standard bar start time check: 09:15 <= start_time < 09:30
            bar_time = dt.time()
            if self.RANGE_START_TIME <= bar_time < self.RANGE_END_TIME:
                range_bars.append(c)

        # Sort chronologically by timestamp
        range_bars.sort(key=lambda x: x["timestamp"])

        # Validate range bar count
        if len(range_bars) < self.expected_range_bars:
            return OpeningRange(
                session_date=target_date,
                high=Decimal("0"),
                low=Decimal("0"),
                avg_volume=0.0,
                bar_count=len(range_bars),
                is_valid=False,
                invalid_reason=(
                    f"Insufficient opening range bars: found {len(range_bars)} "
                    f"of {self.expected_range_bars} expected 5m bars between 09:15 and 09:30 IST."
                ),
            )

        # Truncate to first expected_range_bars in case of redundant timestamps
        selected_bars = range_bars[: self.expected_range_bars]

        # Validate OHLC consistency
        for i, bar in enumerate(selected_bars, 1):
            if not bar["complete"]:
                return OpeningRange(
                    session_date=target_date,
                    high=Decimal("0"),
                    low=Decimal("0"),
                    avg_volume=0.0,
                    bar_count=len(selected_bars),
                    is_valid=False,
                    invalid_reason=f"Opening range bar #{i} ({bar['timestamp']}) is marked incomplete.",
                )
            if bar["high"] < bar["low"] or bar["open"] <= 0 or bar["close"] <= 0:
                return OpeningRange(
                    session_date=target_date,
                    high=Decimal("0"),
                    low=Decimal("0"),
                    avg_volume=0.0,
                    bar_count=len(selected_bars),
                    is_valid=False,
                    invalid_reason=f"Opening range bar #{i} has invalid OHLC prices: H={bar['high']}, L={bar['low']}.",
                )
            if bar["volume"] < 0:
                return OpeningRange(
                    session_date=target_date,
                    high=Decimal("0"),
                    low=Decimal("0"),
                    avg_volume=0.0,
                    bar_count=len(selected_bars),
                    is_valid=False,
                    invalid_reason=f"Opening range bar #{i} has negative volume: {bar['volume']}.",
                )

        high = max(b["high"] for b in selected_bars)
        low = min(b["low"] for b in selected_bars)
        avg_volume = sum(b["volume"] for b in selected_bars) / float(len(selected_bars))

        # Check for degenerate range (zero or extremely narrow range)
        if high <= low:
            return OpeningRange(
                session_date=target_date,
                high=high,
                low=low,
                avg_volume=avg_volume,
                bar_count=len(selected_bars),
                is_valid=False,
                invalid_reason=f"Degenerate opening range: high ({high}) <= low ({low}).",
            )

        range_pct = float((high - low) / low)
        if range_pct < self.min_range_pct:
            return OpeningRange(
                session_date=target_date,
                high=high,
                low=low,
                avg_volume=avg_volume,
                bar_count=len(selected_bars),
                is_valid=False,
                invalid_reason=f"Opening range too narrow ({range_pct * 100:.3f}% < {self.min_range_pct * 100:.3f}%).",
            )

        return OpeningRange(
            session_date=target_date,
            high=high,
            low=low,
            avg_volume=avg_volume,
            bar_count=len(selected_bars),
            is_valid=True,
            invalid_reason=None,
        )

    def evaluate_candle(
        self,
        candle: Union[HistoricalCandle, Dict[str, Any]],
        opening_range: OpeningRange,
        symbol: str,
    ) -> Optional[ORBSignal]:
        """Evaluate a single completed 5-minute candle against the opening range.

        Returns an ORBSignal if breakout occurs and satisfies all filters, else None.
        """
        if not opening_range.is_valid:
            logger.debug("Symbol %s rejected: Invalid opening range (%s)", symbol, opening_range.invalid_reason)
            return None

        c = self._normalize_candle(candle)

        # Filter 1: Candle must be completed
        if not c["complete"]:
            logger.debug("Symbol %s: Candle at %s is incomplete. Ignored.", symbol, c["timestamp"])
            return None

        # Filter 2: Session date must match opening range date
        if c["timestamp"].date() != opening_range.session_date:
            logger.debug("Symbol %s: Candle date %s does not match range date %s", symbol, c["timestamp"].date(), opening_range.session_date)
            return None

        # Filter 3: Candle start time must be strictly after opening range (>= 09:30:00 IST)
        bar_time = c["timestamp"].time()
        if bar_time < self.RANGE_END_TIME:
            return None

        # Filter 4: Entry Cutoff time enforcement (no new entries after cutoff)
        if bar_time > self.entry_cutoff_time:
            logger.debug("Symbol %s: Candle at %s is after entry cutoff (%s)", symbol, bar_time, self.entry_cutoff_time)
            return None

        # Filter 5: Price Breakout Condition (close must be strictly above opening range high)
        close_price = c["close"]
        if close_price <= opening_range.high:
            return None

        # Filter 6: Volume Filter (breakout volume >= multiplier * opening range avg volume)
        volume = c["volume"]
        min_required_volume = self.volume_multiplier * opening_range.avg_volume
        if volume < min_required_volume:
            logger.debug(
                "Symbol %s: Breakout at %s rejected by volume filter (%d < required %.1f)",
                symbol, c["timestamp"], volume, min_required_volume
            )
            return None

        # Calculate exact risk and target levels
        entry_price = close_price
        stop_loss = opening_range.low
        initial_risk = entry_price - stop_loss

        if initial_risk <= Decimal("0"):
            logger.warning("Symbol %s: Non-positive risk (entry=%s, sl=%s)", symbol, entry_price, stop_loss)
            return None

        ratio_dec = Decimal(str(self.reward_risk_ratio))
        target_price = (entry_price + (ratio_dec * initial_risk)).quantize(Decimal("0.05"), rounding=ROUND_HALF_UP)
        stop_loss = stop_loss.quantize(Decimal("0.05"), rounding=ROUND_HALF_UP)
        entry_price = entry_price.quantize(Decimal("0.05"), rounding=ROUND_HALF_UP)
        initial_risk = (entry_price - stop_loss).quantize(Decimal("0.05"), rounding=ROUND_HALF_UP)

        volume_ratio = (volume / opening_range.avg_volume) if opening_range.avg_volume > 0 else 1.0

        reason = (
            f"5m candle close ₹{entry_price:.2f} broke above ORB high ₹{opening_range.high:.2f} "
            f"with volume {volume:,} ({volume_ratio:.2f}x ORB avg {opening_range.avg_volume:,.0f}). "
            f"Target: ₹{target_price:.2f} (1:{self.reward_risk_ratio}), SL: ₹{stop_loss:.2f}."
        )

        return ORBSignal(
            symbol=symbol.upper(),
            signal_type="LONG",
            timestamp=c["timestamp"],
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            initial_risk=initial_risk,
            reward_risk_ratio=self.reward_risk_ratio,
            orb_high=opening_range.high,
            orb_low=opening_range.low,
            candle_close=close_price,
            candle_volume=volume,
            orb_avg_volume=opening_range.avg_volume,
            volume_ratio=round(volume_ratio, 2),
            reason=reason,
        )

    def evaluate(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """BaseStrategy compliance: evaluate candles for symbol and return first valid signal."""
        symbol = market_data.get("symbol", "")
        candles = market_data.get("candles", [])
        if not candles:
            return None

        opening_range = self.calculate_opening_range(candles)
        if not opening_range.is_valid:
            return None

        # Check each subsequent completed candle chronologically
        for candle in candles:
            signal = self.evaluate_candle(candle, opening_range, symbol)
            if signal is not None:
                return signal.to_dict()

        return None
