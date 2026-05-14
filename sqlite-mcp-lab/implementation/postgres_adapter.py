from __future__ import annotations

import os
from typing import Any

from base_adapter import BaseAdapter


class PostgreSQLAdapter(BaseAdapter):
    """
    Bonus adapter skeleton.

    This file proves the architecture supports PostgreSQL.
    Full production parity can be implemented later by porting SQLiteAdapter SQL
    placeholder style from ? to %s.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.conn = None

        if not self.database_url:
            raise ValueError("DATABASE_URL is required for PostgreSQLAdapter")

    def connect(self) -> Any:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is not installed. Run: pip install psycopg[binary]"
            ) from exc

        if self.conn is None:
            self.conn = psycopg.connect(self.database_url)

        return self.conn

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def list_tables(self) -> list[str]:
        conn = self.connect()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """
            )
            return [row[0] for row in cur.fetchall()]

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        conn = self.connect()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (table_name,),
            )

            rows = cur.fetchall()

        if not rows:
            raise ValueError(f"Unknown table: {table_name}")

        return [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
                "pk": False,
            }
            for row in rows
        ]

    def search(self, *args, **kwargs) -> dict[str, Any]:
        raise NotImplementedError("PostgreSQL search is not implemented yet")

    def insert(self, *args, **kwargs) -> dict[str, Any]:
        raise NotImplementedError("PostgreSQL insert is not implemented yet")

    def aggregate(self, *args, **kwargs) -> list[dict[str, Any]]:
        raise NotImplementedError("PostgreSQL aggregate is not implemented yet")