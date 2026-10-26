# System Architecture Document

## 1. High-Level Architecture

The system consists of three independent decoupled processes communicating via shared local persistence and real-time network protocols:

```
┌─────────────────────────────────┐
│     Flutter Frontend Client     │
│   (Desktop Windows/macOS & App) │
└──────────────┬──────────────────┘
               │ HTTP REST / WebSocket (Real-Time Streams)
               ▼
┌─────────────────────────────────┐
│      FastAPI Backend Server     │
│       (app/main.py, /v1)        │
└──────────────┬──────────────────┘
               │ Async SQLAlchemy 2.0 (aiosqlite)
               ▼
┌────────────────────────────────────────────────────────┐
│             SQLite Database (WAL Mode)                 │
│           (./data/nse_paper_trading.db)                │
└──────────────▲─────────────────────────────────────────┘
               │ Async SQLAlchemy 2.0 (aiosqlite)
┌──────────────┴──────────────────┐
│      Trading Engine Worker      │
│     (trading_engine/worker.py)  │
│  - Scanner & ORB Strategy       │
│  - Risk Engine (Validator)      │
│  - Simulated Paper Executor     │
│  - Portfolio & Position State   │
└─────────────────────────────────┘
```

## 2. Decoupling & Independent Process Execution
- **Process Isolation**: Closing or restarting the Flutter frontend does not interrupt the FastAPI backend or the Trading Engine worker.
- **Worker Autonomy**: The Trading Engine runs as a dedicated Python daemon/process, polling market data feeds, evaluating strategy rules, and executing simulated paper trades.
- **Database Concurrency (SQLite WAL Mode)**:
  - Both FastAPI and Trading Engine connect to `sqlite+aiosqlite:///./data/nse_paper_trading.db`.
  - SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL`) enables concurrent readers alongside an active writer.
  - A busy timeout of 10,000ms (`PRAGMA busy_timeout=10000`) guarantees that write collisions automatically back off and retry without throwing lock errors.
  - Short, bounded write transactions ensure minimal database lock duration.

## 3. Future PostgreSQL Migration Path
The system is built on portable SQLAlchemy 2.0 types without database-specific vendor locks:
- No PostgreSQL-specific `JSONB`, `ARRAY`, or custom ENUMs are used in models.
- Alembic configuration supports both SQLite (with `render_as_batch=True`) and PostgreSQL.
- Switching to PostgreSQL in a multi-user or distributed phase requires only pointing `DATABASE_ASYNC_URL` and `DATABASE_SYNC_URL` to PostgreSQL in `.env`.
