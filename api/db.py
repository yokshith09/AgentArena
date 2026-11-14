"""Small thread-safe psycopg connection pool for the API (sync endpoints run in a thread pool).
Sessions use UTC so timestamps serialise as ISO-8601 UTC (docs/08 section 1.1)."""
from __future__ import annotations

import queue
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


class Pool:
    def __init__(self, dsn: str, size: int = 8, connect_timeout: int = 3):
        self.dsn, self.connect_timeout = dsn, connect_timeout
        self._idle: queue.LifoQueue[psycopg.Connection] = queue.LifoQueue(maxsize=size)

    def _new(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, autocommit=True, row_factory=dict_row,
                               connect_timeout=self.connect_timeout, options="-c timezone=UTC")

    @contextmanager
    def conn(self):
        try:
            c = self._idle.get_nowait()
        except queue.Empty:
            c = self._new()
        ok = False
        try:
            yield c
            ok = True
        finally:
            if ok and not c.closed and not c.broken:
                try:
                    self._idle.put_nowait(c)
                    c = None
                except queue.Full:
                    pass
            if c is not None:
                c.close()

    def close(self) -> None:
        while True:
            try:
                self._idle.get_nowait().close()
            except queue.Empty:
                return
