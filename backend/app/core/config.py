import os
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
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
    ALLOWED_ORIGINS: Union[List[str], str] = ["*"]

    # Database Configuration (Default: SQLite for local single-user paper trading)
    # PostgreSQL is reserved for future migration
    DATABASE_ASYNC_URL: str = Field(
        default="sqlite+aiosqlite:///./data/nse_paper_trading.db",
        description="Async database connection URL"
    )
    DATABASE_SYNC_URL: str = Field(
        default="sqlite:///./data/nse_paper_trading.db",
        description="Sync database connection URL for Alembic migrations"
    )

    # Optional PostgreSQL connection parameters (reserved for future migration)
    POSTGRES_SERVER: Optional[str] = "localhost"
    POSTGRES_PORT: Optional[int] = 5432
    POSTGRES_USER: Optional[str] = "postgres"
    POSTGRES_PASSWORD: Optional[str] = ""
    POSTGRES_DB: Optional[str] = "nse_paper_trading"

    # Trading Engine Constants (STRICT PAPER TRADING ONLY)
    TRADING_MODE: str = "PAPER"
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
        return ["*"]

    @property
    def is_paper_trading_only(self) -> bool:
        """Safety invariant: Paper trading must always be True."""
        return True


settings = Settings()
