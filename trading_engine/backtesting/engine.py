"""Historical Backtesting Engine for NSE Intraday Paper Trading (Phase 3 / FR-10).

Strict Rules & Invariants:
- Zero Look-Ahead Bias: Bar-by-bar chronological replay.
- Pure Python & Deterministic Math (Decimal / Float).
- Accurate Execution Slippage & NSE Statutory Charges via NSECostModel.
- Strictly long-only cash equities (Nifty 50 constituents).
- Conservative same-bar stop/target conflict handling (Stop Loss priority).
- Risk Gatekeepers: ₹75 daily loss circuit breaker, 3 trades/day, 10% cash reserve.
- Comprehensive metrics: Gross/Net P&L, Win Rate, Profit Factor, Expectancy, Max Drawdown.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_FLOOR
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.instrument import Instrument
from backend.app.models.market_candle import MarketCandle
from shared.costs import NSECostModel, cost_model

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class BacktestTradeResult:
    """Individual trade result simulated during backtesting."""
    symbol: str
    instrument_id: Optional[int]
    entry_time: str
    exit_time: str
    side: str
    quantity: int
    requested_entry_price: float
    entry_price: float
    requested_exit_price: float
    exit_price: float
    gross_pnl: float
    total_charges: float
    slippage_cost: float
    net_pnl: float
    return_pct: float
    exit_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BacktestResult:
    """Comprehensive performance metrics summary for a backtest simulation run."""
    strategy_name: str
    symbols: List[str]
    timeframe: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    net_pnl: float
    return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float
    loss_rate: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    total_charges: float
    total_slippage: float
    average_win: float
    average_loss: float
    payoff_ratio: float
    expectancy: float
    max_drawdown_amount: float
    max_drawdown_pct: float
    largest_win: float
    largest_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    trades: List[BacktestTradeResult] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["trades"] = [t.to_dict() if isinstance(t, BacktestTradeResult) else t for t in self.trades]
        return data


@dataclass
class _OpenPosition:
    symbol: str
    instrument_id: Optional[int]
    entry_time: datetime
    entry_price: float
    stop_loss: float
    target_price: float
    quantity: int
    entry_turnover: float
    entry_charges: float
    entry_slippage: float


class BacktestEngine:
    """Intraday ORB Historical Simulation Engine with full statutory costs."""

    def __init__(
        self,
        initial_capital: float = 5000.0,
        max_risk_per_trade: float = 25.0,
        max_daily_loss: float = 75.0,
        max_trades_per_day: int = 3,
        max_open_positions: int = 3,
        cash_reserve_pct: float = 0.10,
        max_position_pct: float = 0.25,
        target_multiple: float = 1.5,
        volume_multiplier: float = 1.2,
        tick_size: float = 0.05,
        cost_calculator: Optional[NSECostModel] = None,
    ) -> None:
        self.initial_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_trades_per_day = max_trades_per_day
        self.max_open_positions = max_open_positions
        self.cash_reserve_pct = cash_reserve_pct
        self.max_position_pct = max_position_pct
        self.target_multiple = target_multiple
        self.volume_multiplier = volume_multiplier
        self.tick_size = tick_size
        self.costs = cost_calculator or cost_model

    async def run(
        self,
        strategy_name: str = "ORB_STRATEGY",
        symbols: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeframe: str = "5m",
        candles_by_symbol: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> BacktestResult:
        """Execute historical backtesting replay on candle data."""
        symbols = [s.upper() for s in (symbols or ["RELIANCE", "TCS", "INFY"])]
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = date.today()

        # Step 1: Ingest and group candles chronologically
        data_by_symbol = candles_by_symbol
        if data_by_symbol is None and db_session is not None:
            data_by_symbol = await self._fetch_candles_from_db(
                db_session=db_session,
                symbols=symbols,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )

        if not data_by_symbol:
            return self._empty_result(
                strategy_name=strategy_name,
                symbols=symbols,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )

        # Step 2: Replay simulation
        return self._replay_chronological(
            strategy_name=strategy_name,
            symbols=symbols,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            candles_by_symbol=data_by_symbol,
        )

    async def _fetch_candles_from_db(
        self,
        db_session: AsyncSession,
        symbols: List[str],
        timeframe: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch candles from market_candles joined with instruments."""
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)

        stmt = (
            select(MarketCandle, Instrument.symbol)
            .join(Instrument, MarketCandle.instrument_id == Instrument.id)
            .where(
                Instrument.symbol.in_(symbols),
                MarketCandle.timeframe == timeframe,
                MarketCandle.candle_timestamp >= start_dt,
                MarketCandle.candle_timestamp <= end_dt,
            )
            .order_by(MarketCandle.candle_timestamp.asc())
        )
        res = await db_session.execute(stmt)
        candles_by_sym: Dict[str, List[Dict[str, Any]]] = {s: [] for s in symbols}
        for candle, sym in res.all():
            candles_by_sym[sym].append({
                "instrument_id": candle.instrument_id,
                "candle_timestamp": candle.candle_timestamp,
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": int(candle.volume),
            })
        return candles_by_sym

    def _replay_chronological(
        self,
        strategy_name: str,
        symbols: List[str],
        timeframe: str,
        start_date: date,
        end_date: date,
        candles_by_symbol: Dict[str, List[Dict[str, Any]]],
    ) -> BacktestResult:
        """Replay historical candles bar-by-bar across trading sessions."""
        current_capital = float(self.initial_capital)
        peak_capital = current_capital
        max_drawdown_amount = 0.0
        max_drawdown_pct = 0.0

        all_trades: List[BacktestTradeResult] = []
        equity_curve: List[Dict[str, Any]] = [{
            "timestamp": start_date.isoformat(),
            "capital": current_capital,
            "drawdown_pct": 0.0,
        }]

        # Group candles by trading day across all symbols
        candles_by_day: Dict[date, Dict[str, List[Dict[str, Any]]]] = {}
        for sym, c_list in candles_by_symbol.items():
            for c in c_list:
                ts = c["candle_timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=IST)
                else:
                    ts = ts.astimezone(IST)
                c_normalized = dict(c)
                c_normalized["candle_timestamp"] = ts
                d = ts.date()
                candles_by_day.setdefault(d, {}).setdefault(sym, []).append(c_normalized)

        # Sort trading days chronologically
        sorted_days = sorted(candles_by_day.keys())

        for trade_day in sorted_days:
            day_data = candles_by_day[trade_day]

            # Daily Session Variables
            realized_daily_pnl = 0.0
            daily_trade_count = 0
            daily_circuit_breaker = False
            traded_symbols_today: Set[str] = set()
            open_positions: Dict[str, _OpenPosition] = {}

            # Collect all distinct candle timestamps for this day in ascending order
            all_timestamps: Set[datetime] = set()
            for sym_candles in day_data.values():
                for c in sym_candles:
                    all_timestamps.add(c["candle_timestamp"])
            sorted_timestamps = sorted(all_timestamps)

            # Map candles by (symbol, timestamp)
            candle_lookup: Dict[Tuple[str, datetime], Dict[str, Any]] = {}
            for sym, sym_candles in day_data.items():
                for c in sym_candles:
                    candle_lookup[(sym, c["candle_timestamp"])] = c

            # Track 09:15-09:30 range bars for each symbol
            orb_bars: Dict[str, List[Dict[str, Any]]] = {s: [] for s in symbols}
            orb_ranges: Dict[str, Dict[str, float]] = {}

            # Timeline replay
            for ts in sorted_timestamps:
                bar_time = ts.time()

                # 1. Opening range formation (09:15 - 09:30 IST)
                if bar_time < time(9, 30):
                    for sym in symbols:
                        c = candle_lookup.get((sym, ts))
                        if c:
                            orb_bars[sym].append(c)
                    continue

                # Once 09:30 arrives, finalize ORB ranges if not already done
                for sym in symbols:
                    if sym not in orb_ranges and len(orb_bars[sym]) >= 3:
                        highs = [b["high"] for b in orb_bars[sym][:3]]
                        lows = [b["low"] for b in orb_bars[sym][:3]]
                        vols = [b["volume"] for b in orb_bars[sym][:3]]
                        orb_ranges[sym] = {
                            "high": max(highs),
                            "low": min(lows),
                            "avg_volume": sum(vols) / len(vols) if vols else 1.0,
                        }

                # 2. Monitor open positions against the current bar
                symbols_to_close: List[Tuple[str, float, str]] = []
                for sym, pos in list(open_positions.items()):
                    c = candle_lookup.get((sym, ts))
                    if not c:
                        continue

                    bar_low = c["low"]
                    bar_high = c["high"]
                    bar_close = c["close"]

                    # Conservative same-bar conflict: Stop Loss has absolute priority
                    if bar_low <= pos.stop_loss and bar_high >= pos.target_price:
                        symbols_to_close.append((sym, pos.stop_loss, "STOP_LOSS_HIT"))
                    elif bar_low <= pos.stop_loss:
                        symbols_to_close.append((sym, pos.stop_loss, "STOP_LOSS_HIT"))
                    elif bar_high >= pos.target_price:
                        symbols_to_close.append((sym, pos.target_price, "TARGET_HIT"))
                    elif bar_time >= time(15, 15) or ts == sorted_timestamps[-1]:
                        # End-of-day square-off at 15:15 IST
                        symbols_to_close.append((sym, bar_close, "EOD_SQUARE_OFF"))

                # Execute closes
                for sym, exit_req_price, exit_reason in symbols_to_close:
                    pos = open_positions.pop(sym)
                    # Adverse slippage on sell (exit): exit_req_price - tick_size
                    exit_fill = round(exit_req_price - self.tick_size, 2)
                    exit_cost_breakdown = self.costs.calculate_costs(
                        price=exit_req_price,
                        quantity=pos.quantity,
                        action="SELL",
                        tick_size=self.tick_size,
                    )

                    gross_pnl = round((exit_fill - pos.entry_price) * pos.quantity, 2)
                    total_charges = round(pos.entry_charges + exit_cost_breakdown.total_charges, 2)
                    total_slippage = round(pos.entry_slippage + exit_cost_breakdown.slippage_cost, 2)
                    net_pnl = round(gross_pnl - total_charges, 2)
                    return_pct = round((net_pnl / pos.entry_turnover) * 100, 2) if pos.entry_turnover > 0 else 0.0

                    trade_result = BacktestTradeResult(
                        symbol=sym,
                        instrument_id=pos.instrument_id,
                        entry_time=pos.entry_time.isoformat(),
                        exit_time=ts.isoformat(),
                        side="LONG",
                        quantity=pos.quantity,
                        requested_entry_price=round(pos.entry_price - self.tick_size, 2),
                        entry_price=pos.entry_price,
                        requested_exit_price=round(exit_req_price, 2),
                        exit_price=exit_fill,
                        gross_pnl=gross_pnl,
                        total_charges=total_charges,
                        slippage_cost=total_slippage,
                        net_pnl=net_pnl,
                        return_pct=return_pct,
                        exit_reason=exit_reason,
                    )
                    all_trades.append(trade_result)

                    # Update capital and daily P&L
                    current_capital += (pos.entry_turnover + net_pnl)
                    realized_daily_pnl += net_pnl

                    # Check daily circuit breaker (₹75)
                    if realized_daily_pnl <= -self.max_daily_loss:
                        daily_circuit_breaker = True

                    # Update equity curve and drawdowns
                    if current_capital > peak_capital:
                        peak_capital = current_capital
                    dd_amount = peak_capital - current_capital
                    dd_pct = (dd_amount / peak_capital * 100) if peak_capital > 0 else 0.0
                    if dd_amount > max_drawdown_amount:
                        max_drawdown_amount = dd_amount
                    if dd_pct > max_drawdown_pct:
                        max_drawdown_pct = dd_pct

                    equity_curve.append({
                        "timestamp": ts.isoformat(),
                        "capital": round(current_capital, 2),
                        "drawdown_pct": round(dd_pct, 2),
                    })

                # 3. Check for new breakout entry signals
                if bar_time < time(14, 30) and not daily_circuit_breaker:
                    if daily_trade_count < self.max_trades_per_day and len(open_positions) < self.max_open_positions:
                        for sym in symbols:
                            if sym in open_positions or sym in traded_symbols_today:
                                continue
                            if sym not in orb_ranges:
                                continue

                            c = candle_lookup.get((sym, ts))
                            if not c:
                                continue

                            orb_range = orb_ranges[sym]
                            orb_high = orb_range["high"]
                            orb_low = orb_range["low"]
                            orb_avg_vol = orb_range["avg_volume"]

                            # Breakout conditions: close > orb_high and volume >= multiplier * orb_avg_volume
                            is_breakout = (
                                c["close"] > orb_high
                                and c["volume"] >= (self.volume_multiplier * orb_avg_vol)
                            )
                            if not is_breakout:
                                continue

                            # Long Entry Setup
                            entry_req_price = c["close"]
                            # Adverse slippage on BUY: entry_req_price + tick_size
                            entry_fill_price = round(entry_req_price + self.tick_size, 2)
                            stop_loss = orb_low
                            risk_per_share = entry_fill_price - stop_loss
                            if risk_per_share <= 0:
                                continue

                            # Reward-to-risk: target at least 1.5x risk
                            target_price = round(entry_fill_price + (self.target_multiple * risk_per_share), 2)

                            # Dynamic Position Sizing (PDF Section 9.1)
                            # 10% cash reserve preservation
                            reserve_capital = current_capital * self.cash_reserve_pct
                            deployable_capital = max(0.0, current_capital - reserve_capital)
                            # Max position size cap (25% of total capital)
                            max_pos_val = current_capital * self.max_position_pct
                            available_pos_capital = min(deployable_capital, max_pos_val)

                            qty_by_risk = math.floor(self.max_risk_per_trade / risk_per_share)
                            qty_by_capital = math.floor(available_pos_capital / entry_fill_price)
                            quantity = min(qty_by_risk, qty_by_capital)

                            if quantity < 1:
                                continue

                            # Calculate initial entry costs
                            entry_cost_breakdown = self.costs.calculate_costs(
                                price=entry_req_price,
                                quantity=quantity,
                                action="BUY",
                                tick_size=self.tick_size,
                            )
                            turnover = quantity * entry_fill_price

                            # Open position
                            open_positions[sym] = _OpenPosition(
                                symbol=sym,
                                instrument_id=c.get("instrument_id"),
                                entry_time=ts,
                                entry_price=entry_fill_price,
                                stop_loss=stop_loss,
                                target_price=target_price,
                                quantity=quantity,
                                entry_turnover=turnover,
                                entry_charges=entry_cost_breakdown.total_charges,
                                entry_slippage=entry_cost_breakdown.slippage_cost,
                            )
                            current_capital -= turnover
                            daily_trade_count += 1
                            traded_symbols_today.add(sym)

                            if daily_trade_count >= self.max_trades_per_day or len(open_positions) >= self.max_open_positions:
                                break

        # Step 3: Compute final metrics
        return self._calculate_metrics(
            strategy_name=strategy_name,
            symbols=symbols,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=current_capital,
            trades=all_trades,
            equity_curve=equity_curve,
            max_drawdown_amount=max_drawdown_amount,
            max_drawdown_pct=max_drawdown_pct,
        )

    def _calculate_metrics(
        self,
        strategy_name: str,
        symbols: List[str],
        timeframe: str,
        start_date: date,
        end_date: date,
        initial_capital: float,
        final_capital: float,
        trades: List[BacktestTradeResult],
        equity_curve: List[Dict[str, Any]],
        max_drawdown_amount: float,
        max_drawdown_pct: float,
    ) -> BacktestResult:
        """Compute performance evaluation metrics strictly adhering to Section 15 of project report."""
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.net_pnl > 0]
        losing_trades = [t for t in trades if t.net_pnl < 0]
        breakeven_trades = [t for t in trades if t.net_pnl == 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        be_count = len(breakeven_trades)

        win_rate = round((win_count / total_trades) * 100, 2) if total_trades > 0 else 0.0
        loss_rate = round((loss_count / total_trades) * 100, 2) if total_trades > 0 else 0.0

        gross_profit = round(sum(t.net_pnl for t in winning_trades), 2)
        gross_loss = round(abs(sum(t.net_pnl for t in losing_trades)), 2)

        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 2)
        elif gross_profit > 0:
            profit_factor = 999.0
        else:
            profit_factor = 0.0

        total_charges = round(sum(t.total_charges for t in trades), 2)
        total_slippage = round(sum(t.slippage_cost for t in trades), 2)
        net_pnl = round(final_capital - initial_capital, 2)
        return_pct = round((net_pnl / initial_capital) * 100, 2) if initial_capital > 0 else 0.0

        average_win = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        average_loss = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0

        payoff_ratio = round(average_win / average_loss, 2) if average_loss > 0 else 0.0
        expectancy = round(((win_rate / 100.0) * average_win) - ((loss_rate / 100.0) * average_loss), 2)

        largest_win = round(max((t.net_pnl for t in trades), default=0.0), 2)
        largest_loss = round(min((t.net_pnl for t in trades), default=0.0), 2)

        # Consecutive wins / losses
        max_cons_wins = 0
        curr_cons_wins = 0
        max_cons_losses = 0
        curr_cons_losses = 0
        for t in trades:
            if t.net_pnl > 0:
                curr_cons_wins += 1
                curr_cons_losses = 0
                max_cons_wins = max(max_cons_wins, curr_cons_wins)
            elif t.net_pnl < 0:
                curr_cons_losses += 1
                curr_cons_wins = 0
                max_cons_losses = max(max_cons_losses, curr_cons_losses)
            else:
                curr_cons_wins = 0
                curr_cons_losses = 0

        return BacktestResult(
            strategy_name=strategy_name,
            symbols=symbols,
            timeframe=timeframe,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            initial_capital=round(initial_capital, 2),
            final_capital=round(final_capital, 2),
            net_pnl=net_pnl,
            return_pct=return_pct,
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            breakeven_trades=be_count,
            win_rate=win_rate,
            loss_rate=loss_rate,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            total_charges=total_charges,
            total_slippage=total_slippage,
            average_win=average_win,
            average_loss=average_loss,
            payoff_ratio=payoff_ratio,
            expectancy=expectancy,
            max_drawdown_amount=round(max_drawdown_amount, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_consecutive_wins=max_cons_wins,
            max_consecutive_losses=max_cons_losses,
            trades=trades,
            equity_curve=equity_curve,
        )

    def _empty_result(
        self,
        strategy_name: str,
        symbols: List[str],
        timeframe: str,
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        """Return a clean empty result when no candle data is available."""
        return BacktestResult(
            strategy_name=strategy_name,
            symbols=symbols,
            timeframe=timeframe,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            net_pnl=0.0,
            return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=0.0,
            loss_rate=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            total_charges=0.0,
            total_slippage=0.0,
            average_win=0.0,
            average_loss=0.0,
            payoff_ratio=0.0,
            expectancy=0.0,
            max_drawdown_amount=0.0,
            max_drawdown_pct=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            trades=[],
            equity_curve=[{
                "timestamp": start_date.isoformat(),
                "capital": self.initial_capital,
                "drawdown_pct": 0.0,
            }],
        )
