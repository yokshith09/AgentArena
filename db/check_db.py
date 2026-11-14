"""Stage 1 check: load fixtures into the compose Postgres, read back, verify constraints.
Needs `docker compose up -d migrate` (starts Postgres and applies db/migrations) and `pip install -r requirements.txt`. TRUNCATES the arena tables first."""
import os

import psycopg

dsn = os.environ.get("DATABASE_URL", "postgresql://arena:arena@localhost:5432/arena")
RUN = "22222222-2222-4222-8222-222222222222"
with psycopg.connect(dsn, autocommit=True) as c:
    c.execute("TRUNCATE events, runs, benchmarks, tasks, agents CASCADE")
    with open(os.path.join(os.path.dirname(__file__), "fixtures", "fixture.sql"), encoding="utf8") as fixture:
        c.execute(fixture.read())
    n = c.execute("SELECT count(*) FROM events WHERE run_id=%s", (RUN,)).fetchone()[0]
    assert n == 4, n
    assert c.execute("SELECT 1 FROM runs WHERE status='INFRA_ERROR' AND state='done'").fetchone()
    for bad in (
        "INSERT INTO runs(agent_id,task_id,state,status) VALUES ('agent-a-plain','fix-off-by-one','queued','PASS')",
        f"INSERT INTO events(run_id,type) VALUES ('{RUN}','bogus')",
    ):
        try:
            c.execute(bad)
            raise SystemExit("constraint missing: " + bad)
        except psycopg.errors.CheckViolation:
            pass
    print("db OK")
