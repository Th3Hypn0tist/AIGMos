from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class SQLiteAdapter:
    def __init__(self, path: str | Path) -> None:
        resolved = Path(path).expanduser().resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(resolved)
        self._lock = threading.RLock()
        self._bootstrap()

    @contextmanager
    def _connect(self):
        # SQLite is only a persistence sink here, not a live shared buffer.
        # Use short-lived connections and a conservative journal mode so this
        # stays robust on WSL drvfs paths like /mnt/d/..., where WAL can be
        # fragile under rapid open/close patterns.
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5.0, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
        finally:
            conn.close()

    def _bootstrap(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS kv (
                        symbol TEXT PRIMARY KEY,
                        value  TEXT NOT NULL
                    )
                    """
                )
                conn.commit()

    def get(self, symbol: str) -> Any:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT value FROM kv WHERE symbol = ?",
                    (symbol,),
                ).fetchone()

        if row is None:
            return None

        return json.loads(row[0])

    def set(self, symbol: str, value: Any) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO kv(symbol, value)
                    VALUES(?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET value = excluded.value
                    """,
                    (symbol, json.dumps(value, ensure_ascii=False)),
                )
                conn.commit()

    def delete(self, symbol: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM kv WHERE symbol = ?", (symbol,))
                conn.commit()

    def list_symbols(self) -> list[str]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT symbol FROM kv ORDER BY symbol"
                ).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        return None
