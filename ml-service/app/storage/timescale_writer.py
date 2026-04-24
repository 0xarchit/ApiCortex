"""
TimescaleDB writer for inference results.

Persists API failure predictions to a hypertable with idempotent upsert logic
based on 1-minute time buckets. Automatically creates schema and indexes on
first connection.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from psycopg2.extras import Json, execute_batch
from psycopg2.pool import ThreadedConnectionPool

from app.config import Settings
from app.schemas.telemetry_event import TelemetryEvent


@dataclass
class PredictionRecord:
    """
    Single API failure prediction to persist to database.

    Attributes:
        time: Timestamp of prediction.
        org_id, api_id, endpoint, method: Endpoint identifier (UUIDs/strings).
        risk_score: Failure probability [0.0, 1.0].
        prediction: Risk category (normal/degraded/high_failure_risk).
        confidence: Model confidence [0.5, 1.0].
        top_features: List of {feature: str, contribution: float, abs_contribution: float}.
        feature_values: Dict of all feature values used for prediction.
        model_version, feature_schema_version: Versions for auditing/migration.
        model_hash: Hash of model artifact.
        is_warmed_up: Whether endpoint had sufficient history for this prediction.
    """
    time: datetime
    org_id: str
    api_id: str
    endpoint: str
    method: str
    risk_score: float
    prediction: str
    confidence: float
    top_features: list[dict[str, Any]]
    feature_values: dict[str, float]
    model_version: str = "1.0"
    feature_schema_version: str = "2.0"
    model_hash: str = ""
    is_warmed_up: bool = False


class TimescaleWriter:
    """
    Manages connection to TimescaleDB and writes API failure predictions.

    Creates hypertable on first instantiation with idempotent upsert logic
    based on (org_id, api_id, endpoint, method, time) conflict key.
    Buckets time to nearest minute to handle late/duplicate deliveries.
    """
    def __init__(self, settings: Settings) -> None:
        """
        Connect to TimescaleDB and ensure api_failure_predictions schema exists.

        Args:
            settings: Configuration with timescale_database connection string.
        """
        self._pool = ThreadedConnectionPool(
            minconn=settings.db_pool_min_connections,
            maxconn=settings.db_pool_max_connections,
            dsn=settings.timescale_database,
        )
        self._page_size = settings.db_write_page_size
        self._ensure_schema()

    def _get_conn(self):
        conn = self._pool.getconn()
        if conn.closed:
            self._pool.putconn(conn, close=True)
            conn = self._pool.getconn()
        conn.autocommit = False
        return conn

    def _put_conn(self, conn, close: bool = False) -> None:
        if conn is None:
            return
        should_close = close or bool(conn.closed)
        self._pool.putconn(conn, close=should_close)

    def _ensure_schema(self) -> None:
        """Create hypertable and indexes if they don't exist (idempotent operation)."""
        conn = self._get_conn()
        discard_conn = False
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS api_telemetry (
                        time TIMESTAMPTZ NOT NULL,
                        org_id UUID NOT NULL,
                        api_id UUID NOT NULL,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL,
                        status INTEGER NOT NULL,
                        latency_ms INTEGER NOT NULL,
                        request_size INTEGER NOT NULL DEFAULT 0,
                        response_size INTEGER NOT NULL DEFAULT 0,
                        schema_hash TEXT,
                        schema_version TEXT
                    );
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_telemetry
                    ADD COLUMN IF NOT EXISTS request_size INTEGER NOT NULL DEFAULT 0;
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_telemetry
                    ADD COLUMN IF NOT EXISTS response_size INTEGER NOT NULL DEFAULT 0;
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_telemetry
                    ADD COLUMN IF NOT EXISTS schema_hash TEXT;
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_telemetry
                    ADD COLUMN IF NOT EXISTS schema_version TEXT;
                    """
                )
                cursor.execute(
                    """
                    SELECT create_hypertable(
                        'api_telemetry',
                        'time',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_api_telemetry_org_time
                    ON api_telemetry (org_id, time DESC);
                    """
                )
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
                        feature_values JSONB NOT NULL DEFAULT '{}'::jsonb,
                        model_version TEXT NOT NULL DEFAULT '1.0',
                        feature_schema_version TEXT NOT NULL DEFAULT '2.0',
                        model_hash TEXT DEFAULT '',
                        is_warmed_up BOOLEAN DEFAULT false
                    );
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT 'GET';
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS top_features JSONB NOT NULL DEFAULT '[]'::jsonb;
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS feature_values JSONB NOT NULL DEFAULT '{}'::jsonb;
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS model_version TEXT NOT NULL DEFAULT '1.0';
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS feature_schema_version TEXT NOT NULL DEFAULT '2.0';
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS model_hash TEXT DEFAULT '';
                    """
                )
                cursor.execute(
                    """
                    ALTER TABLE api_failure_predictions
                    ADD COLUMN IF NOT EXISTS is_warmed_up BOOLEAN DEFAULT false;
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
                    DROP INDEX IF EXISTS idx_api_failure_predictions_idempotent;
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_api_failure_predictions_idempotent
                    ON api_failure_predictions (org_id, api_id, endpoint, method, time);
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_api_failure_predictions_lookup
                    ON api_failure_predictions (org_id, api_id, endpoint, time DESC);
                    """
                )
            conn.commit()
        except Exception:
            discard_conn = True
            if not conn.closed:
                conn.rollback()
            raise
        finally:
            self._put_conn(conn, close=discard_conn)

    @staticmethod
    def _bucket_time(ts: datetime) -> datetime:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts.replace(second=0, microsecond=0)

    def write_telemetry(self, events: list[TelemetryEvent]) -> None:
        if not events:
            return

        conn = self._get_conn()
        discard_conn = False
        try:
            with conn.cursor() as cursor:
                execute_batch(
                    cursor,
                    """
                    INSERT INTO api_telemetry (
                        time,
                        org_id,
                        api_id,
                        endpoint,
                        method,
                        status,
                        latency_ms,
                        request_size,
                        response_size,
                        schema_hash,
                        schema_version
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    [
                        (
                            event.timestamp,
                            event.org_id,
                            event.api_id,
                            event.endpoint,
                            event.method,
                            event.status,
                            event.latency_ms,
                            event.request_size_bytes,
                            event.response_size_bytes,
                            event.schema_hash,
                            event.schema_version,
                        )
                        for event in events
                    ],
                    page_size=self._page_size,
                )
            conn.commit()
        except Exception:
            discard_conn = True
            if not conn.closed:
                conn.rollback()
            raise
        finally:
            self._put_conn(conn, close=discard_conn)

    def write_predictions(self, records: list[PredictionRecord]) -> None:
        """
        Batch write predictions with idempotent upsert (handles duplicates gracefully).

        Uses ON CONFLICT with GREATEST() for risk_score to preserve highest risk
        if duplicate predictions arrive for same endpoint in same minute.

        Args:
            records: List of PredictionRecord objects to write (no-op if empty).
        """
        if not records:
            return

        conn = self._get_conn()
        discard_conn = False
        try:
            with conn.cursor() as cursor:
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
                        feature_values,
                        model_version,
                        feature_schema_version,
                        model_hash,
                        is_warmed_up
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (org_id, api_id, endpoint, method, time)
                    DO UPDATE SET
                        risk_score = GREATEST(EXCLUDED.risk_score, api_failure_predictions.risk_score),
                        prediction = EXCLUDED.prediction,
                        confidence = EXCLUDED.confidence,
                        top_features = EXCLUDED.top_features,
                        feature_values = EXCLUDED.feature_values,
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
                            Json(record.feature_values),
                            record.model_version,
                            record.feature_schema_version,
                            record.model_hash,
                            record.is_warmed_up,
                        )
                        for record in records
                    ],
                    page_size=self._page_size,
                )
            conn.commit()
        except Exception:
            discard_conn = True
            if not conn.closed:
                conn.rollback()
            raise
        finally:
            self._put_conn(conn, close=discard_conn)

    def close(self) -> None:
        """Close database connection pool."""
        self._pool.closeall()
