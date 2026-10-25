"""Small semantic layer + SQL compiler. Only allowlisted fields/metrics can be queried."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

# SQL fragments below are developer-owned constants, never LLM-provided strings.
DIMENSIONS = {
    "tenant_id": "tenant_id",
    "service_name": "service_name",
}

METRICS = {
    "request_count": "COUNT(*)",
    "error_count": "SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END)",
    "error_rate": (
        "SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) "
        "/ NULLIF(COUNT(*), 0)"
    ),
}

@dataclass
class QueryPlan:
    sql: str
    params: dict[str, Any]
    explanation: dict[str, Any]

def compile_metrics_query(
    *,
    metrics: list[str],
    dimensions: list[str],
    start_time: datetime,
    end_time: datetime,
    authorized_tenant_ids: list[str],
    limit: int = 10,
) -> QueryPlan:
    """Compile a structured request into parameterized SQL."""
    if not metrics:
        raise ValueError("At least one metric is required.")
    if not dimensions:
        raise ValueError("At least one dimension is required.")
    if start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time.")
    if not authorized_tenant_ids:
        raise PermissionError("No authorized tenants in the current security context.")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100.")

    unknown_metrics = sorted(set(metrics) - set(METRICS))
    unknown_dimensions = sorted(set(dimensions) - set(DIMENSIONS))
    if unknown_metrics:
        raise ValueError(f"Unsupported metrics: {unknown_metrics}")
    if unknown_dimensions:
        raise ValueError(f"Unsupported dimensions: {unknown_dimensions}")

    # SQL identifiers and expressions are selected only from the registries above.
    select_parts = [f"{DIMENSIONS[d]} AS {d}" for d in dimensions]
    select_parts += [f"{METRICS[m]} AS {m}" for m in metrics]

    group_by = ", ".join(DIMENSIONS[d] for d in dimensions)
    order_metric = "error_rate" if "error_rate" in metrics else metrics[0]

    tenant_binds = ", ".join(f":tenant_{i}" for i in range(len(authorized_tenant_ids)))
    sql = f"""
        SELECT {", ".join(select_parts)}
        FROM api_events
        WHERE event_time >= :start_time
          AND event_time < :end_time
          AND tenant_id IN ({tenant_binds})
        GROUP BY {group_by}
        ORDER BY {order_metric} DESC
        LIMIT :row_limit
    """

    params: dict[str, Any] = {
        "start_time": start_time,
        "end_time": end_time,
        "row_limit": limit,
    }
    params.update({
        f"tenant_{i}": tenant_id
        for i, tenant_id in enumerate(authorized_tenant_ids)
    })

    return QueryPlan(
        sql=sql,
        params=params,
        explanation={
            "metrics": metrics,
            "dimensions": dimensions,
            "time_window": [start_time.isoformat(), end_time.isoformat()],
            "limit": limit,
        },
    )

def run_metrics_query(
    engine: Engine,
    *,
    metrics: list[str],
    dimensions: list[str],
    start_time: datetime,
    end_time: datetime,
    authorized_tenant_ids: list[str],
    limit: int = 10,
) -> dict[str, Any]:
    plan = compile_metrics_query(
        metrics=metrics,
        dimensions=dimensions,
        start_time=start_time,
        end_time=end_time,
        authorized_tenant_ids=authorized_tenant_ids,
        limit=limit,
    )
    # Bound parameters keep values separate from SQL text.
    with engine.connect() as conn:
        rows = conn.execute(text(plan.sql), plan.params).mappings().all()

    return {
        "columns": dimensions + metrics,
        "row_count": len(rows),
        "rows": [dict(row) for row in rows],
        "query_plan": plan.explanation,
    }
