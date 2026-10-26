# NSE Paper-Trading & Intraday Research System: Requirements Specification

## 1. System Overview
The **NSE Paper-Trading & Intraday Research System** is a modular, high-reliability, local application designed for algorithmic intraday trading research and simulation. It operates in strict simulation mode against National Stock Exchange (NSE) equities, with primary focus on NIFTY 50 intraday strategies (such as Opening Range Breakout - ORB).

## 2. Fundamental Safety Invariants
1. **Strict Paper Trading Only**: Under no circumstances shall real broker capital or live orders be placed.
2. **Broker Decoupling**: Trading engine strategies and execution modules operate against simulated execution abstractions. Live broker execution interfaces are permanently rejected.
3. **Risk Gatekeeping**: All strategy signals must pass through the Risk Validator (Daily Loss Limits, Max Open Positions, Maximum Capital Utilization) before generating paper orders.
4. **Audit Trail**: Every signal, approval/rejection, order fill, position adjustment, and risk evaluation must be durably recorded.
5. **Zero Hardcoded Credentials**: No API keys, client codes, TOTP secrets, passwords, or personal credentials may ever be committed to source control or hardcoded.

## 3. Technology Stack
- **Frontend**: Flutter (Cross-platform targeting Desktop Windows/macOS and Android mobile)
- **Backend**: Python FastAPI with async I/O and WebSocket streaming
- **Trading Engine**: Independent Python worker process with asynchronous loop
- **Primary Database**: SQLite 3 (WAL mode, busy timeout 10000ms, Foreign Keys enforced)
- **Database ORM**: SQLAlchemy 2.0 (Modern mapped_column declarative style)
- **Database Migrations**: Alembic
- **Data Validation & Settings**: Pydantic v2 & Pydantic-Settings
- **Testing**: Pytest & Pytest-Asyncio

## 4. Phase Breakdown
- **Phase 1 (Completed)**: System Foundation, Database Architecture, SQLite Migration (ADR-001), Independent Worker Lifecycle, Flutter Shell.
- **Phase 2 (Upcoming)**: Market Data Provider (Angel One SmartAPI adapter), Nifty 50 Scanner, ORB Strategy Calculations.
- **Phase 3 (Future)**: Historical Backtesting Framework and Metrics Engine.
- **Phase 4 (Future)**: Real-time Flutter UI Charts and Dashboard Integration.
