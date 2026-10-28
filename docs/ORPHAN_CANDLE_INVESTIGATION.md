# Existing SQLite Orphan Candle Investigation

Investigation date: 2026-10-27

## Safety and scope

Original database confirmed:

```text
/Users/jassi/Desktop/Personal/Intraday/nse-paper-trading/data/nse_paper_trading.db
```

The original was queried only through the immutable read-only URI:

```sql
file:/Users/jassi/Desktop/Personal/Intraday/nse-paper-trading/data/nse_paper_trading.db?mode=ro&immutable=1
```

No migration, insert, update, delete, or PRAGMA configuration change was run
against that database. Remediation and migration experiments used temporary
copies under `/private/tmp`, which were removed afterward.

## Exact affected record — FAIL

`PRAGMA integrity_check` returned `ok`, but `PRAGMA foreign_key_check` returned
one violation:

```text
market_candles|1|instruments|0
```

The complete orphan record is:

| Field | Value |
| --- | --- |
| Candle primary key | `1` |
| Referenced instrument ID | `999999` |
| Symbol / name | unavailable; no instrument exists |
| Timeframe | `5m` |
| Timestamp | `2026-10-26 17:15:41.525393` |
| Open / high / low / close | `100.0 / 105.0 / 99.0 / 103.0` |
| Volume / open interest | `1000 / NULL` |
| Created / updated | `2026-10-26 17:15:41.528748` / `2026-10-26 17:15:41.528754` |

There are no other foreign-key violations. Four valid instruments and four
valid candles remain; all valid candles are 15-minute TCS test records.

## Queries used

```sql
SELECT version_num FROM alembic_version;
PRAGMA integrity_check;
PRAGMA foreign_key_check;

SELECT c.id, c.instrument_id, i.symbol, i.name, c.timeframe,
       c.candle_timestamp, c.open, c.high, c.low, c.close,
       c.volume, c.open_interest, c.created_at, c.updated_at
FROM market_candles AS c
LEFT JOIN instruments AS i ON i.id = c.instrument_id
WHERE i.id IS NULL
ORDER BY c.id;

SELECT id, symbol, name, exchange, token, segment, is_tradable
FROM instruments ORDER BY id;
SELECT * FROM pragma_foreign_key_list('market_candles');
```

## Root-cause investigation — PASS

The orphan exactly matches the negative foreign-key test fixture in
`backend/tests/test_sqlite_features.py`:

```python
instrument_id = 999999
timeframe = "5m"
open, high, low, close = 100.0, 105.0, 99.0, 103.0
volume = 1000
```

The model and initial migration both define
`market_candles.instrument_id -> instruments.id ON DELETE CASCADE`. The likely
cause is that this test was run historically against the development database
using a SQLite connection on which `PRAGMA foreign_keys` was disabled. The test
then inserted its intentionally invalid fixture instead of raising the expected
integrity error. No evidence supports restoring an instrument: ID `999999` has
no identity, symbol, token, or market-data provenance.

## Disposable remediation test — PARTIAL

On a temporary copy only, the exact record was deleted with a predicate that
matched all identifying values:

```sql
DELETE FROM market_candles
WHERE id = 1 AND instrument_id = 999999 AND timeframe = '5m'
  AND candle_timestamp = '2026-10-26 17:15:41.525393'
  AND open = 100.0 AND high = 105.0 AND low = 99.0 AND close = 103.0
  AND volume = 1000;
```

Results before migration on that copy:

- one row deleted;
- `PRAGMA integrity_check` returned `ok`;
- `PRAGMA foreign_key_check` returned no violations;
- four instruments and four valid candles were preserved.

## Pending migration safety — FAIL

The orphan-remediated temporary copy was then upgraded from
`7d826b4ac3b6` to `financial_safety_0001`. Alembic reported the head revision
and integrity/foreign-key checks passed, but the copy contained **zero market
candles afterward**.

This is a separate destructive migration defect. The migration batch-recreates
the parent `instruments` table before `market_candles`. SQLite executes the
existing `ON DELETE CASCADE` relationship while the parent is recreated, which
cascades deletion of the valid child candle rows. The relevant operation order
is in `2026_10_27_0001_financial_safety_constraints.py`:

```python
_numeric("instruments", {"tick_size": 4})
_numeric("market_candles", {"open": 4, "high": 4, "low": 4, "close": 4})
```

Therefore the pending migration is not safe for a populated database even
after orphan remediation. No original financial values were changed or
converted. Financial data preservation is not demonstrated by this test.

## Proposed remediation and data-loss implications

1. **Orphan record:** deletion is the evidence-supported remedy, but only with
   explicit user approval. It removes one proven invalid test fixture and no
   identifiable market data. Restoring an instrument would fabricate an
   identity and is not recommended.
2. **Migration:** do not run it on any populated database. First replace or
   revise the migration strategy to preserve child rows during SQLite table
   recreation, then prove row-for-row preservation and foreign-key validity on
   a fresh copy.
3. **Data loss:** deleting candle ID `1` is limited and intentional once
   approved. Running the current migration risks deletion of valid candles and
   must not be approved.

## Migration readiness

Current original revision: `7d826b4ac3b6`.

**Not ready.** The orphan can be safely remediated in principle, but the
pending migration must be corrected and independently re-verified first.

## Recommendation

**REQUIRES USER APPROVAL** — approve the narrowly scoped deletion of the
proven test fixture only after the migration itself has been fixed and tested
for child-record preservation. No data-remediation operation was applied to
the original database.
