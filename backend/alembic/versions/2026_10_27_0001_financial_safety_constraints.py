"""Use exact financial numerics and enforce Phase 1 paper safety invariants.

Revision ID: financial_safety_0001
Revises: 7d826b4ac3b6
"""

from alembic import op
import sqlalchemy as sa

revision = "financial_safety_0001"
down_revision = "7d826b4ac3b6"
branch_labels = None
depends_on = None


def _numeric(table: str, columns: dict[str, int]) -> None:
    with op.batch_alter_table(table, recreate="always") as batch:
        for column, scale in columns.items():
            batch.alter_column(column, existing_type=sa.Float(), type_=sa.Numeric(18, scale))


def upgrade() -> None:
    _numeric("instruments", {"tick_size": 4})
    with op.batch_alter_table("instruments", recreate="always") as batch:
        batch.create_check_constraint("ck_instrument_lot_size_positive", "lot_size > 0")
        batch.create_check_constraint("ck_instrument_tick_size_positive", "tick_size > 0")

    _numeric("market_candles", {"open": 4, "high": 4, "low": 4, "close": 4})
    with op.batch_alter_table("market_candles", recreate="always") as batch:
        batch.create_check_constraint("ck_candle_ohlc_valid", "open > 0 AND high >= low AND high >= open AND high >= close AND low <= open AND low <= close")
        batch.create_check_constraint("ck_candle_volume_nonnegative", "volume >= 0")

    _numeric("trading_signals", {"trigger_price": 4, "stop_loss": 4, "target_price": 4})
    with op.batch_alter_table("trading_signals", recreate="always") as batch:
        batch.create_check_constraint("ck_signal_prices_positive", "trigger_price > 0 AND stop_loss > 0 AND target_price > 0")

    _numeric("paper_orders", {"requested_price": 4, "executed_price": 4})
    with op.batch_alter_table("paper_orders", recreate="always") as batch:
        batch.create_check_constraint("ck_paper_order_simulated", "is_paper = 1")
        batch.create_check_constraint("ck_paper_order_quantity_positive", "quantity > 0")
        batch.create_check_constraint("ck_paper_order_price_positive", "requested_price > 0")

    _numeric("positions", {"average_entry_price": 4, "current_price": 4, "stop_loss": 4, "target": 4, "realized_pnl": 2, "unrealized_pnl": 2})
    with op.batch_alter_table("positions", recreate="always") as batch:
        batch.create_check_constraint("ck_position_quantity_positive", "quantity > 0")
        batch.create_check_constraint("ck_position_simulated", "is_paper = 1")

    _numeric("trading_sessions", {"initial_capital": 2, "realized_pnl": 2, "unrealized_pnl": 2})
    _numeric("portfolio_snapshots", {"total_capital": 2, "available_margin": 2, "utilized_margin": 2, "realized_pnl": 2, "unrealized_pnl": 2})
    _numeric("trade_logs", {"price": 4, "pnl": 2})


def downgrade() -> None:
    # SQLite batch downgrades retain data but intentionally remove only these new invariants.
    for table, names in (("positions", ["ck_position_quantity_positive", "ck_position_simulated"]), ("paper_orders", ["ck_paper_order_simulated", "ck_paper_order_quantity_positive", "ck_paper_order_price_positive"]), ("trading_signals", ["ck_signal_prices_positive"]), ("market_candles", ["ck_candle_ohlc_valid", "ck_candle_volume_nonnegative"]), ("instruments", ["ck_instrument_lot_size_positive", "ck_instrument_tick_size_positive"])):
        with op.batch_alter_table(table, recreate="always") as batch:
            for name in names:
                batch.drop_constraint(name, type_="check")
