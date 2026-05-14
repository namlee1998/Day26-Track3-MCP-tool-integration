from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any

from db import SQLiteAdapter, ValidationError


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "sqlite_lab.db"
MCP_SERVER_PATH = BASE_DIR / "mcp_server.py"

EXPECTED_TABLES = {"students", "courses", "enrollments"}

EXPECTED_COLUMNS = {
    "students": {"id", "name", "cohort", "score", "created_at"},
    "courses": {"id", "title", "credits"},
    "enrollments": {"id", "student_id", "course_id", "grade"},
}


def pass_check(message: str) -> None:
    print(f"[PASS] {message}")


def fail_check(message: str) -> None:
    print(f"[FAIL] {message}")
    raise SystemExit(1)


def assert_equal(actual: Any, expected: Any, message: str) -> None:
    if actual != expected:
        fail_check(f"{message}. Expected={expected!r}, actual={actual!r}")

    pass_check(message)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        fail_check(message)

    pass_check(message)


def assert_raises_message(
    fn,
    expected_message_part: str,
    message: str,
) -> None:
    try:
        fn()
    except Exception as exc:
        if expected_message_part not in str(exc):
            fail_check(
                f"{message}. Wrong error. "
                f"Expected to contain={expected_message_part!r}, actual={str(exc)!r}"
            )
        pass_check(message)
        return

    fail_check(f"{message}. Expected exception was not raised.")


def load_mcp_server_module():
    spec = importlib.util.spec_from_file_location("mcp_server", MCP_SERVER_PATH)

    if spec is None or spec.loader is None:
        fail_check("Could not load mcp_server.py import spec")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_db_file_exists() -> None:
    assert_true(
        DB_PATH.exists(),
        f"Database file exists: {DB_PATH}",
    )


def verify_sqlite_connection() -> None:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1;")
        conn.close()
    except sqlite3.Error as exc:
        fail_check(f"SQLite connection failed: {exc}")

    pass_check("SQLite connection works")


def verify_tables(adapter: SQLiteAdapter) -> None:
    tables = set(adapter.list_tables())
    missing = EXPECTED_TABLES - tables

    assert_true(
        not missing,
        f"Expected tables found: {sorted(EXPECTED_TABLES)}",
    )


def verify_schemas(adapter: SQLiteAdapter) -> None:
    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        schema = adapter.get_table_schema(table_name)
        actual_columns = {column["name"] for column in schema}
        missing_columns = expected_columns - actual_columns

        assert_true(
            not missing_columns,
            f"Schema valid for table: {table_name}",
        )


def verify_seed_data(adapter: SQLiteAdapter) -> None:
    conn = adapter.connect()

    expected_min_counts = {
        "students": 10,
        "courses": 5,
        "enrollments": 15,
    }

    for table_name, minimum_count in expected_min_counts.items():
        row = conn.execute(f'SELECT COUNT(*) AS count FROM "{table_name}"').fetchone()
        count = int(row["count"])

        assert_true(
            count >= minimum_count,
            f"Seed data valid for {table_name}: {count} rows",
        )


def verify_mcp_server_importable() -> Any:
    assert_true(
        MCP_SERVER_PATH.exists(),
        f"mcp_server.py exists: {MCP_SERVER_PATH}",
    )

    module = load_mcp_server_module()

    assert_true(hasattr(module, "mcp"), "mcp_server.py exposes variable: mcp")
    assert_true(hasattr(module, "main"), "mcp_server.py exposes function: main")

    return module


def verify_search(adapter: SQLiteAdapter) -> None:
    result = adapter.search(
        table="students",
        filters={"cohort": {"op": "eq", "value": "A1"}},
        columns=["id", "name", "cohort", "score"],
        limit=5,
        offset=0,
        order_by="score",
        descending=True,
    )

    assert_true("rows" in result, "search returns rows")
    assert_true("count" in result, "search returns count")
    assert_true(result["count"] >= 3, "search filters cohort=A1")
    assert_true(
        all(row["cohort"] == "A1" for row in result["rows"]),
        "search result rows match filter",
    )

    scores = [row["score"] for row in result["rows"]]
    assert_equal(scores, sorted(scores, reverse=True), "search supports descending order")


def verify_search_like_and_in(adapter: SQLiteAdapter) -> None:
    like_result = adapter.search(
        table="students",
        filters={"name": {"op": "like", "value": "%Nguyen%"}},
        limit=10,
    )
    assert_true(like_result["count"] >= 1, "search supports LIKE operator")

    in_result = adapter.search(
        table="students",
        filters={"cohort": {"op": "in", "value": ["A1", "B1"]}},
        limit=20,
    )
    assert_true(in_result["count"] >= 1, "search supports IN operator")
    assert_true(
        all(row["cohort"] in {"A1", "B1"} for row in in_result["rows"]),
        "IN result rows match allowed cohorts",
    )


def verify_insert(adapter: SQLiteAdapter) -> None:
    result = adapter.insert(
        table="students",
        values={
            "name": "Verify Student",
            "cohort": "Z9",
            "score": 8.8,
            "created_at": "2026-05-14T12:00:00",
        },
    )

    assert_true(result["inserted_id"] is not None, "insert returns inserted_id")
    assert_true(result["row"] is not None, "insert returns inserted row")
    assert_equal(result["row"]["name"], "Verify Student", "inserted row has correct name")


def verify_aggregate(adapter: SQLiteAdapter) -> None:
    count_result = adapter.aggregate(
        table="students",
        metric="count",
    )

    assert_true(isinstance(count_result, list), "aggregate count returns list")
    assert_true(count_result[0]["value"] >= 10, "aggregate count students works")

    avg_result = adapter.aggregate(
        table="students",
        metric="avg",
        column="score",
        group_by="cohort",
    )

    assert_true(isinstance(avg_result, list), "aggregate avg group_by returns list")
    assert_true(len(avg_result) >= 1, "aggregate avg group_by has rows")
    assert_true(
        all("group" in row and "value" in row for row in avg_result),
        "aggregate rows contain group and value",
    )


def verify_error_handling(adapter: SQLiteAdapter) -> None:
    assert_raises_message(
        lambda: adapter.search(table="not_a_table"),
        "Unknown table: not_a_table",
        "invalid table gives clear error",
    )

    assert_raises_message(
        lambda: adapter.search(table="students", columns=["not_a_column"]),
        "Unknown column: not_a_column in students",
        "invalid column gives clear error",
    )

    assert_raises_message(
        lambda: adapter.search(
            table="students",
            filters={"score": {"op": "between", "value": [1, 10]}},
        ),
        "Unsupported operator: between",
        "invalid operator gives clear error",
    )

    assert_raises_message(
        lambda: adapter.aggregate(table="students", metric="median", column="score"),
        "Unsupported metric: median",
        "invalid metric gives clear error",
    )

    assert_raises_message(
        lambda: adapter.insert(table="students", values={}),
        "Insert values cannot be empty",
        "empty insert gives clear error",
    )

    assert_raises_message(
        lambda: adapter.aggregate(table="students", metric="avg"),
        "Column required for metric avg",
        "missing aggregate column gives clear error",
    )


def verify_resources(module: Any) -> None:
    database_schema = module.database_schema()
    parsed_database_schema = json.loads(database_schema)

    assert_true(
        EXPECTED_TABLES.issubset(set(parsed_database_schema.keys())),
        "database schema resource returns all expected tables",
    )

    table_schema = module.table_schema("students")
    parsed_table_schema = json.loads(table_schema)

    assert_equal(
        parsed_table_schema["table"],
        "students",
        "table schema resource returns requested table",
    )

    student_columns = {column["name"] for column in parsed_table_schema["schema"]}

    assert_true(
        EXPECTED_COLUMNS["students"].issubset(student_columns),
        "table schema resource returns student columns",
    )


def main() -> None:
    print("=== Phase 5 Verification ===")

    verify_db_file_exists()
    verify_sqlite_connection()
    module = verify_mcp_server_importable()

    adapter = SQLiteAdapter()

    try:
        verify_tables(adapter)
        verify_schemas(adapter)
        verify_seed_data(adapter)

        verify_search(adapter)
        verify_search_like_and_in(adapter)
        verify_insert(adapter)
        verify_aggregate(adapter)
        verify_error_handling(adapter)
        verify_resources(module)

    finally:
        adapter.close()

    print("\n=== Result ===")
    print("Phase 5 verification passed.")


if __name__ == "__main__":
    main()