# NSE Paper-Trading & Intraday Research System

A local, decoupled **NSE Paper-Trading & Intraday Research System** built for algorithmic intraday trading research and real-time simulation.

⚠️ **CRITICAL TRADING SAFETY NOTICE**:
> This system is strictly designed for simulated **Paper Trading**. Real broker order execution is permanently disabled and rejected across all layers.

---

## 1. Architectural Overview

The system is composed of three independent, decoupled processes:

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

- **Independent Worker**: Closing the Flutter frontend or stopping the FastAPI server does **not** terminate the Trading Engine worker.
- **SQLite with WAL Mode (ADR-001)**: The primary database is local SQLite (`./data/nse_paper_trading.db`) running with Write-Ahead Logging (`PRAGMA journal_mode=WAL`), foreign key enforcement (`PRAGMA foreign_keys=ON`), and a 10-second busy timeout (`PRAGMA busy_timeout=10000`).
- **PostgreSQL Ready**: Full schema portability is maintained. Migrating to PostgreSQL requires only updating `DATABASE_ASYNC_URL` and `DATABASE_SYNC_URL` in `.env`.

---

## 2. Directory Structure

```text
nse-paper-trading/
├── backend/
│   ├── alembic/              # Database migration environment
│   ├── app/
│   │   ├── api/v1/           # Modular REST and WebSocket routers (/v1/health, /v1/ws)
│   │   ├── core/             # Configuration, logging, centralized exceptions
│   │   ├── database/         # SQLAlchemy 2.0 async session and DeclarativeBase
│   │   ├── models/           # 13 ORM entities (Session, Candle, Order, Position, Logs...)
│   │   ├── repositories/     # Generic async database repository pattern
│   │   ├── schemas/          # Pydantic v2 validation models
│   │   ├── services/         # Business logic layer (HealthService, etc.)
│   │   └── websocket/        # Real-time WebSocket ConnectionManager
│   ├── tests/                # Pytest async test suite
│   ├── alembic.ini           # Alembic configuration
│   └── requirements.txt      # Backend Python dependencies
│
├── trading_engine/
│   ├── config/               # Worker configuration and safety invariants
│   ├── market_data/          # Market data abstraction & Mock provider
│   ├── scanner/              # Universe scanning & ORB candidate detection
│   ├── strategy/             # Strategy interface & ORB strategy placeholder
│   ├── risk/                 # Risk validator & position sizing logic
│   ├── execution/            # Simulated paper order execution engine
│   ├── portfolio/            # Portfolio margin & position manager
│   ├── backtesting/          # Historical backtesting simulation engine
│   ├── storage/              # Worker async database persistence
│   ├── tests/                # Unit tests for risk rules & paper executor
│   ├── worker.py             # Independent daemon entry point
│   └── requirements.txt      # Trading engine dependencies
│
├── frontend/                 # Flutter application (Android, Windows, macOS)
│   └── lib/
│       ├── core/             # Theme (Dark/Light), constants, network config
│       ├── features/         # Modular feature screens (Dashboard, Scanner, Trades, etc.)
│       └── shared/           # Reusable widgets (PaperTradingBanner)
│
├── data/                     # Local SQLite database directory (auto-created)
├── docs/                     # Specifications, Architecture, Schema, ADR Decision Log
├── scripts/                  # Shell scripts for setup, backend, worker, frontend
├── shared/                   # Shared domain enums and contracts
├── .env.example              # Sample environment configuration
├── docker-compose.yml        # Optional PostgreSQL docker setup
└── README.md
```

---

## 3. Getting Started

### Prerequisites
- Python 3.12+
- Flutter 3.32+
- (Optional) Docker Compose if running PostgreSQL in the future

### Step 1: Environment Setup
```bash
cd nse-paper-trading

# Create Python virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Configure environment file
cp .env.example .env
```

### Step 2: Database Setup & Migrations
Initialize the SQLite database (`data/nse_paper_trading.db`) and apply all 13 model tables:
```bash
./scripts/setup_db.sh
# or directly:
alembic -c backend/alembic.ini upgrade head
```

---

## 4. Running the Components

Each component runs independently in its own terminal window:

### A. Run FastAPI Backend
```bash
./scripts/run_backend.sh
# Server starts at http://127.0.0.1:8000
# Interactive Swagger Documentation: http://127.0.0.1:8000/docs
# Health Check Endpoint: http://127.0.0.1:8000/v1/health
```

### B. Run Independent Trading Engine Worker
```bash
./scripts/run_worker.sh
# Worker starts its own cycle, evaluating strategy rules and risk checks independently
```

### C. Run Flutter Frontend
```bash
./scripts/run_frontend.sh
# Or specify target platform:
cd frontend
flutter run -d macos    # macOS Desktop
flutter run -d windows  # Windows Desktop
flutter run             # Android device / emulator
```

---

## 5. Running Tests

Run the complete backend and trading engine test suite:
```bash
.venv/bin/pytest backend/tests trading_engine/tests -v
```

All 13 foundation tests verify:
- Database connectivity & async queries
- Model CRUD operations
- SQLite foreign key constraints enforcement (`PRAGMA foreign_keys=ON`)
- Unique candlestick constraint (`instrument_id + timeframe + candle_timestamp`)
- Concurrent database reads in WAL mode
- Concurrent backend API and trading worker read/write access
- Risk validator limits and daily drawdown stop
- Paper execution safety guard against live orders
- FastAPI `/v1/health` endpoint response
