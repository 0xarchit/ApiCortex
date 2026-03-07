from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    risk_score: float
    prediction: str
    confidence: float
    top_features: list[dict[str, Any]]


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
                    risk_score DOUBLE PRECISION NOT NULL,
                    prediction TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    top_features JSONB NOT NULL DEFAULT '[]'::jsonb
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
                CREATE INDEX IF NOT EXISTS idx_api_failure_predictions_lookup
                ON api_failure_predictions (org_id, api_id, endpoint, time DESC);
                """
            )
        self._conn.commit()

    def write_predictions(self, records: list[PredictionRecord]) -> None:
        if not records:
            return

        with self._conn.cursor() as cursor:
            execute_batch(
                cursor,
                """
                INSERT INTO api_failure_predictions (
                    time,
                    org_id,
                    api_id,
                    endpoint,
                    risk_score,
                    prediction,
                    confidence,
                    top_features
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                [
                    (
                        record.time,
                        record.org_id,
                        record.api_id,
                        record.endpoint,
                        record.risk_score,
                        record.prediction,
                        record.confidence,
                        Json(record.top_features),
                    )
                    for record in records
                ],
                page_size=500,
            )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
