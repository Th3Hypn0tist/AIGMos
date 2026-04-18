from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class SQLiteAdapter:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = threading.RLock()

        with self._lock:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kv (
                    symbol TEXT PRIMARY KEY,
                    value  TEXT NOT NULL
                )
                """
            )
            self.conn.commit()

    def get(self, symbol: str) -> Any:
        with self._lock:
            row = self.conn.execute(
                "SELECT value FROM kv WHERE symbol = ?",
                (symbol,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row[0])

    def set(self, symbol: str, value: Any) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO kv(symbol, value)
                VALUES(?, ?)
                ON CONFLICT(symbol) DO UPDATE SET value = excluded.value
                """,
                (symbol, json.dumps(value, ensure_ascii=False)),
            )
            self.conn.commit()

    def delete(self, symbol: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM kv WHERE symbol = ?", (symbol,))
            self.conn.commit()

    def list_symbols(self) -> list[str]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT symbol FROM kv ORDER BY symbol"
            ).fetchall()
        return [row[0] for row in rows]
