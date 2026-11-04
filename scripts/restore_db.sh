#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

DB_FILE="data/nse_paper_trading.db"
BACKUP_DIR="data/backups"

if [ -n "$1" ]; then
    RESTORE_FILE="$1"
else
    # Find newest backup
    RESTORE_FILE="$(ls -t ${BACKUP_DIR}/nse_paper_trading_*.db 2>/dev/null | head -n 1)"
fi

if [ -z "${RESTORE_FILE}" ] || [ ! -f "${RESTORE_FILE}" ]; then
    echo "Error: No valid backup file found to restore."
    echo "Usage: ./scripts/restore_db.sh [path/to/backup.db]"
    exit 1
fi

echo "=================================================="
echo "  NSE Paper-Trading SQLite Database Restore"
echo "=================================================="
echo "Source: ${RESTORE_FILE}"
echo "Target: ${DB_FILE}"

# Check integrity of backup before restoring
INTEGRITY="$(sqlite3 "${RESTORE_FILE}" "PRAGMA integrity_check;")"
if [ "${INTEGRITY}" != "ok" ]; then
    echo "Error: Backup file failed integrity check: ${INTEGRITY}"
    exit 1
fi

# Remove existing WAL/SHM files
rm -f "${DB_FILE}-wal" "${DB_FILE}-shm"

# Restore database
sqlite3 "${RESTORE_FILE}" ".backup '${DB_FILE}'"

echo "  Database restored successfully."
echo "=================================================="
