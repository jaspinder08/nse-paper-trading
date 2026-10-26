from typing import Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.runtime_config import canonical_sqlite_url, sqlite_path_from_url


class TradingEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
    )

    # STRICT SAFETY INVARIANT: Trading mode must ALWAYS be PAPER
    TRADING_MODE: Literal["PAPER"] = Field(description="The only supported execution mode")
    PAPER_INITIAL_CAPITAL: float = 100000.0
    MAX_CAPITAL_PER_DAY: float = 50000.0
    MAX_LOSS_PER_DAY: float = 2000.0
    MAX_OPEN_POSITIONS: int = 3
    ENGINE_SCAN_INTERVAL_SECONDS: float = 1.0

    # Market Data
    MARKET_DATA_PROVIDER: str = "mock"

    # Database URLs (Default: SQLite, PostgreSQL reserved for future)
    DATABASE_ASYNC_URL: str | None = None
    DATABASE_SYNC_URL: str | None = None

    @field_validator("DATABASE_ASYNC_URL", mode="before")
    @classmethod
    def canonical_async_url(cls, value: str | None) -> str:
        return canonical_sqlite_url(value, "async")

    @field_validator("DATABASE_SYNC_URL", mode="before")
    @classmethod
    def canonical_sync_url(cls, value: str | None) -> str:
        return canonical_sqlite_url(value, "sync")

    @model_validator(mode="after")
    def validate_database_pair(self) -> "TradingEngineSettings":
        if sqlite_path_from_url(self.DATABASE_ASYNC_URL) != sqlite_path_from_url(self.DATABASE_SYNC_URL):
            raise ValueError("DATABASE_ASYNC_URL and DATABASE_SYNC_URL must target the same file")
        return self

    @property
    def is_paper_mode(self) -> bool:
        return self.TRADING_MODE == "PAPER"


engine_settings = TradingEngineSettings()
