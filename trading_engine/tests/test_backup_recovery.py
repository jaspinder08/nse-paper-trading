"""Disaster Recovery & SQLite Backup Regression Tests (Phase 8 / FR-12, FR-14)."""

import os
from pathlib import Path
import subprocess
import pytest


def test_backup_and_restore_scripts():
    """Verify scripts/backup_db.sh and scripts/restore_db.sh execute cleanly with PRAGMA integrity ok."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    backup_script = root_dir / "scripts" / "backup_db.sh"
    restore_script = root_dir / "scripts" / "restore_db.sh"
    db_file = root_dir / "data" / "nse_paper_trading.db"

    assert backup_script.is_file(), "backup_db.sh must exist"
    assert restore_script.is_file(), "restore_db.sh must exist"
    assert db_file.is_file(), "data/nse_paper_trading.db must exist"

    # 1. Run backup
    backup_result = subprocess.run(
        [str(backup_script)],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )
    assert backup_result.returncode == 0, f"Backup failed: {backup_result.stderr}"
    assert "Backup verified successfully" in backup_result.stdout

    # 2. Run restore
    restore_result = subprocess.run(
        [str(restore_script)],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )
    assert restore_result.returncode == 0, f"Restore failed: {restore_result.stderr}"
    assert "Database restored successfully" in restore_result.stdout
