"""Shared, dependency-free runtime invariants for local application processes."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nse_paper_trading.db"


def canonical_sqlite_url(value: str | None, driver: str) -> str:
    """Return an absolute SQLite URL anchored to the repository, never ``cwd``.

    Only local SQLite files are supported in Phase 1.  Keeping this function in
    ``shared`` makes the backend, worker, and Alembic resolve precisely the
    same file without sharing an engine or session.
    """
    prefix = "sqlite+aiosqlite:///" if driver == "async" else "sqlite:///"
    if not value:
        path = DEFAULT_DB_PATH
    else:
        if not value.startswith(prefix):
            raise ValueError(f"DATABASE_{driver.upper()}_URL must be a local SQLite URL")
        raw_path = value[len(prefix):]
        if not raw_path or raw_path == ":memory:":
            raise ValueError("A persistent SQLite database path is required")
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
    return f"{prefix}{path.resolve()}"


def sqlite_path_from_url(url: str) -> Path:
    """Extract the validated absolute filesystem path from a SQLite URL."""
    marker = ":///"
    if not url.startswith("sqlite") or marker not in url:
        raise ValueError("Expected a SQLite URL")
    return Path(url.split(marker, 1)[1])
