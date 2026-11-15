# Database (A2)

Schema: [docs/07](../docs/07-data-schema.md) (authoritative). Postgres 16 via compose.

## Migrations

`db/migrations/NNN_description.sql`, forward-only. **Never edit a file that has been applied**
(after CP0): add the next number instead. Owner: Dev-A.

```bash
docker compose up -d migrate          # starts Postgres, applies pending migrations, exits 0
python db/migrate.py --dry-run        # from the host: list pending (DATABASE_URL or PG* env)
python db/migrate.py
```

- `db/migrate.py` applies pending files in numeric order. Each file runs in one transaction with
  its `schema_migrations` row, so a failure rolls back completely and stops (exit 1). Bad file
  names or duplicate numbers exit 2 before anything runs. An advisory lock serialises concurrent
  runs.
- In compose, `migrate` is a one-shot service; services that need the schema (`proxy`, later
  `api`) wait for it with `condition: service_completed_successfully`.
- Postgres no longer runs migrations through `docker-entrypoint-initdb.d`. Databases created that
  way are recognised (their `schema_migrations` row already exists).

## Demo data (X7)

`db/demo-data.sql` is the **frozen real benchmark data** for the demo (Groq `gpt-oss-20b` via Bifrost,
2026-11-15): X3 (first real run), the X6 pilot, and both X6 benchmarks: 4 benchmarks, 33 runs,
421 events, 3 agents, 5 tasks. No fixtures, no secrets (scanned for key patterns, auth headers,
emails and local paths).

```bash
docker compose up -d migrate          # empty database with the schema
python db/demo.py load                # applies migrations, then loads the file in one transaction
```

Loading twice is refused and changes nothing. To re-export after new runs:
`python db/demo.py export --benchmark <id> [--benchmark <id> ...]` (only finished benchmarks;
event ids are renumbered on load, order is kept).

Restore check (2026-11-15): loaded into a fresh database three times; all 118 API responses
(benchmarks, leaderboards, compare grids, resilience, runs, run details, event traces) identical
to the source database.

## Fixtures

`db/fixtures/fixture.sql` is **fabricated test data, never results**. `python db/check_db.py`
truncates the arena tables, loads the fixture, and checks the constraints.

## Tests

`python -m pytest tests/db -q`: runner tests on throwaway databases (needs CREATEDB, which the
compose `arena` user has).
