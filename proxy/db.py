"""Postgres access for the proxy. Sync psycopg used from a thread pool, so it also runs on
Windows' default (Proactor) event loop. One shared connection, reconnected on failure.
The proxy only reads `runs` and only writes `events` (docs/10 section 2.5 rule 4)."""
from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class RunInfo:
    state: str
    scenario: str
    started_at: dt.datetime | None


@dataclass
class Event:
    type: str
    payload: dict
    latency: int | None = None
    error: str | None = None
    agent_role: str | None = None


class Database:
    def __init__(self, dsn: str, connect_timeout: int = 2):
        self.dsn = dsn
        self.connect_timeout = connect_timeout
        self._conn: psycopg.Connection | None = None
        self._lock = threading.Lock()

    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.dsn, autocommit=True, connect_timeout=self.connect_timeout)
        return self._conn

    def _run(self, fn):
        with self._lock:
            try:
                return fn(self._connection())
            except psycopg.OperationalError:
                # Stale/broken connection: drop it and retry once with a fresh one.
                self.close_unlocked()
                return fn(self._connection())

    def get_run(self, run_id: str) -> RunInfo | None:
        def q(c):
            row = c.execute("SELECT state, scenario, started_at FROM runs WHERE run_id = %s",
                            (run_id,)).fetchone()
            return RunInfo(*row) if row else None
        return self._run(q)

    def insert_events(self, run_id: str, events: list[Event]) -> None:
        if not events:
            return

        # One multi-row INSERT: atomic on its own and a single round trip. (A BEGIN/executemany/
        # COMMIT sequence cost ~50 ms per call on Windows due to TCP delayed-ACK stalls.)
        rows = ", ".join(["(%s, %s, %s, %s, %s, %s)"] * len(events))
        params = [v for e in events
                  for v in (run_id, e.type, e.agent_role, Jsonb(e.payload), e.latency, e.error)]
        self._run(lambda c: c.execute(
            "INSERT INTO events (run_id, type, agent_role, payload, latency, error) VALUES " + rows,
            params))

    def close_unlocked(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except psycopg.Error:
                pass  # already broken; we are discarding it
            self._conn = None

    def close(self) -> None:
        with self._lock:
            self.close_unlocked()
