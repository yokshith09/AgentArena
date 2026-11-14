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

## Fixtures

`db/fixtures/fixture.sql` is **fabricated test data, never results**. `python db/check_db.py`
truncates the arena tables, loads the fixture, and checks the constraints.

## Tests

`python -m pytest tests/db -q`: runner tests on throwaway databases (needs CREATEDB, which the
compose `arena` user has).
