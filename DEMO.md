# Demo Checklist

## 1. Show Setup

```powershell
python -m pip install -r requirements.txt
python implementation\init_db.py
```

Mention that the database has three tables: `students`, `courses`, and `enrollments`.

## 2. Show Automated Verification

```powershell
python implementation\verify_server.py
```

Point out these checks:

- tools discovered: `search`, `insert`, `aggregate`
- resources discovered: `schema://database`
- resource template discovered: `schema://table/{table_name}`
- invalid requests are rejected with clear errors

## 3. Show MCP Client Smoke Test

```powershell
python implementation\client_smoke.py
```

This starts `implementation/mcp_server.py` over stdio using the MCP Python client, lists tools and resources, calls `search`, and reads `schema://table/students`.

## 4. Show Claude Code Client Config

```powershell
claude mcp list
claude mcp get sqlite-lab
```

Expected status:

```text
sqlite-lab ... Connected
```

The project-level Claude config is in `.mcp.json`.
