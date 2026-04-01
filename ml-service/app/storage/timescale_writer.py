from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_batch

from app.config import Settings


@dataclass
class PredictionRecord:
    time: datetime
    org_id: str
    api_id: str
    endpoint: str
    method: str
    risk_score: float
    prediction: str
    confidence: float
    top_features: list[dict[str, Any]]
    model_version: str = "1.0"
    feature_schema_version: str = "1.0"
    model_hash: str = ""
    is_warmed_up: bool = False


class TimescaleWriter:
    def __init__(self, settings: Settings) -> None:
        self._conn = psycopg2.connect(settings.timescale_database)
        self._conn.autocommit = False
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS api_failure_predictions (
                    time TIMESTAMPTZ NOT NULL,
                    org_id UUID NOT NULL,
                    api_id UUID NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL DEFAULT 'GET',
                    risk_score DOUBLE PRECISION NOT NULL,
                    prediction TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    top_features JSONB NOT NULL DEFAULT '[]'::jsonb,
                    model_version TEXT NOT NULL DEFAULT '1.0',
                    feature_schema_version TEXT NOT NULL DEFAULT '1.0',
                    model_hash TEXT DEFAULT '',
                    is_warmed_up BOOLEAN DEFAULT false
                );
                """
            )
            cursor.execute(
                """
                SELECT create_hypertable(
                    'api_failure_predictions',
                    'time',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
                """
            )
            
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_api_failure_predictions_idempotent
                ON api_failure_predictions (org_id, api_id, endpoint, method, time_bucket('1 minute', time));
                """
            )
            
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_api_failure_predictions_lookup
                ON api_failure_predictions (org_id, api_id, endpoint, time DESC);
                """
            )
        self._conn.commit()

    def _bucket_time(self, ts: datetime) -> datetime:
        """Bucket timestamp to nearest minute for idempotency."""
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        # Truncate to minute boundary
        return ts.replace(second=0, microsecond=0)


    def write_predictions(self, records: list[PredictionRecord]) -> None:
        if not records:
            return

        with self._conn.cursor() as cursor:
            # Use UPSERT with ON CONFLICT to ensure idempotency
            # Conflict key is (org_id, api_id, endpoint, method, time_bucket)
            execute_batch(
                cursor,
                """
                INSERT INTO api_failure_predictions (
                    time,
                    org_id,
                    api_id,
                    endpoint,
                    method,
                    risk_score,
                    prediction,
                    confidence,
                    top_features,
                    model_version,
                    feature_schema_version,
                    model_hash,
                    is_warmed_up
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (org_id, api_id, endpoint, method, time_bucket('1 minute', time))
                DO UPDATE SET
                    risk_score = GREATEST(EXCLUDED.risk_score, api_failure_predictions.risk_score),
                    prediction = EXCLUDED.prediction,
                    confidence = EXCLUDED.confidence,
                    top_features = EXCLUDED.top_features,
                    model_version = EXCLUDED.model_version,
                    feature_schema_version = EXCLUDED.feature_schema_version,
                    model_hash = EXCLUDED.model_hash,
                    is_warmed_up = EXCLUDED.is_warmed_up;
                """,
                [
                    (
                        self._bucket_time(record.time),
                        record.org_id,
                        record.api_id,
                        record.endpoint,
                        record.method,
                        record.risk_score,
                        record.prediction,
                        record.confidence,
                        Json(record.top_features),
                        record.model_version,
                        record.feature_schema_version,
                        record.model_hash,
                        record.is_warmed_up,
                    )
                    for record in records
                ],
                page_size=500,
            )
        self._conn.commit()


    def close(self) -> None:
        self._conn.close()
