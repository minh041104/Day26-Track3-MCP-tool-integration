# Lab: Build a Database MCP Server with FastMCP and SQLite

## Goal

Build a Model Context Protocol (MCP) server using FastMCP that exposes a small database through:

- `search`
- `insert`
- `aggregate`

You must also expose the database schema as an MCP resource, test the server with Inspector or equivalent tooling, and show the server working from at least one MCP client.

## Current Implementation

This repository includes a working SQLite + FastMCP implementation under `implementation/`.

```text
implementation/
  db.py              # SQLite adapter with validation and safe parameter binding
  init_db.py         # reproducible schema and seed data
  mcp_server.py      # FastMCP tools and resources
  verify_server.py   # repeatable verification script
```

The sample database contains:

- `students`
- `courses`
- `enrollments`

## Setup

Recommended: use a virtual environment so FastMCP dependencies do not affect other Python projects.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Initialize the SQLite database:

```powershell
python implementation\init_db.py
```

Start the MCP server over stdio:

```powershell
python implementation\mcp_server.py
```

## Tools

The server exposes exactly three tools:

- `search`: search rows with optional filters, column selection, ordering, limit, and offset
- `insert`: insert one row and return the inserted payload
- `aggregate`: run `count`, `avg`, `sum`, `min`, or `max`, optionally grouped by columns

Example filter shapes:

```json
{"cohort": "A1"}
```

```json
[{"column": "score", "op": "gte", "value": 85}]
```

Supported filter operators:

- `eq`, `ne`, `gt`, `gte`, `lt`, `lte`
- `like`
- `in`
- `is_null`, `not_null`

## Resources

The server exposes schema context as MCP resources:

- `schema://database`
- `schema://table/{table_name}`

Examples:

- `schema://table/students`
- `schema://table/courses`
- `schema://table/enrollments`

## Verification

Run the repeatable verification script:

```powershell
python implementation\verify_server.py
```

The script verifies:

- database initialization
- tool discovery for `search`, `insert`, and `aggregate`
- schema resource discovery
- schema resource template discovery
- valid `search`, `insert`, and `aggregate` calls
- invalid requests for unknown tables, unknown columns, bad aggregate metrics, and empty inserts

Expected ending:

```text
[ok] database reset after verification
```

## MCP Client Integration

This repo includes a project-scoped Claude Code MCP config in `.mcp.json`.

Verify Claude can see the server:

```powershell
claude mcp list
claude mcp get sqlite-lab
```

Verified local result:

```text
sqlite-lab: C:\Users\mlodt\miniconda3\python.exe C:\VinuniLabs\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py - Connected
```

The same server is also verified with a lightweight MCP Python client:

```powershell
python implementation\client_smoke.py
```

Expected output includes:

```text
tools: ['search', 'insert', 'aggregate']
resources: ['schema://database']
resource templates: ['schema://table/{table_name}']
```

If you move the repository or use a different Python interpreter, update `.mcp.json` to point to the new absolute paths.

## Demo

Use [DEMO.md](DEMO.md) as the short demo checklist. It covers setup, verification, MCP client smoke test, and Claude Code connection status.

Use [DEMO_SCRIPT_VI.md](DEMO_SCRIPT_VI.md) as the Vietnamese presentation script.

A generated silent Vietnamese MP4 demo is available at:

```text
demo_assets/sqlite_mcp_lab_demo_vi.mp4
```

The English version is available at:

```text
demo_assets/sqlite_mcp_lab_demo.mp4
```

Regenerate the Vietnamese video with:

```powershell
python demo_assets\create_demo_video_vi.py
```

Regenerate the English video with:

```powershell
python demo_assets\create_demo_video.py
```

## Learning Outcomes

By the end of this lab, students should be able to:

- explain what MCP tools and resources are
- build a FastMCP server in Python
- connect FastMCP to a SQLite database
- safely validate database requests before executing SQL
- expose dynamic schema context through `@mcp.resource(...)`
- test tool schemas, normal calls, and error responses
- connect the server to an MCP client such as Claude Code, Codex, or Gemini CLI

## Required Features

### Part 1: MCP Server

Implement a FastMCP server that exposes exactly these tool categories:

1. `search`
2. `insert`
3. `aggregate`

Your server may use SQLite for the main implementation. If you want to support PostgreSQL too, design the code so the database layer can be swapped later.

### Part 2: Resource

Expose database schema information as MCP resources:

- one resource for the full database schema
- one dynamic resource template for a single table schema

Suggested URIs:

- `schema://database`
- `schema://table/{table_name}`

### Part 3: Validation and Error Handling

Your tools must reject unsafe or invalid requests:

- unknown table names
- unknown column names
- unsupported filter operators
- invalid aggregate requests
- empty inserts

Do not build SQL by blindly concatenating raw user input.

### Part 4: Testing and Verification

Verify all of the following:

1. the server starts correctly
2. the three tools are discoverable
3. the schema resource is discoverable
4. valid tool calls return useful results
5. invalid tool calls return clear errors
6. at least one MCP client can connect and use the server

### Part 5: Demo Deliverables

Prepare:

- GitHub repository
- setup instructions
- tool descriptions
- testing steps
- at least one client configuration example
- short demo video, around 2 minutes

Inspector screenshots are recommended if you use MCP Inspector.

## Suggested Project Structure

```text
implementation/
  db.py
  init_db.py
  mcp_server.py
  verify_server.py
  tests/
    test_server.py
```

## Recommended Data Model

Use a small relational dataset so `search`, `insert`, and `aggregate` are easy to demo. Example:

- `students`
- `courses`
- `enrollments`

## Example Tasks to Demonstrate

- search all students in cohort `A1`
- insert a new student
- count rows in a table
- compute average score by cohort
- read the full schema resource
- read `schema://table/students`
- show an invalid request, such as searching a missing table

## FastMCP and Inspector References

- FastMCP quickstart: https://gofastmcp.com/v2/getting-started/quickstart
- FastMCP resources: https://gofastmcp.com/v2/servers/resources
- MCP Inspector: https://modelcontextprotocol.io/docs/tools/inspector

## Client Setup Notes

### Claude Code

Anthropic documents local JSON config and `claude mcp add` flows here:

- https://code.claude.com/docs/en/mcp

Claude Code supports MCP resources via `@server:resource-uri` references and supports environment variable expansion in `.mcp.json`.

### Codex

OpenAI documents Codex MCP setup here:

- https://developers.openai.com/learn/docs-mcp

Codex supports MCP server configuration through the CLI and `~/.codex/config.toml`.

### Gemini CLI

Gemini CLI has a built-in MCP manager. In the verified local workflow, the simplest path is:

```bash
gemini mcp add sqlite-lab /ABSOLUTE/PATH/TO/python /ABSOLUTE/PATH/TO/implementation/mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
```

Gemini CLI also documents configuration details here:

- https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md

Expected outcome:

- the server appears as `Connected`
- Gemini can discover `search`, `insert`, and `aggregate`
- a headless smoke test works with `gemini --allowed-mcp-server-names sqlite-lab --yolo -p "..."`

### Antigravity

Antigravity commonly uses an `mcp_config.json` file with a shape similar to Gemini CLI. Verify the current product behavior in your installed version before grading against exact UI steps.

## Deliverable Checklist

- working FastMCP server
- SQLite database and seed data
- `search`, `insert`, `aggregate` tools
- schema resource and schema resource template
- verification steps
- automated tests or repeatable verification script
- client configuration example
- README with setup and demo steps
- Inspector startup command or helper script
- at least one verified Gemini CLI or Claude/Codex client test

## Bonus

Optional bonus:

- add authentication for SSE or HTTP transport
- support both SQLite and PostgreSQL with the same MCP surface
- add richer output annotations or pagination
