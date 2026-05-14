# SQLite MCP Server Lab

A production-quality MCP server built with **FastMCP** that exposes a SQLite database through safe, validated tools and schema resources. Supports HTTP transport with Bearer token authentication, and is architected to support both SQLite and PostgreSQL behind a shared interface.

---

## Features

### Tools
| Tool | Description |
|------|-------------|
| `health_check` | Smoke-test: verify server can access SQLite |
| `list_tables` | List all user-defined tables |
| `get_schema` | Return schema for a single table |
| `search` | Query rows with filters, ordering, and pagination |
| `insert` | Insert a new row and return the inserted payload |
| `aggregate` | Compute `count`, `avg`, `sum`, `min`, `max` with optional `group_by` |

### Resources
| URI | Description |
|-----|-------------|
| `schema://database` | Full database schema (all tables) |
| `schema://table/{table_name}` | Schema for a single table |

### Bonus
- **HTTP + Bearer Auth** — `mcp_http_server.py` exposes the server over HTTP with middleware that validates `Authorization: Bearer <token>`
- **Shared Adapter Interface** — `BaseAdapter` (ABC) is implemented by both `SQLiteAdapter` and `PostgreSQLAdapter`, making the database layer swappable
- **Pagination** — `search` supports `limit` and `offset` for page-by-page data retrieval

---

## Project Structure

```text
sqlite-mcp-lab/
├── implementation/
│   ├── base_adapter.py        # Abstract base class (shared interface)
│   ├── db.py                  # SQLiteAdapter implementation
│   ├── postgres_adapter.py    # PostgreSQLAdapter implementation (bonus)
│   ├── init_db.py             # Schema creation + seed data
│   ├── mcp_server.py          # Main FastMCP server (stdio)
│   ├── mcp_http_server.py     # HTTP server with Bearer auth (bonus)
│   ├── verify_server.py       # Standalone verification script
│   └── sqlite_lab.db          # SQLite database (auto-generated)
├── tests/
│   └── test_server.py         # pytest test suite
├── .mcp.json                  # Claude Code / Claude Desktop config
├── start_inspector.sh         # MCP Inspector launcher
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/namlee1998/Day26-Track3-MCP-tool-integration.git
cd Day26-Track3-MCP-tool-integration/sqlite-mcp-lab

python -m venv .venv

# Mac/Linux
source .venv/bin/activate

# Windows (Git Bash)
source .venv/Scripts/activate

pip install -r requirements.txt
```

### 2. Initialize the database

```bash
python implementation/init_db.py
```

Expected output:
```
Database initialized successfully.
Tables: students, courses, enrollments
```

### 3. Start the MCP server

```bash
python implementation/mcp_server.py
```

Expected output:
```
Starting MCP server 'SQLite Lab' with transport 'stdio'
```

---

## Testing with MCP Inspector

```bash
chmod +x start_inspector.sh
./start_inspector.sh
```

Or directly:
```bash
npx -y @modelcontextprotocol/inspector python implementation/mcp_server.py
```

Open the Inspector UI and verify:
- 6 tools are listed: `health_check`, `list_tables`, `get_schema`, `search`, `insert`, `aggregate`
- 1 resource listed: `schema://database`

### Example tool calls in Inspector

**search** — filter students by cohort:
```json
{
  "table": "students",
  "filters": { "cohort": { "op": "eq", "value": "A1" } },
  "order_by": "score",
  "descending": true
}
```

**insert** — add a new student:
```json
{
  "table": "students",
  "values": {
    "name": "Demo User",
    "cohort": "C1",
    "score": 95.0,
    "created_at": "2024-01-01"
  }
}
```

**aggregate** — average score per cohort:
```json
{
  "table": "students",
  "metric": "avg",
  "column": "score",
  "group_by": "cohort"
}
```

**Error case** — invalid table:
```json
{
  "table": "fake_table"
}
```
Expected: `"Unknown table: fake_table"`

---

## Client Integration

### Claude Desktop

Edit `claude_desktop_config.json`:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows (Store):** `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "command": "/absolute/path/to/python",
      "args": ["/absolute/path/to/sqlite-mcp-lab/implementation/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop completely, then test:
```
List all tables in my SQLite database
Search for all students in cohort A1, sort by score descending
What is the average score for each cohort?
Insert a new student named "Demo User" in cohort C1 with score 95
```

### Claude Code / `.mcp.json`

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "python",
      "args": ["implementation/mcp_server.py"]
    }
  }
}
```

---

## Verification

Run the verification script:

```bash
python implementation/verify_server.py
```

Run the test suite:

```bash
pytest tests/ -v
```

---

## Bonus: HTTP Server with Bearer Auth

Start the HTTP server:

```bash
cd implementation
MCP_BEARER_TOKEN=my-secret-token python mcp_http_server.py
```

Test authentication:

```bash
# No token → 401
curl -s -o - -w "\nHTTP: %{http_code}\n" http://127.0.0.1:8000/mcp/

# Wrong token → 401
curl -s -o - -w "\nHTTP: %{http_code}\n" http://127.0.0.1:8000/mcp/ \
  -H "Authorization: Bearer wrong-token"

# Valid token → 200
python -c "
import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:8000/mcp/',
    method='POST',
    headers={
        'Authorization': 'Bearer my-secret-token',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
    },
    data=json.dumps({'jsonrpc':'2.0','method':'initialize','params':{'protocolVersion':'2024-11-05','clientInfo':{'name':'test','version':'1.0'},'capabilities':{}},'id':1}).encode()
)
with urllib.request.urlopen(req) as r:
    print('HTTP:', r.status)
    print(r.read().decode())
"
```

---

## Bonus: Shared Adapter Interface

`BaseAdapter` is an abstract base class that both `SQLiteAdapter` and `PostgreSQLAdapter` implement:

```python
from base_adapter import BaseAdapter
from db import SQLiteAdapter
from postgres_adapter import PostgreSQLAdapter

# Both share the same interface
adapter: BaseAdapter = SQLiteAdapter()           # SQLite
# adapter: BaseAdapter = PostgreSQLAdapter()    # PostgreSQL (needs DATABASE_URL)
```

To use PostgreSQL:
```bash
pip install psycopg[binary]
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

---

## Bonus: Pagination

```python
# Page 1
search(table="students", limit=3, offset=0)

# Page 2
search(table="students", limit=3, offset=3)

# Page 3
search(table="students", limit=3, offset=6)
```

---

## Data Model

```sql
students(id, name, cohort, score, created_at)
courses(id, title, credits)
enrollments(id, student_id, course_id, grade)
```

Seed data: 10 students, 5 courses, 15 enrollments.

---

## References

- [FastMCP Quickstart](https://gofastmcp.com/v2/getting-started/quickstart)
- [FastMCP Resources](https://gofastmcp.com/v2/servers/resources)
- [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
- [Model Context Protocol](https://modelcontextprotocol.io)
