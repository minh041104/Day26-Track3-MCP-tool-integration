from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import Awaitable
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from implementation.init_db import create_database
from implementation.mcp_server import mcp


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resource_text(resource_result: Any) -> str:
    return resource_result.contents[0].content


async def expect_error(label: str, call: Awaitable[Any]) -> None:
    logging.disable(logging.CRITICAL)
    try:
        await call
    except Exception as exc:
        print(f"[ok] {label}: {exc}")
    else:
        raise AssertionError(f"Expected an error for: {label}")
    finally:
        logging.disable(logging.NOTSET)


async def main() -> None:
    create_database()
    print("[ok] database initialized")

    tools = await mcp.list_tools()
    tool_names = [tool.name for tool in tools]
    require(set(tool_names) == {"search", "insert", "aggregate"}, tool_names)
    print(f"[ok] tools discovered: {tool_names}")

    resources = await mcp.list_resources()
    resource_uris = [str(resource.uri) for resource in resources]
    require("schema://database" in resource_uris, resource_uris)
    print(f"[ok] resources discovered: {resource_uris}")

    templates = await mcp.list_resource_templates()
    template_uris = [str(template.uri_template) for template in templates]
    require("schema://table/{table_name}" in template_uris, template_uris)
    print(f"[ok] resource templates discovered: {template_uris}")

    database_schema = json.loads(resource_text(await mcp.read_resource("schema://database")))
    require({"students", "courses", "enrollments"} <= set(database_schema["tables"]), database_schema)
    print("[ok] read schema://database")

    students_schema = json.loads(resource_text(await mcp.read_resource("schema://table/students")))
    student_columns = {column["name"] for column in students_schema["columns"]}
    require({"id", "name", "email", "cohort", "score"} <= student_columns, students_schema)
    print("[ok] read schema://table/students")

    search_result = await mcp.call_tool(
        "search",
        {
            "table": "students",
            "filters": {"cohort": "A1"},
            "columns": ["id", "name", "score"],
            "order_by": "score",
            "descending": True,
        },
    )
    search_content = search_result.structured_content
    require(search_content["count"] == 2, search_content)
    require(search_content["rows"][0]["name"] == "Binh Tran", search_content)
    print(f"[ok] search call returned {search_content['count']} A1 students")

    insert_result = await mcp.call_tool(
        "insert",
        {
            "table": "students",
            "values": {
                "name": "Verify Student",
                "email": "verify.student@example.edu",
                "cohort": "A3",
                "score": 87.0,
            },
        },
    )
    inserted = insert_result.structured_content["inserted"]
    require(inserted["id"] == 6, inserted)
    print(f"[ok] insert call returned id {inserted['id']}")

    aggregate_result = await mcp.call_tool(
        "aggregate",
        {"table": "students", "metric": "avg", "column": "score", "group_by": "cohort"},
    )
    aggregate_content = aggregate_result.structured_content
    cohorts = {row["cohort"] for row in aggregate_content["rows"]}
    require({"A1", "A2", "A3", "B1"} <= cohorts, aggregate_content)
    print("[ok] aggregate call computed average score by cohort")

    await expect_error("unknown table rejected", mcp.call_tool("search", {"table": "missing"}))
    await expect_error(
        "unknown column rejected",
        mcp.call_tool("search", {"table": "students", "columns": ["missing"]}),
    )
    await expect_error(
        "bad aggregate metric rejected",
        mcp.call_tool("aggregate", {"table": "students", "metric": "median", "column": "score"}),
    )
    await expect_error("empty insert rejected", mcp.call_tool("insert", {"table": "students", "values": {}}))

    create_database()
    print("[ok] database reset after verification")


if __name__ == "__main__":
    asyncio.run(main())
