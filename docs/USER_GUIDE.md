# NSE Paper-Trading & Intraday Research System
## Comprehensive User & Operations Guide (v1.0)

---

## 1. System Overview & Architecture

The **NSE Paper-Trading & Intraday Research System** is an intraday equities research and paper-trading platform built strictly for Indian National Stock Exchange (NSE) cash-market equities (Nifty 50 constituents). 

### 🛡️ Non-Negotiable Safety Mandate
- **Strictly Paper Trading Only**: This application operates exclusively in simulated paper-trading mode.
- **Zero Broker Execution**: No live broker order-placement, modification, or cancellation endpoints exist in the codebase.
- **Local-First & Cost-Free**: Operates entirely on the local computer without requiring paid cloud AI APIs or monthly SaaS subscriptions.

### Architecture Components
```
                      ┌────────────────────────────────────────┐
                      │          Flutter Frontend UI           │
                      │  (Dashboard, Scanner, Risk, Backtest)  │
                      └──────────────────┬─────────────────────┘
                                         │ REST (Port 8000) & WebSocket (/v1/ws)
                                         ▼
                      ┌────────────────────────────────────────┐
                      │          FastAPI Backend Server        │
                      │  (OpenAPI Swagger, REST Routers, WS)   │
                      └──────────────────┬─────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌─────────────────┐            ┌───────────────────┐            ┌───────────────────┐
│ Trading Engine  │            │  Local SQLite DB  │            │ Historical        │
│ Worker Loop     │◄──────────►│ (WAL Mode, Local) │◄──────────►│ Backtesting Engine│
│ (ORB + Sizing)  │            │ data/nse_paper.db │            │ (Zero Look-Ahead) │
└─────────────────┘            └───────────────────┘            └───────────────────┘
```

---

## 2. Prerequisites & Setup

### Prerequisites
- **Python**: 3.11+ or 3.12+
- **Flutter SDK**: 3.24+ (Dart 3.5+)
- **Operating System**: macOS, Linux, or Windows (via WSL or PowerShell)
- **SQLite3**: Pre-installed on macOS/Linux.

### Installation
Clone or navigate to the repository directory:
```bash
cd nse-paper-trading
```

Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r trading_engine/requirements.txt
```

Initialize local SQLite database:
```bash
./scripts/setup_db.sh
```

---

## 3. Starting the System

### Single-Command Unified Launcher (Recommended)
You can launch the **FastAPI Backend**, the **Trading Engine Worker**, and the **Flutter Frontend** simultaneously with one command:
```bash
./scripts/run_all.sh
```
- Automatically checks database readiness.
- Traps `SIGINT` / `SIGTERM` so pressing `Ctrl+C` cleanly shuts down all background processes without orphan processes.

### Starting Services Individually
- **Backend API**:
  ```bash
  ./scripts/run_backend.sh
  # Running at http://127.0.0.1:8000 (Swagger docs: http://127.0.0.1:8000/docs)
  ```
- **Trading Engine Worker**:
  ```bash
  ./scripts/run_worker.sh
  ```
- **Flutter Frontend UI**:
  ```bash
  ./scripts/run_frontend.sh
  ```

---

## 4. Configuration Settings (`.env`)

Configuration parameters can be tuned in `.env` (or via environment variables):

| Parameter | Default Value | Description |
| :--- | :--- | :--- |
| `TRADING_MODE` | `PAPER` | **Locked to `PAPER`**. Live execution is permanently rejected. |
| `PAPER_INITIAL_CAPITAL` | `5000.0` | Initial virtual trading capital in INR (₹). |
| `CASH_RESERVE_PCT` | `0.10` | 10% capital buffer reserved and never allocated. |
| `MAX_POSITION_PCT` | `0.25` | Maximum 25% of virtual capital permitted in a single stock. |
| `MAX_RISK_PER_TRADE_INR`| `25.0` | Maximum planned loss at stop-loss per trade. |
| `MAX_DAILY_LOSS_INR` | `75.0` | **Daily Loss Circuit Breaker**: Blocks all entries if realized loss hits ₹75. |
| `MAX_TRADES_PER_DAY` | `3` | Maximum number of new trades allowed per session. |
| `MAX_EVENTS_PER_DAY` | `6` | Maximum simulated order events allowed per session. |
| `MIN_REWARD_RISK` | `1.5` | Minimum 1.5:1 reward-to-risk ratio required for entry. |
| `MARKET_DATA_PROVIDER` | `mock` | `mock` (deterministic local data) or `angel_one`. |

---

## 5. Trading Strategy Rules (5-Minute ORB)

The system evaluates a strictly defined Opening Range Breakout (ORB) candidate strategy:
1. **Timeframe**: 5-minute OHLCV completed candles.
2. **Opening Range (09:15–09:30 IST)**: High and Low established across the first three 5-minute bars.
3. **Long Breakout Trigger**: A completed candle closes above the opening range high (`close > orb_high`).
4. **Volume Confirmation**: Candle volume must exceed `1.2x` the opening range average volume.
5. **Entry Window Cutoff**: No new entries are permitted after 14:30 IST.
6. **Stop-Loss**: Fixed at the opening range low (`orb_low`).
7. **Target**: Calculated as `entry + 1.5 * (entry - stop)`.
8. **Intraday Exits**:
   - Target reached: Exits at target price with 1-tick adverse slippage.
   - Stop-Loss reached: Exits at stop-loss with 1-tick adverse slippage.
   - Same-bar conflict: Stop-loss takes priority over target.
   - End-of-Day (EOD) Square-off: Automatic square-off at 15:15 IST.
9. **Transaction Costs**: Accurately modeled via [shared/costs.py](file:///Users/jassi/Desktop/Personal/Intraday/nse-paper-trading/shared/costs.py) (STT, exchange charges, SEBI fees, GST, stamp duty, and slippage).

---

## 6. Frontend Features & Usage

### 📊 Dashboard Screen
- **Market Status Banner**: Displays market session status (`ACTIVE`, `SCHEDULED`, `CLOSED`) and Asia/Kolkata exchange hours.
- **Backend Health Indicator**: Real-time heartbeat monitoring.
- **Capital & Portfolio Summary**: Live Net Equity, Realized P&L, Unrealized P&L, Available Margin, and Cash Reserve.
- **Risk Progress Meter**: Visual bar showing percentage utilization of the ₹75 Daily Circuit Breaker.

### 🔍 Candidate Scanner Screen
- Live table of all Nifty 50 constituents.
- Shows status: `TRIGGERED`, `PENDING_BREAKOUT`, `RANGE_FORMING`, `REJECTED_VOLUME`, `REJECTED_CUTOFF`.
- Filter chips to view triggered breakouts or pending stocks.

### 🛡️ Risk Management Screen
- Real-time quotas: Trades taken (`X / 3`), Order events (`X / 6`), Open positions (`X / 3`).
- Explanatory audit scorecard for all 9 Gatekeeper checks.

### 💼 Portfolio & Orders Screen
- **Active Positions**: Displays symbol, side, quantity, average entry price, LTP, stop-loss, target, and mark-to-market unrealized P&L.
- **Paper Orders**: Complete log of simulated orders and fill statuses.

### 📜 Trade Journal Screen
- Detailed ledger of executed fills, exit reasons, net P&L, and statutory fees.
- CSV export integration.

### 🧪 Backtesting Screen (`FR-10`)
- **Configurable Form**: Select strategy (`ORB_STRATEGY`), symbols, date range, and starting capital.
- **Interactive Results Scorecard**: Win Rate %, Net P&L, Profit Factor, Expectancy, Max Drawdown %, Gross Profit/Loss, and Charges.
- **Simulated Trade Table**: Bar-by-bar chronological execution log without look-ahead bias.

---

## 7. Multi-Session Paper Observation Suite (`Phase 7`)

To review simulation evidence and audit data across 20–30 trading sessions:
```bash
.venv/bin/python3 scripts/simulate_session.py --sessions 25 --capital 5000.0
```
- Replays consecutive trading sessions chronologically.
- Validates circuit breakers, trade limits, and statutory fees.
- Reconciles cash and P&L with 100% mathematical auditability (zero drift).

---

## 8. Backup & Disaster Recovery

### Online SQLite Backup
To back up the live database without stopping active services:
```bash
./scripts/backup_db.sh
```
- Creates an online atomic snapshot in `data/backups/`.
- Executes `PRAGMA integrity_check` on the backup to guarantee zero corruption.

### Database Restore
To restore from the latest backup:
```bash
./scripts/restore_db.sh
```
Or specify a specific backup file:
```bash
./scripts/restore_db.sh data/backups/nse_paper_trading_YYYYMMDD_HHMMSS.db
```

### Universe Master Update
To validate point-in-time constituent date intervals and refresh instruments:
```bash
.venv/bin/python3 scripts/update_universe.py
```

---

## 9. Data Export Endpoints (`FR-14`)

All data can be downloaded directly from the REST API or Swagger UI (`http://127.0.0.1:8000/docs`):
- **Trading Signals CSV**: `GET /v1/export/signals`
- **Trade Journal CSV**: `GET /v1/export/trades`
- **Positions CSV**: `GET /v1/export/positions`
- **Backtest Run CSV**: `GET /v1/export/backtest/{run_id}`

---

## 10. Research Limitations & Disclaimers

1. **Paper Trading Disclaimer**: Simulated performance does not guarantee future results. Market depth, partial fills, queue priority, and extreme volatility are modeled conservatively but may differ from real-world execution.
2. **Survivorship Bias**: Historical backtests use dated constituent data where available; older historical periods may reflect survivorship bias.
3. **Strict No-Trading Policy**: This system is designed solely for quantitative intraday research, risk analysis, and educational evaluation. Real trading order interfaces are intentionally excluded from the architecture.
