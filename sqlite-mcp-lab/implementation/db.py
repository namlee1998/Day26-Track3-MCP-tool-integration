from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "sqlite_lab.db"

SUPPORTED_OPERATORS = {"eq", "gt", "lt", "gte", "lte", "like", "in"}
SUPPORTED_METRICS = {"count", "avg", "sum", "min", "max"}


class ValidationError(ValueError):
    """Raised when user-provided MCP input is invalid."""


class SQLiteAdapter:
    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON;")
        return self.conn

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def list_tables(self) -> list[str]:
        conn = self.connect()
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        return [row["name"] for row in rows]

    def table_exists(self, table_name: str) -> bool:
        return table_name in self.list_tables()

    def validate_table(self, table_name: str) -> None:
        if table_name not in self.list_tables():
            raise ValidationError(f"Unknown table: {table_name}")

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        self.validate_table(table_name)

        conn = self.connect()
        rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()

        return [
            {
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "nullable": not bool(row["notnull"]),
                "default": row["dflt_value"],
                "pk": bool(row["pk"]),
            }
            for row in rows
        ]

    def list_columns(self, table_name: str) -> list[str]:
        schema = self.get_table_schema(table_name)
        return [column["name"] for column in schema]

    def validate_column(self, table_name: str, column_name: str) -> None:
        columns = self.list_columns(table_name)

        if column_name not in columns:
            raise ValidationError(f"Unknown column: {column_name} in {table_name}")

    def validate_columns(self, table_name: str, columns: list[str]) -> None:
        for column in columns:
            self.validate_column(table_name, column)

    def quote_identifier(self, identifier: str) -> str:
        return f'"{identifier}"'

    def build_where_clause(
        self,
        table_name: str,
        filters: dict[str, Any] | None,
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []

        for column_name, condition in filters.items():
            self.validate_column(table_name, column_name)

            if not isinstance(condition, dict):
                raise ValidationError(
                    f"Filter for column '{column_name}' must be an object"
                )

            op = condition.get("op")
            value = condition.get("value")

            if op not in SUPPORTED_OPERATORS:
                raise ValidationError(f"Unsupported operator: {op}")

            quoted_column = self.quote_identifier(column_name)

            if op == "eq":
                clauses.append(f"{quoted_column} = ?")
                params.append(value)

            elif op == "gt":
                clauses.append(f"{quoted_column} > ?")
                params.append(value)

            elif op == "lt":
                clauses.append(f"{quoted_column} < ?")
                params.append(value)

            elif op == "gte":
                clauses.append(f"{quoted_column} >= ?")
                params.append(value)

            elif op == "lte":
                clauses.append(f"{quoted_column} <= ?")
                params.append(value)

            elif op == "like":
                clauses.append(f"{quoted_column} LIKE ?")
                params.append(value)

            elif op == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError(
                        "Filter value for operator 'in' must be a non-empty list"
                    )

                placeholders = ", ".join(["?"] * len(value))
                clauses.append(f"{quoted_column} IN ({placeholders})")
                params.extend(value)

        return " WHERE " + " AND ".join(clauses), params

    def search(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self.validate_table(table)

        if limit < 1:
            raise ValidationError("Limit must be greater than 0")

        if offset < 0:
            raise ValidationError("Offset cannot be negative")

        if columns:
            self.validate_columns(table, columns)
            select_clause = ", ".join(self.quote_identifier(col) for col in columns)
        else:
            select_clause = "*"

        where_clause, params = self.build_where_clause(table, filters)

        order_clause = ""
        if order_by:
            self.validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            order_clause = f" ORDER BY {self.quote_identifier(order_by)} {direction}"

        sql = (
            f"SELECT {select_clause} "
            f"FROM {self.quote_identifier(table)}"
            f"{where_clause}"
            f"{order_clause}"
            f" LIMIT ? OFFSET ?"
        )

        query_params = [*params, limit, offset]

        conn = self.connect()
        rows = conn.execute(sql, query_params).fetchall()

        count_sql = (
            f"SELECT COUNT(*) AS count "
            f"FROM {self.quote_identifier(table)}"
            f"{where_clause}"
        )
        count_row = conn.execute(count_sql, params).fetchone()

        return {
            "rows": [dict(row) for row in rows],
            "count": int(count_row["count"]),
            "limit": limit,
            "offset": offset,
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self.validate_table(table)

        if not values:
            raise ValidationError("Insert values cannot be empty")

        columns = list(values.keys())
        self.validate_columns(table, columns)

        quoted_columns = ", ".join(self.quote_identifier(col) for col in columns)
        placeholders = ", ".join(["?"] * len(columns))

        sql = (
            f"INSERT INTO {self.quote_identifier(table)} "
            f"({quoted_columns}) VALUES ({placeholders})"
        )

        conn = self.connect()
        cursor = conn.execute(sql, [values[col] for col in columns])
        conn.commit()

        inserted_id = cursor.lastrowid

        result = self.search(
            table=table,
            filters={"id": {"op": "eq", "value": inserted_id}},
            limit=1,
        )

        inserted_row = result["rows"][0] if result["rows"] else None

        return {
            "inserted_id": inserted_id,
            "row": inserted_row,
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: dict[str, Any] | None = None,
        group_by: str | None = None,
    ) -> list[dict[str, Any]]:
        self.validate_table(table)

        if metric not in SUPPORTED_METRICS:
            raise ValidationError(f"Unsupported metric: {metric}")

        if metric != "count" and not column:
            raise ValidationError(f"Column required for metric {metric}")

        if column:
            self.validate_column(table, column)

        if group_by:
            self.validate_column(table, group_by)

        where_clause, params = self.build_where_clause(table, filters)

        if metric == "count":
            metric_expr = "COUNT(*)"
        else:
            metric_expr = f"{metric.upper()}({self.quote_identifier(column)})"

        if group_by:
            sql = (
                f"SELECT {self.quote_identifier(group_by)} AS group_value, "
                f"{metric_expr} AS value "
                f"FROM {self.quote_identifier(table)}"
                f"{where_clause} "
                f"GROUP BY {self.quote_identifier(group_by)} "
                f"ORDER BY {self.quote_identifier(group_by)} ASC"
            )
        else:
            sql = (
                f"SELECT {metric_expr} AS value "
                f"FROM {self.quote_identifier(table)}"
                f"{where_clause}"
            )

        conn = self.connect()
        rows = conn.execute(sql, params).fetchall()

        if group_by:
            return [
                {
                    "group": row["group_value"],
                    "value": row["value"],
                }
                for row in rows
            ]

        return [
            {
                "group": None,
                "value": rows[0]["value"] if rows else None,
            }
        ]

    def __enter__(self) -> "SQLiteAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def main() -> None:
    adapter = SQLiteAdapter()

    try:
        print("Database path:")
        print(adapter.db_path)

        print("\nTables:")
        for table in adapter.list_tables():
            print(f"- {table}")

        print("\nSearch students cohort A1:")
        result = adapter.search(
            table="students",
            filters={"cohort": {"op": "eq", "value": "A1"}},
            order_by="score",
            descending=True,
        )
        print(result)

        print("\nAggregate avg score by cohort:")
        result = adapter.aggregate(
            table="students",
            metric="avg",
            column="score",
            group_by="cohort",
        )
        print(result)

        print("\nValidation check:")
        try:
            adapter.search(table="not_real")
        except ValidationError as exc:
            print(f"Expected error: {exc}")

    finally:
        adapter.close()


if __name__ == "__main__":
    main()