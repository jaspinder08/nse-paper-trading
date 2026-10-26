from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingEngineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # STRICT SAFETY INVARIANT: Trading mode must ALWAYS be PAPER
    TRADING_MODE: str = Field(default="PAPER", description="STRICT: PAPER only")
    PAPER_INITIAL_CAPITAL: float = 100000.0
    MAX_CAPITAL_PER_DAY: float = 50000.0
    MAX_LOSS_PER_DAY: float = 2000.0
    MAX_OPEN_POSITIONS: int = 3
    ENGINE_SCAN_INTERVAL_SECONDS: float = 1.0

    # Market Data
    MARKET_DATA_PROVIDER: str = "mock"

    # Database URLs (Default: SQLite, PostgreSQL reserved for future)
    DATABASE_ASYNC_URL: str = "sqlite+aiosqlite:///./data/nse_paper_trading.db"
    DATABASE_SYNC_URL: str = "sqlite:///./data/nse_paper_trading.db"

    @property
    def is_paper_mode(self) -> bool:
        return self.TRADING_MODE.upper() == "PAPER"


engine_settings = TradingEngineSettings()
