from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import event, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.models.ingestion import DataIngestionJob
from backend.app.models.logs import SystemLog
from trading_engine.config.settings import engine_settings
from shared.runtime_config import sqlite_path_from_url


class EngineStorageRepository:
    """Async repository for trading worker persistence using SQLite (or PostgreSQL)."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self.db_url = db_url or engine_settings.DATABASE_ASYNC_URL
        self._ensure_dir()

        connect_args = {}
        if "sqlite" in self.db_url.lower():
            connect_args["check_same_thread"] = False

        self.engine = create_async_engine(
            self.db_url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )

        if "sqlite" in self.db_url.lower():
            @event.listens_for(self.engine.sync_engine, "connect")
            def set_pragmas(dbapi_connection, _):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=10000")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    def _ensure_dir(self) -> None:
        sqlite_path_from_url(self.db_url).parent.mkdir(parents=True, exist_ok=True)

    async def log_system_event(self, level: str, module: str, message: str, details: Optional[str] = None) -> None:
        """Write a system diagnostic event using a short transaction."""
        async with self.session_factory() as session:
            async with session.begin():
                log_entry = SystemLog(
                    level=level,
                    module=module,
                    message=message,
                    details=details,
                    logged_at=datetime.now(timezone.utc),
                )
                session.add(log_entry)

    async def recover_interrupted_jobs(self) -> int:
        """Recover any jobs left in 'RUNNING' status from previous worker crashes or restarts."""
        async with self.session_factory() as session:
            async with session.begin():
                stmt = (
                    update(DataIngestionJob)
                    .where(DataIngestionJob.status == "RUNNING")
                    .values(
                        status="PENDING",
                        error_message="Recovered from worker restart",
                    )
                )
                res = await session.execute(stmt)
                return res.rowcount or 0

    async def get_next_pending_job_id(self) -> Optional[int]:
        """Fetch the ID of the next pending ingestion job, if any."""
        async with self.session_factory() as session:
            stmt = (
                select(DataIngestionJob.id)
                .where(DataIngestionJob.status == "PENDING")
                .order_by(DataIngestionJob.id.asc())
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

    async def dispose(self) -> None:
        await self.engine.dispose()
