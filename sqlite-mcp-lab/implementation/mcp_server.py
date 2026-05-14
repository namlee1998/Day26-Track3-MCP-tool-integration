from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from db import SQLiteAdapter


mcp = FastMCP("SQLite Lab")


# ---------------------------------------------------------------------------
# Phase 1 helper tools
# ---------------------------------------------------------------------------

@mcp.tool()
def health_check() -> dict[str, Any]:
    """
    Smoke-test tool for checking whether the MCP server can access SQLite.
    """
    adapter = SQLiteAdapter()

    try:
        tables = adapter.list_tables()
        return {
            "status": "ok",
            "server": "SQLite Lab",
            "database": str(adapter.db_path),
            "tables": tables,
            "table_count": len(tables),
        }
    finally:
        adapter.close()


@mcp.tool()
def list_tables() -> dict[str, Any]:
    """
    List all user-defined SQLite tables.
    """
    adapter = SQLiteAdapter()

    try:
        tables = adapter.list_tables()
        return {
            "tables": tables,
            "count": len(tables),
        }
    finally:
        adapter.close()


@mcp.tool()
def get_schema(table_name: str) -> dict[str, Any]:
    """
    Return schema information for a single table.

    Args:
        table_name: Name of the SQLite table.
    """
    adapter = SQLiteAdapter()

    try:
        schema = adapter.get_table_schema(table_name)
        return {
            "table": table_name,
            "schema": schema,
        }
    finally:
        adapter.close()


# ---------------------------------------------------------------------------
# Phase 2 core tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search(
    table: str,
    filters: dict[str, Any] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """
    Search rows from a SQLite table using validated filters.
    """
    adapter = SQLiteAdapter()

    try:
        return adapter.search(
            table=table,
            filters=filters,
            columns=columns,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    finally:
        adapter.close()


@mcp.tool()
def insert(
    table: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Insert a new row into a SQLite table.
    """
    adapter = SQLiteAdapter()

    try:
        return adapter.insert(
            table=table,
            values=values,
        )
    finally:
        adapter.close()


@mcp.tool()
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: dict[str, Any] | None = None,
    group_by: str | None = None,
) -> list[dict[str, Any]]:
    """
    Aggregate rows from a SQLite table.
    """
    adapter = SQLiteAdapter()

    try:
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    finally:
        adapter.close()


# ---------------------------------------------------------------------------
# Phase 3 MCP resources
# ---------------------------------------------------------------------------

@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Return JSON schema for the whole SQLite database.

    Resource URI:
        schema://database
    """
    adapter = SQLiteAdapter()

    try:
        schema_by_table: dict[str, Any] = {}

        for table_name in adapter.list_tables():
            schema_by_table[table_name] = adapter.get_table_schema(table_name)

        return json.dumps(
            schema_by_table,
            ensure_ascii=False,
            indent=2,
        )
    finally:
        adapter.close()


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Return JSON schema for one SQLite table.

    Resource URI:
        schema://table/{table_name}

    Example:
        schema://table/students
    """
    adapter = SQLiteAdapter()

    try:
        schema = adapter.get_table_schema(table_name)

        payload = {
            "table": table_name,
            "schema": schema,
        }

        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    finally:
        adapter.close()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()