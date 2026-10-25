# MCP + Semantic Layer + MySQL demo

A compact teaching example of this flow:

LLM/host -> MCP client -> MCP server -> semantic layer -> query compiler
-> SQLAlchemy -> MySQL -> structured results.

## Requirements

- Python 3.11+
- MySQL 8.x (or a compatible MySQL server)
- A dedicated read-only MySQL account for the API
- An MCP-compatible host/client

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your MySQL connection and demo tenant IDs. The checked-in
`.env.example` contains placeholders; use a dedicated read-only database account.
Create the table:

```bash
mysql -u root -p < schema.sql
```

For a quick local test, insert a few rows:

```sql
USE observability;
INSERT INTO api_events (tenant_id, event_time, status_code, service_name) VALUES
('tenant-a', '2026-10-02 10:00:00', 200, 'portal'),
('tenant-a', '2026-10-02 10:01:00', 503, 'portal'),
('tenant-b', '2026-10-03 11:00:00', 500, 'ingestion'),
('tenant-b', '2026-10-03 11:02:00', 200, 'ingestion');
```

Run the server in terminal 1:

```bash
python server.py
```

Run the client in terminal 2:

```bash
python client.py
```

## Where each responsibility lives

- `server.py`: MCP tools and database engine lifecycle.
- `semantic_layer.py`: allowlisted business metrics, dimensions, SQL compiler and execution.
- `client.py`: MCP protocol connection, tool discovery and invocation.
- `schema.sql`: one-table schema and example indexes.

## How the dynamic query works

The caller sends structured business intent, not SQL. `semantic_layer.py` maps only approved metric/dimension keys to SQL fragments, binds time and tenant values as parameters, and applies a row limit. It does not accept arbitrary table names, column names, SQL snippets, or caller-provided tenant IDs.

## Important production hardening

This is a learning starter, not a complete production deployment.

1. **Authentication:** protect Streamable HTTP with your organization's identity provider and TLS. The sample binds to localhost by default.
2. **Authorization:** replace `ALLOWED_TENANT_IDS` with tenant scope derived from the authenticated principal on every request. Never trust tenant IDs supplied by the LLM.
3. **Database privileges:** use a dedicated SELECT-only MySQL account; do not use an administrator account.
4. **Query controls:** add per-user rate limits, query timeout enforcement, auditing, concurrency limits and maximum time-window rules.
5. **Indexes:** validate actual access patterns with `EXPLAIN ANALYZE` on representative data. The sample has two candidate composite indexes; keep only indexes justified by measured plans and write overhead.
6. **Large datasets:** index time and tenant filters, select only required columns, aggregate in MySQL, and return bounded result sets. Consider time partitioning or pre-aggregated rollup tables only after measuring query plans and operational needs.
7. **MCP SDK:** this sample targets the MCP Python SDK v1 maintenance line (`mcp>=1.28,<2`) to keep its API stable for this tutorial. Check the SDK's current docs before upgrading to v2.
8. **LLM integration:** `client.py` calls a tool directly to demonstrate the protocol. In a real agent host, provide the discovered MCP tools to your model, let the model choose a tool call, validate the arguments, execute it, then send the result back to the model for summarization.

## Expected behavior

For the sample rows, `error_rate` is calculated as the count of rows with `status_code >= 500` divided by all rows in each group. It is returned as a ratio (for example, `0.5` means 50%).
