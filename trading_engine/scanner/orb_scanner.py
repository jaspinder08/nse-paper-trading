"""Stock scanner candidate for NIFTY 50 Opening Range Breakout (ORB).

Scans active Nifty 50 constituents against completed 5-minute candles to detect:
1. TRIGGERED: Valid breakout above ORB high with volume confirmation
2. PENDING_BREAKOUT: Valid range established, waiting for close above ORB high
3. RANGE_FORMING: In early morning session (09:15-09:30 IST) while range bars build
4. REJECTED_VOLUME: Price broke above ORB high but lacked volume filter confirmation
5. INVALID_RANGE / NO_DATA: Insufficient or invalid candles
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Union

from shared.market_time import now_ist, to_ist
from trading_engine.market_data.base import AbstractMarketDataProvider
from trading_engine.market_data.types import HistoricalCandle
from trading_engine.scanner.base import BaseScanner
from trading_engine.strategy.orb import OpeningRange, ORBSignal, ORBStrategy
from trading_engine.universe.nifty50 import get_nifty50_constituents

logger = logging.getLogger("orb_scanner")


@dataclass(frozen=True)
class ScanCandidate:
    """Represents the scan verdict and metrics for an individual stock."""
    symbol: str
    status: str  # "TRIGGERED", "PENDING_BREAKOUT", "RANGE_FORMING", "REJECTED_VOLUME", "NO_RANGE"
    current_price: float
    orb_high: Optional[float]
    orb_low: Optional[float]
    orb_range_pct: Optional[float]
    distance_to_high_pct: Optional[float]
    volume_ratio: Optional[float]
    signal: Optional[Dict[str, Any]]
    reason: str
    last_candle_time: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ORBScanner(BaseScanner):
    """Production intraday scanner for NIFTY 50 Opening Range Breakouts."""

    def __init__(
        self,
        strategy: Optional[ORBStrategy] = None,
        market_data_provider: Optional[AbstractMarketDataProvider] = None,
    ) -> None:
        self.strategy = strategy or ORBStrategy()
        self.market_data = market_data_provider

    def scan_symbol(
        self,
        symbol: str,
        candles: List[Union[HistoricalCandle, Dict[str, Any]]],
        target_date: Optional[date] = None,
    ) -> ScanCandidate:
        """Evaluate a symbol's intraday 5-minute candles and determine its ORB status."""
        symbol = symbol.upper()
        if not candles:
            return ScanCandidate(
                symbol=symbol,
                status="NO_DATA",
                current_price=0.0,
                orb_high=None,
                orb_low=None,
                orb_range_pct=None,
                distance_to_high_pct=None,
                volume_ratio=None,
                signal=None,
                reason="No candles available for evaluation.",
                last_candle_time=None,
            )

        # 1. Compute Opening Range (09:15-09:30 IST)
        opening_range: OpeningRange = self.strategy.calculate_opening_range(candles, target_date=target_date)

        # Get latest completed candle
        latest = candles[-1]
        norm_latest = self.strategy._normalize_candle(latest)
        current_price = float(norm_latest["close"])
        last_time_str = norm_latest["timestamp"].isoformat()

        if not opening_range.is_valid:
            # Check if we are still within the opening range window (09:15-09:30)
            if opening_range.bar_count < self.strategy.expected_range_bars:
                status = "RANGE_FORMING"
                reason = f"Opening range forming ({opening_range.bar_count}/{self.strategy.expected_range_bars} bars completed)."
            else:
                status = "INVALID_RANGE"
                reason = opening_range.invalid_reason or "Opening range validation failed."

            return ScanCandidate(
                symbol=symbol,
                status=status,
                current_price=current_price,
                orb_high=None,
                orb_low=None,
                orb_range_pct=None,
                distance_to_high_pct=None,
                volume_ratio=None,
                signal=None,
                reason=reason,
                last_candle_time=last_time_str,
            )

        orb_high_f = float(opening_range.high)
        orb_low_f = float(opening_range.low)
        range_pct = round(((orb_high_f - orb_low_f) / orb_low_f) * 100.0, 2)
        dist_pct = round(((current_price - orb_high_f) / orb_high_f) * 100.0, 2)

        # 2. Check for Breakout Trigger in post-09:30 completed candles
        triggered_signal: Optional[ORBSignal] = None
        rejected_by_volume: bool = False
        rejected_by_cutoff: bool = False
        highest_volume_ratio: float = 0.0

        for c in candles:
            norm_c = self.strategy._normalize_candle(c)
            bar_time = norm_c["timestamp"].time()

            # Skip candles inside the opening range
            if bar_time < self.strategy.RANGE_END_TIME:
                continue

            vol_ratio = (
                norm_c["volume"] / opening_range.avg_volume
                if opening_range.avg_volume > 0
                else 1.0
            )
            highest_volume_ratio = max(highest_volume_ratio, vol_ratio)

            # Check price condition
            if norm_c["close"] > opening_range.high:
                if bar_time > self.strategy.entry_cutoff_time:
                    rejected_by_cutoff = True
                    continue

                if norm_c["volume"] < self.strategy.volume_multiplier * opening_range.avg_volume:
                    rejected_by_volume = True
                    continue

                # Valid trigger!
                sig = self.strategy.evaluate_candle(c, opening_range, symbol)
                if sig is not None and triggered_signal is None:
                    triggered_signal = sig

        # 3. Categorize Status
        if triggered_signal is not None:
            return ScanCandidate(
                symbol=symbol,
                status="TRIGGERED",
                current_price=current_price,
                orb_high=orb_high_f,
                orb_low=orb_low_f,
                orb_range_pct=range_pct,
                distance_to_high_pct=dist_pct,
                volume_ratio=triggered_signal.volume_ratio,
                signal=triggered_signal.to_dict(),
                reason=triggered_signal.reason,
                last_candle_time=last_time_str,
            )

        if rejected_by_volume:
            return ScanCandidate(
                symbol=symbol,
                status="REJECTED_VOLUME",
                current_price=current_price,
                orb_high=orb_high_f,
                orb_low=orb_low_f,
                orb_range_pct=range_pct,
                distance_to_high_pct=dist_pct,
                volume_ratio=round(highest_volume_ratio, 2),
                signal=None,
                reason=f"Breakout above ₹{orb_high_f:.2f} detected, but failed volume filter ({highest_volume_ratio:.2f}x < {self.strategy.volume_multiplier}x).",
                last_candle_time=last_time_str,
            )

        if rejected_by_cutoff:
            return ScanCandidate(
                symbol=symbol,
                status="REJECTED_CUTOFF",
                current_price=current_price,
                orb_high=orb_high_f,
                orb_low=orb_low_f,
                orb_range_pct=range_pct,
                distance_to_high_pct=dist_pct,
                volume_ratio=round(highest_volume_ratio, 2),
                signal=None,
                reason=f"Breakout occurred after entry cutoff time ({self.strategy.entry_cutoff_time}).",
                last_candle_time=last_time_str,
            )

        # Standard pending breakout
        return ScanCandidate(
            symbol=symbol,
            status="PENDING_BREAKOUT",
            current_price=current_price,
            orb_high=orb_high_f,
            orb_low=orb_low_f,
            orb_range_pct=range_pct,
            distance_to_high_pct=dist_pct,
            volume_ratio=round(highest_volume_ratio, 2),
            signal=None,
            reason=f"Valid ORB established [₹{orb_low_f:.2f} - ₹{orb_high_f:.2f}]. Price {dist_pct:+.2f}% vs high.",
            last_candle_time=last_time_str,
        )

    async def scan(
        self,
        universe: Optional[List[str]] = None,
        candles_by_symbol: Optional[Dict[str, List[Any]]] = None,
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Scan given universe (or official Nifty 50) and return categorized breakout candidates."""
        ref_date = as_of_date or now_ist().date()
        if universe is None:
            universe = get_nifty50_constituents(ref_date)

        results: List[ScanCandidate] = []

        if candles_by_symbol is not None:
            for sym in universe:
                c_list = candles_by_symbol.get(sym, [])
                candidate = self.scan_symbol(sym, c_list, target_date=ref_date)
                results.append(candidate)
        elif self.market_data is not None:
            for sym in universe:
                try:
                    c_list = await self.market_data.fetch_candles(
                        symbol=sym,
                        timeframe="5m",
                        from_dt=datetime.combine(ref_date, datetime.min.time()),
                        to_dt=datetime.combine(ref_date, datetime.max.time()),
                    )
                    candidate = self.scan_symbol(sym, c_list, target_date=ref_date)
                    results.append(candidate)
                except Exception as exc:
                    logger.warning("Error fetching scan candles for %s: %s", sym, exc)
                    results.append(
                        ScanCandidate(
                            symbol=sym,
                            status="ERROR",
                            current_price=0.0,
                            orb_high=None,
                            orb_low=None,
                            orb_range_pct=None,
                            distance_to_high_pct=None,
                            volume_ratio=None,
                            signal=None,
                            reason=f"Data fetch error: {exc}",
                            last_candle_time=None,
                        )
                    )
        else:
            # No data source provided
            for sym in universe:
                results.append(
                    ScanCandidate(
                        symbol=sym,
                        status="NO_DATA",
                        current_price=0.0,
                        orb_high=None,
                        orb_low=None,
                        orb_range_pct=None,
                        distance_to_high_pct=None,
                        volume_ratio=None,
                        signal=None,
                        reason="No candle data provider configured.",
                        last_candle_time=None,
                    )
                )

        # Prioritize:
        # 1. TRIGGERED first
        # 2. PENDING_BREAKOUT sorted by proximity to high (distance_to_high_pct descending, i.e., closest to 0% first)
        # 3. RANGE_FORMING
        # 4. REJECTED / NO_DATA
        status_priority = {
            "TRIGGERED": 0,
            "PENDING_BREAKOUT": 1,
            "RANGE_FORMING": 2,
            "REJECTED_VOLUME": 3,
            "REJECTED_CUTOFF": 4,
            "INVALID_RANGE": 5,
            "NO_DATA": 6,
            "ERROR": 7,
        }

        def sort_key(c: ScanCandidate):
            prio = status_priority.get(c.status, 99)
            # For pending breakout, closer to breakout is higher priority (e.g. -0.2% before -3.5%)
            dist = c.distance_to_high_pct if c.distance_to_high_pct is not None else -999.0
            return (prio, -dist)

        results.sort(key=sort_key)
        return [c.to_dict() for c in results]
