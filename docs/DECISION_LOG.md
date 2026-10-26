# Architecture Decision Records (ADR) Log

## ADR-001: SQLite as the Initial Primary Database

### Context
The application is a single-user, locally executed NSE paper-trading and research system running on the trader's workstation (Mac/Windows). Initially, PostgreSQL was configured as the default database. However, running a background PostgreSQL server adds friction, local container overhead, external service lifecycle dependencies, and complexity for a local single-user research tool.

### Decision
Adopt **SQLite 3** as the primary default database for the initial release, while preserving full architectural portability to migrate to PostgreSQL in a future multi-user phase.

### Implementation Details
1. **Concurrency Configuration**:
   - Write-Ahead Logging (`PRAGMA journal_mode=WAL`) enabled on connection creation.
   - 10-second busy timeout (`PRAGMA busy_timeout=10000`) configured to eliminate lock contention between FastAPI and the independent trading engine worker.
   - Foreign key integrity strictly enforced via `PRAGMA foreign_keys=ON`.
   - `PRAGMA synchronous=NORMAL` for optimal performance.
2. **Directory Lifecycle**:
   - The `./data` storage directory is created automatically on connection initialization if missing.
3. **Database Driver**:
   - `sqlite+aiosqlite` is used for non-blocking asynchronous operations in FastAPI and the trading worker.
   - Sync `sqlite:///` is used for Alembic migrations.
4. **Portability Preservation**:
   - Models use database-independent SQLAlchemy 2.0 constructs.
   - Alembic migrations use batch mode (`render_as_batch=True`).
   - PostgreSQL drivers and connection parameters remain documented and supported via `.env` configuration.

### Consequences
- **Positive**:
  - Zero-configuration local startup (no need to run Docker or local PostgreSQL daemon).
  - Instant project bootstrapping with a single local file (`./data/nse_paper_trading.db`).
  - High performance with negligible memory footprint.
  - Full support for concurrent reads and safe serial writes between FastAPI and the Trading Worker.
- **Negative / Limitations**:
  - Not suitable for horizontal scaling across multiple distributed servers (which is not a requirement for this local single-user system).
  - PostgreSQL migration path remains available whenever multi-user or cloud deployment is required.
