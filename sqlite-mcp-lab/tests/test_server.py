from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_DIR = PROJECT_ROOT / "implementation"

if str(IMPLEMENTATION_DIR) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATION_DIR))

from db import SQLiteAdapter, ValidationError  # noqa: E402
import mcp_server  # noqa: E402


@pytest.fixture()
def adapter() -> SQLiteAdapter:
    db = SQLiteAdapter()
    try:
        yield db
    finally:
        db.close()


def test_search_valid(adapter: SQLiteAdapter) -> None:
    result = adapter.search(
        table="students",
        filters={"cohort": {"op": "eq", "value": "A1"}},
        columns=["id", "name", "cohort", "score"],
        limit=5,
        order_by="score",
        descending=True,
    )

    assert "rows" in result
    assert "count" in result
    assert result["count"] >= 1
    assert all(row["cohort"] == "A1" for row in result["rows"])

    scores = [row["score"] for row in result["rows"]]
    assert scores == sorted(scores, reverse=True)


def test_search_invalid_table(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError, match="Unknown table: bad_table"):
        adapter.search(table="bad_table")


def test_search_invalid_column(adapter: SQLiteAdapter) -> None:
    with pytest.raises(
        ValidationError,
        match="Unknown column: bad_column in students",
    ):
        adapter.search(
            table="students",
            columns=["id", "bad_column"],
        )


def test_search_invalid_operator(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError, match="Unsupported operator: between"):
        adapter.search(
            table="students",
            filters={"score": {"op": "between", "value": [7, 9]}},
        )


def test_search_like(adapter: SQLiteAdapter) -> None:
    result = adapter.search(
        table="students",
        filters={"name": {"op": "like", "value": "%Nguyen%"}},
        limit=10,
    )

    assert result["count"] >= 1


def test_search_in(adapter: SQLiteAdapter) -> None:
    result = adapter.search(
        table="students",
        filters={"cohort": {"op": "in", "value": ["A1", "A2"]}},
        limit=20,
    )

    assert result["count"] >= 1
    assert all(row["cohort"] in {"A1", "A2"} for row in result["rows"])


def test_insert_valid(adapter: SQLiteAdapter) -> None:
    result = adapter.insert(
        table="students",
        values={
            "name": "Pytest Student",
            "cohort": "T1",
            "score": 8.4,
            "created_at": "2026-05-14T13:00:00",
        },
    )

    assert result["inserted_id"] is not None
    assert result["row"]["name"] == "Pytest Student"
    assert result["row"]["cohort"] == "T1"


def test_insert_empty(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError, match="Insert values cannot be empty"):
        adapter.insert(table="students", values={})


def test_insert_bad_column(adapter: SQLiteAdapter) -> None:
    with pytest.raises(
        ValidationError,
        match="Unknown column: bad_column in students",
    ):
        adapter.insert(
            table="students",
            values={
                "name": "Bad Student",
                "bad_column": "bad",
            },
        )


def test_aggregate_count(adapter: SQLiteAdapter) -> None:
    result = adapter.aggregate(
        table="students",
        metric="count",
    )

    assert isinstance(result, list)
    assert result[0]["group"] is None
    assert result[0]["value"] >= 10


def test_aggregate_avg(adapter: SQLiteAdapter) -> None:
    result = adapter.aggregate(
        table="students",
        metric="avg",
        column="score",
        group_by="cohort",
    )

    assert isinstance(result, list)
    assert len(result) >= 1
    assert all("group" in row and "value" in row for row in result)


def test_aggregate_bad_metric(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError, match="Unsupported metric: median"):
        adapter.aggregate(
            table="students",
            metric="median",
            column="score",
        )


def test_aggregate_missing_column(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError, match="Column required for metric avg"):
        adapter.aggregate(
            table="students",
            metric="avg",
        )


def test_schema_resource() -> None:
    payload = mcp_server.database_schema()
    parsed = json.loads(payload)

    assert "students" in parsed
    assert "courses" in parsed
    assert "enrollments" in parsed


def test_table_schema_resource() -> None:
    payload = mcp_server.table_schema("students")
    parsed = json.loads(payload)

    assert parsed["table"] == "students"

    columns = {column["name"] for column in parsed["schema"]}

    assert {"id", "name", "cohort", "score", "created_at"}.issubset(columns)


def test_table_schema_resource_invalid_table() -> None:
    with pytest.raises(ValidationError, match="Unknown table: bad_table"):
        mcp_server.table_schema("bad_table")