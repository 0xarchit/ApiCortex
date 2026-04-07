from pydantic import BaseModel
from typing import Any

class TelemetryEndpointStatsOut(BaseModel):
    endpoint: str
    method: str
    request_count: int
    error_rate: float
    p95_latency_ms: float
