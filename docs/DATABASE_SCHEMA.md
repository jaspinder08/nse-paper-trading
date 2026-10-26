# Database Schema Specification

## 1. Primary Storage Engine
- **Engine**: SQLite 3 (Default, Local Single-User)
- **Path**: `./data/nse_paper_trading.db`
- **Key PRAGMAs**:
  - `journal_mode = WAL`
  - `busy_timeout = 10000`
  - `foreign_keys = ON`
  - `synchronous = NORMAL`

## 2. Entity Overview (13 Models)

| Entity Name | Table Name | Purpose | Primary Key | Key Constraints & Indexes |
|-------------|------------|---------|-------------|----------------------------|
| `TradingSession` | `trading_sessions` | Intraday trading session lifecycle and cumulative P&L | `id` (INTEGER) | `ix_trading_sessions_session_date` |
| `TradingConfig` | `trading_configs` | Dynamic key-value engine settings | `id` (INTEGER) | `key` (UNIQUE, indexed) |
| `Instrument` | `instruments` | NSE tradable equity symbol definition | `id` (INTEGER) | `symbol` (UNIQUE, indexed), `exchange`, `token` |
| `MarketCandle` | `market_candles` | OHLCV candlestick records across timeframes | `id` (INTEGER / BIGINT) | `uq_candle_instrument_timeframe_timestamp` (UNIQUE on instrument_id + timeframe + candle_timestamp) |
| `TradingSignal` | `trading_signals` | Strategy breakout and entry signals | `id` (INTEGER) | FK -> `instruments.id`, FK -> `trading_sessions.id`, `status` |
| `PaperOrder` | `paper_orders` | Simulated paper order records | `id` (INTEGER) | `is_paper = TRUE`, FK -> `instruments.id`, FK -> `trading_signals.id` |
| `Position` | `positions` | Active and closed simulated intraday positions | `id` (INTEGER) | FK -> `instruments.id`, `status` (OPEN/CLOSED) |
| `PortfolioSnapshot`| `portfolio_snapshots`| Periodic equity and margin snapshots | `id` (INTEGER) | FK -> `trading_sessions.id`, `snapshot_time` |
| `TradeLog` | `trade_logs` | Audit trail for order fills, stops, and exits | `id` (INTEGER) | FK -> `paper_orders.id`, FK -> `positions.id` |
| `RiskLog` | `risk_logs` | Audit trail for risk rule validations | `id` (INTEGER) | FK -> `trading_signals.id`, `check_name`, `passed` |
| `BacktestRun` | `backtest_runs` | Historical strategy simulation execution run | `id` (INTEGER) | `strategy_name`, `timeframe`, `win_rate` |
| `BacktestTrade` | `backtest_trades` | Individual trades within a backtest run | `id` (INTEGER) | FK -> `backtest_runs.id`, FK -> `instruments.id` |
| `SystemLog` | `system_logs` | Diagnostic and operational logs | `id` (INTEGER) | `level`, `module`, `logged_at` |
