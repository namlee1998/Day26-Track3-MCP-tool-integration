# SQLite MCP Server Lab

A FastMCP-based MCP server that exposes a SQLite database through safe tools and schema resources.

## Features

This project exposes:

### Tools

- `health_check`
- `list_tables`
- `get_schema`
- `search`
- `insert`
- `aggregate`

### Resources

- `schema://database`
- `schema://table/{table_name}`

## Project Structure

```text
.
├── implementation/
│   ├── db.py
│   ├── init_db.py
│   ├── mcp_server.py
│   ├── verify_server.py
│   └── sqlite_lab.db
├── tests/
│   └── test_server.py
├── .mcp.json
├── start_inspector.sh
├── requirements.txt
└── README.md