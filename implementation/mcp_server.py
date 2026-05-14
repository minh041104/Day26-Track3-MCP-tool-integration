from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastmcp import FastMCP

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import DB_PATH, create_database


mcp = FastMCP("SQLite Lab MCP Server")
adapter = SQLiteAdapter(DB_PATH)


def ensure_database() -> None:
    if not Path(DB_PATH).exists():
        create_database(DB_PATH)


@mcp.tool(name="search")
def search(
    table: str,
    filters: Any = None,
    columns: list[str] | str | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """
    Search rows in a table.

    Filters can be either {"column": "value"} for equality filters, or a list
    like [{"column": "score", "op": "gte", "value": 85}].
    Supported operators: eq, ne, gt, gte, lt, lte, like, in, is_null, not_null.
    """
    ensure_database()
    try:
        rows = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "table": table,
        "count": len(rows),
        "limit": limit,
        "offset": offset,
        "rows": rows,
    }


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """
    Insert one row into a table.

    The values object must be non-empty and every key must match a real column.
    The inserted payload is returned, including the generated id when present.
    """
    ensure_database()
    try:
        inserted = adapter.insert(table=table, values=values)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "table": table,
        "inserted": inserted,
    }


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: Any = None,
    group_by: list[str] | str | None = None,
) -> dict[str, Any]:
    """
    Aggregate rows in a table.

    Supported metrics: count, avg, sum, min, max. Count can omit column to use
    COUNT(*); other metrics require a column.
    """
    ensure_database()
    try:
        rows = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by,
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "table": table,
        "metric": metric,
        "column": column,
        "count": len(rows),
        "rows": rows,
    }


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full SQLite database schema as JSON text."""
    ensure_database()
    return json.dumps(adapter.get_database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""
    ensure_database()
    try:
        schema = adapter.get_table_schema(table_name)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    return json.dumps(schema, indent=2)


if __name__ == "__main__":
    ensure_database()
    mcp.run()
