#!/usr/bin/env bash
set -e

# Resolve repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

DB_FILE="data/nse_paper_trading.db"
BACKUP_DIR="data/backups"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/nse_paper_trading_${TIMESTAMP}.db"

if [ ! -f "${DB_FILE}" ]; then
    echo "Error: Database file ${DB_FILE} does not exist."
    exit 1
fi

mkdir -p "${BACKUP_DIR}"

echo "=================================================="
echo "  NSE Paper-Trading SQLite Database Backup"
echo "=================================================="
echo "Source: ${DB_FILE}"
echo "Target: ${BACKUP_FILE}"

# Use SQLite online backup API to prevent WAL locking corruption
sqlite3 "${DB_FILE}" ".backup '${BACKUP_FILE}'"

# Verify backup integrity
INTEGRITY="$(sqlite3 "${BACKUP_FILE}" "PRAGMA integrity_check;")"
if [ "${INTEGRITY}" == "ok" ]; then
    SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
    echo "  Backup verified successfully (Integrity: ${INTEGRITY}, Size: ${SIZE})"
    echo "=================================================="
else
    echo "  Error: Backup integrity check failed: ${INTEGRITY}"
    exit 1
fi
