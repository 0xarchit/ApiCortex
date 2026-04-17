"""Response schemas for telemetry and metrics endpoints."""
from pydantic import BaseModel
from typing import Any

class TelemetryEndpointStatsOut(BaseModel):
    """Response schema for endpoint statistics and metrics."""
    endpoint: str
    method: str
    request_count: int
    error_rate: float
    p95_latency_ms: float
