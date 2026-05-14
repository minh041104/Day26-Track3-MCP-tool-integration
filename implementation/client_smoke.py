from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"


async def main() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = [tool.name for tool in tools.tools]
            print("tools:", tool_names)

            search_result = await session.call_tool(
                "search",
                {
                    "table": "students",
                    "filters": {"cohort": "A1"},
                    "columns": ["id", "name"],
                },
            )
            print("search:", search_result.content[0].text)

            resources = await session.list_resources()
            resource_uris = [str(resource.uri) for resource in resources.resources]
            print("resources:", resource_uris)

            templates = await session.list_resource_templates()
            template_uris = [str(template.uriTemplate) for template in templates.resourceTemplates]
            print("resource templates:", template_uris)

            schema = await session.read_resource("schema://table/students")
            print("students schema:", schema.contents[0].text[:200].replace("\n", " "))


if __name__ == "__main__":
    asyncio.run(main())
