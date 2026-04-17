"""Telemetry and metrics endpoints.

Provides endpoint statistics, request counts, latency metrics, and
error rates from time-series data.
"""
import uuid

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.schemas.telemetry import TelemetryEndpointStatsOut
from app.services.dashboard_service import timescale_engine

router = APIRouter()

@router.get("/endpoints", response_model=list[TelemetryEndpointStatsOut])
def get_telemetry_endpoints(request: Request, window_hours: int = 24):
    org_id = uuid.UUID(str(request.state.org_id))
    window_hours = max(1, min(window_hours, 168))

    query = text(
        """
        SELECT
            endpoint,
            method,
            COUNT(*) as request_count,
            AVG(CASE WHEN status >= 500 THEN 1.0 ELSE 0.0 END) as error_rate,
            COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms), 0) as p95_latency_ms
        FROM api_telemetry
        WHERE org_id = :org_id
          AND time >= now() - make_interval(hours => :window_hours)
        GROUP BY endpoint, method
        ORDER BY request_count DESC
        """
    )
    with timescale_engine.connect() as conn:
        rows = conn.execute(query, {"org_id": str(org_id), "window_hours": window_hours}).mappings().all()

    return [
        TelemetryEndpointStatsOut(
            endpoint=row["endpoint"],
            method=row["method"],
            request_count=int(row["request_count"]),
            error_rate=float(row["error_rate"]),
            p95_latency_ms=float(row["p95_latency_ms"]),
        )
        for row in rows
    ]
