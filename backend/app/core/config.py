from typing import List, Literal, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.runtime_config import canonical_sqlite_url, sqlite_path_from_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
    )

    # General
    PROJECT_NAME: str = "NSE Paper-Trading System"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/v1"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database Configuration (Default: SQLite for local single-user paper trading)
    # PostgreSQL is reserved for future migration
    DATABASE_ASYNC_URL: str = Field(
        default=None,
        description="Async database connection URL"
    )
    DATABASE_SYNC_URL: str = Field(
        default=None,
        description="Sync database connection URL for Alembic migrations"
    )

    # Trading Engine Constants (STRICT PAPER TRADING ONLY)
    TRADING_MODE: Literal["PAPER"]
    PAPER_INITIAL_CAPITAL: float = 100000.0
    MAX_CAPITAL_PER_DAY: float = 50000.0
    MAX_LOSS_PER_DAY: float = 2000.0
    MAX_OPEN_POSITIONS: int = 3
    ENGINE_SCAN_INTERVAL_SECONDS: float = 1.0

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        raise ValueError("ALLOWED_ORIGINS must be a comma-separated list or JSON list")

    @field_validator("DATABASE_ASYNC_URL", mode="before")
    @classmethod
    def canonical_async_url(cls, value: str | None) -> str:
        return canonical_sqlite_url(value, "async")

    @field_validator("DATABASE_SYNC_URL", mode="before")
    @classmethod
    def canonical_sync_url(cls, value: str | None) -> str:
        return canonical_sqlite_url(value, "sync")

    @model_validator(mode="after")
    def validate_database_pair(self) -> "Settings":
        async_path = sqlite_path_from_url(self.DATABASE_ASYNC_URL)
        sync_path = sqlite_path_from_url(self.DATABASE_SYNC_URL)
        if async_path != sync_path:
            raise ValueError("DATABASE_ASYNC_URL and DATABASE_SYNC_URL must target the same file")
        return self

    @property
    def is_paper_trading_only(self) -> bool:
        """True only when validated configuration is in the sole supported mode."""
        return self.TRADING_MODE == "PAPER"


settings = Settings()
