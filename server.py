"""MCP server exposing a governed business-metrics tool."""
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from mcp.server.fastmcp import FastMCP

from semantic_layer import run_metrics_query

load_dotenv()

database_url = os.environ["DATABASE_URL"]
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    pool_timeout=10,
    connect_args={"connect_timeout": 5},
)

# DEMO ONLY: static scope for a local tutorial. Production should resolve the
# authenticated principal and its tenant/role permissions for each request.
AUTHORIZED_TENANTS = [
    item.strip()
    for item in os.getenv("ALLOWED_TENANT_IDS", "").split(",")
    if item.strip()
]

mcp = FastMCP("Governed MySQL Metrics", json_response=True)

@mcp.tool()
def list_available_metrics() -> dict:
    """List business metrics and dimensions supported by the governed query API."""
    return {
        "metrics": {
            "request_count": "Number of API event rows",
            "error_count": "Rows where status_code >= 500",
            "error_rate": "Error rows divided by all rows, between 0 and 1",
        },
        "dimensions": ["tenant_id", "service_name"],
        "notes": [
            "Time range is required for every query.",
            "Only allowlisted metrics and dimensions are supported.",
            "Tenant scope comes from server configuration in this demo.",
        ],
    }

@mcp.tool()
def query_metrics(
    metrics: list[str],
    dimensions: list[str],
    start_time: str,
    end_time: str,
    limit: int = 10,
) -> dict:
    """Query governed API-event metrics for an ISO-8601 time window.

    Example times: 2026-10-01T00:00:00 and 2026-11-01T00:00:00.
    The end time is exclusive. Supported metrics: request_count, error_count,
    error_rate. Supported dimensions: tenant_id, service_name.
    """
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        return run_metrics_query(
            engine,
            metrics=metrics,
            dimensions=dimensions,
            start_time=start_dt,
            end_time=end_dt,
            authorized_tenant_ids=AUTHORIZED_TENANTS,
            limit=limit,
        )
    except (ValueError, PermissionError) as exc:
        return {"error": str(exc), "type": type(exc).__name__}

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
