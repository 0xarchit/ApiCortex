"""
Feature engineering for API failure prediction.

Maintains rolling windows of telemetry events per endpoint, computing
time-series features (latency, error rate, traffic, schema changes) for
model inference. Handles late/out-of-order events and warm-up tracking.
"""
from __future__ import annotations

import json
import logging
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Deque, Any

import numpy as np

from app.schemas.telemetry_event import TelemetryEvent


WINDOW_1M = timedelta(minutes=1)
WINDOW_5M = timedelta(minutes=5)
WINDOW_15M = timedelta(minutes=15)
FEATURE_HISTORY_LIMIT = 180

# Lateness threshold: events older than this are considered late/stale
LATENESS_THRESHOLD = timedelta(minutes=30)

# Minimum number of events required for stable feature computation
MIN_EVENTS_FOR_WARMUP = 100

FEATURE_COLUMNS = [
    "p50_latency",
    "p90_latency",
    "p95_latency",
    "latency_variance",
    "latency_delta",
    "error_rate",
    "error_rate_delta",
    "traffic_rps",
    "traffic_delta",
    "schema_fields_added",
    "schema_fields_removed",
    "schema_breaking_changes",
    "schema_entropy",
    "schema_entropy_delta",
    "recent_deploy",
    "p95_latency_roll_mean_15",
    "latency_variance_roll_std_15",
    "error_rate_roll_mean_15",
    "error_rate_acceleration",
    "traffic_utilization_proxy",
    "p95_to_p50_ratio",
    "latency_p95_zscore",
    "error_rate_ewm",
    "p95_latency_roll_max_15",
    "error_high_streak",
]

LEGACY_FEATURE_ALIASES = {
    "latency_mean": "p50_latency",
    "latency_p95": "p95_latency",
}


@dataclass(frozen=True)
class EventKey:
    """Unique identifier for an API endpoint (org + api + path + method)."""
    org_id: str
    api_id: str
    endpoint: str
    method: str


@dataclass(frozen=True)
class EventSnapshot:
    """Single raw telemetry event snapshot for feature computation."""
    timestamp: datetime
    status: int
    latency_ms: int
    schema_hash: str | None


@dataclass(frozen=True)
class FeatureSnapshot:
    """
    Snapshot of computed features for an endpoint at a specific time.

    Attributes:
        timestamp: When features were computed (latest event time).
        p50_latency, p90_latency, p95_latency: Latency percentiles.
        latency_variance: Variance of latencies.
        error_rate: Proportion of 5xx responses.
        traffic_rps: Requests per second.
        schema_entropy: Entropy of schema hash values.
    """
    timestamp: datetime
    p50_latency: float
    p90_latency: float
    p95_latency: float
    latency_variance: float
    error_rate: float
    traffic_rps: float
    schema_entropy: float


@dataclass
class FeatureRow:
    """
    Computed features for one endpoint at a point in time.

    Attributes:
        time: Timestamp when features were computed (latest event time).
        org_id, api_id, endpoint, method: Endpoint identifier.
        features: Dict mapping feature names to float values.
        is_warmed_up: Whether endpoint has sufficient history for predictions.
    """
    time: datetime
    org_id: str
    api_id: str
    endpoint: str
    method: str
    features: dict[str, float]
    is_warmed_up: bool = False


class RollingFeatureEngineer:
    """
    Maintains per-endpoint rolling state and computes model features with warm-up tracking.

    Accumulates telemetry events in sliding windows, tracks late/out-of-order
    events, and computes time-series features for each endpoint. Monitors
    when endpoints have enough history (MIN_EVENTS_FOR_WARMUP) for stable
    predictions.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._history: dict[EventKey, Deque[EventSnapshot]] = defaultdict(deque)
        self._feature_history: dict[EventKey, Deque[FeatureSnapshot]] = defaultdict(
            lambda: deque(maxlen=FEATURE_HISTORY_LIMIT)
        )
        self._event_counts: dict[EventKey, int] = defaultdict(int)
        self._is_warmed_up: dict[EventKey, bool] = {}
        self._logger = logger or logging.getLogger(__name__)
        self._total_events_processed = 0
        self._late_events_dropped = 0
        self._out_of_order_events = 0
        self._max_event_time_seen: dict[EventKey, datetime] = {}

    def is_endpoint_warmed_up(self, key: EventKey) -> bool:
        """Check if an endpoint has sufficient history for stable predictions."""
        return self._is_warmed_up.get(key, False)

    def get_event_skew_metrics(self) -> dict[str, Any]:
        """Get metrics on event timing anomalies."""
        return {
            "late_events_dropped": self._late_events_dropped,
            "out_of_order_events": self._out_of_order_events,
            "total_events_processed": self._total_events_processed,
        }

    def _is_event_too_late(self, event_time: datetime, key: EventKey, now: datetime) -> bool:
        """Check if event is too far in the past (older than lateness threshold)."""
        age = now - event_time
        return age > LATENESS_THRESHOLD

    def _is_event_out_of_order(self, event_time: datetime, key: EventKey) -> bool:
        """Check if event timestamp is before the maximum timestamp seen for this key."""
        max_time = self._max_event_time_seen.get(key)
        if max_time is None:
            return False
        return event_time < max_time

    def bootstrap_from_state(self, state: dict[str, Any]) -> None:
        """
        Restore rolling history from persisted checkpoint state.

        Useful after restarts to continue using accumulated history rather
        than starting cold. Logs if restoration encounters errors.

        Args:
            state: Dict exported by export_state() method.
        """
        try:
            for key_dict, events_data in state.get("history", {}).items():
                key = EventKey(**json.loads(key_dict))
                queue: Deque[EventSnapshot] = deque()
                for event_dict in events_data:
                    event_dict["timestamp"] = datetime.fromisoformat(event_dict["timestamp"])
                    snapshot = EventSnapshot(**event_dict)
                    queue.append(snapshot)
                self._history[key] = queue

            for key_dict, features_data in state.get("feature_history", {}).items():
                key = EventKey(**json.loads(key_dict))
                queue: Deque[FeatureSnapshot] = deque(maxlen=FEATURE_HISTORY_LIMIT)
                for feature_dict in features_data:
                    feature_dict["timestamp"] = datetime.fromisoformat(feature_dict["timestamp"])
                    snapshot = FeatureSnapshot(**feature_dict)
                    queue.append(snapshot)
                self._feature_history[key] = queue
            
            self._event_counts = defaultdict(int, {
                EventKey(**json.loads(k)): v 
                for k, v in state.get("event_counts", {}).items()
            })
            self._is_warmed_up = {
                EventKey(**json.loads(k)): v 
                for k, v in state.get("is_warmed_up", {}).items()
            }
            
            self._max_event_time_seen = {
                EventKey(**json.loads(k)): datetime.fromisoformat(v)
                for k, v in state.get("max_event_time_seen", {}).items()
            }
            
            self._total_events_processed = state.get("total_events_processed", 0)
            self._late_events_dropped = state.get("late_events_dropped", 0)
            self._out_of_order_events = state.get("out_of_order_events", 0)
            
            self._logger.info("Loaded feature state from bootstrap", extra={
                "extra": {
                    "keys_restored": len(self._history),
                    "feature_keys_restored": len(self._feature_history),
                    "total_events": self._total_events_processed,
                    "late_events_dropped": self._late_events_dropped,
                    "out_of_order_events": self._out_of_order_events,
                }
            })
        except Exception as exc:
            self._logger.warning("Failed to bootstrap feature state", extra={
                "extra": {"error": str(exc)}
            })

    def export_state(self) -> dict[str, Any]:
        """
        Serialize rolling history and metrics for persistence across restarts.

        Returns:
            Dict with history, event_counts, warm-up flags, and timing metrics.
        """
        return {
            "history": {
                json.dumps({"org_id": k.org_id, "api_id": k.api_id, "endpoint": k.endpoint, "method": k.method}): [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "status": e.status,
                        "latency_ms": e.latency_ms,
                        "schema_hash": e.schema_hash
                    }
                    for e in self._history[k]
                ]
                for k in self._history.keys()
            },
            "feature_history": {
                json.dumps({"org_id": k.org_id, "api_id": k.api_id, "endpoint": k.endpoint, "method": k.method}): [
                    {
                        "timestamp": f.timestamp.isoformat(),
                        "p50_latency": f.p50_latency,
                        "p90_latency": f.p90_latency,
                        "p95_latency": f.p95_latency,
                        "latency_variance": f.latency_variance,
                        "error_rate": f.error_rate,
                        "traffic_rps": f.traffic_rps,
                        "schema_entropy": f.schema_entropy,
                    }
                    for f in self._feature_history[k]
                ]
                for k in self._feature_history.keys()
            },
            "event_counts": {
                json.dumps({"org_id": k.org_id, "api_id": k.api_id, "endpoint": k.endpoint, "method": k.method}): v
                for k, v in self._event_counts.items()
            },
            "is_warmed_up": {
                json.dumps({"org_id": k.org_id, "api_id": k.api_id, "endpoint": k.endpoint, "method": k.method}): v
                for k, v in self._is_warmed_up.items()
            },
            "max_event_time_seen": {
                json.dumps({"org_id": k.org_id, "api_id": k.api_id, "endpoint": k.endpoint, "method": k.method}): v.isoformat()
                for k, v in self._max_event_time_seen.items()
            },
            "total_events_processed": self._total_events_processed,
            "late_events_dropped": self._late_events_dropped,
            "out_of_order_events": self._out_of_order_events,
        }


    def ingest(self, events: list[TelemetryEvent]) -> list[FeatureRow]:
        """
        Process batch of telemetry events and compute features for all touched endpoints.

        Handles late/out-of-order event filtering, maintains rolling windows,
        updates warm-up status, and computes feature vectors. Returns one
        FeatureRow per endpoint that received new events.

        Args:
            events: List of validated TelemetryEvent objects to ingest.

        Returns:
            List of FeatureRow objects (one per unique endpoint in batch).
        """
        if not events:
            return []

        touched_keys: set[EventKey] = set()
        now = datetime.now(UTC)

        for event in sorted(events, key=lambda e: e.timestamp):
            key = EventKey(
                org_id=event.org_id,
                api_id=event.api_id,
                endpoint=event.endpoint,
                method=event.method,
            )
            event_time = event.timestamp.astimezone(UTC)

            if self._is_event_too_late(event_time, key, now):
                self._late_events_dropped += 1
                self._logger.debug(
                    "Dropping late event (outside lateness threshold)",
                    extra={"extra": {
                        "event_age_minutes": (now - event_time).total_seconds() / 60,
                        "threshold_minutes": LATENESS_THRESHOLD.total_seconds() / 60,
                        "endpoint": key.endpoint,
                    }}
                )
                continue

            if self._is_event_out_of_order(event_time, key):
                self._out_of_order_events += 1
                self._logger.debug(
                    "Processing out-of-order event",
                    extra={"extra": {
                        "event_time": event_time.isoformat(),
                        "max_time_seen": self._max_event_time_seen[key].isoformat() if key in self._max_event_time_seen else None,
                        "endpoint": key.endpoint,
                    }}
                )

            if key not in self._max_event_time_seen or event_time > self._max_event_time_seen[key]:
                self._max_event_time_seen[key] = event_time

            snapshot = EventSnapshot(
                timestamp=event_time,
                status=event.status,
                latency_ms=event.latency_ms,
                schema_hash=event.schema_hash,
            )
            self._history[key].append(snapshot)
            self._event_counts[key] += 1
            self._total_events_processed += 1
            touched_keys.add(key)
            self._prune_old(key, event_time)
            
            if not self._is_warmed_up.get(key, False):
                if self._event_counts[key] >= MIN_EVENTS_FOR_WARMUP:
                    self._is_warmed_up[key] = True
                    self._logger.info(
                        "Endpoint warmed up",
                        extra={"extra": {
                            "org_id": key.org_id,
                            "api_id": key.api_id,
                            "endpoint": key.endpoint,
                            "method": key.method,
                            "total_events": self._event_counts[key]
                        }}
                    )

        rows: list[FeatureRow] = []
        for key in touched_keys:
            latest_ts = self._history[key][-1].timestamp
            features = self._compute_features(key, latest_ts)
            self._feature_history[key].append(
                FeatureSnapshot(
                    timestamp=latest_ts,
                    p50_latency=features["p50_latency"],
                    p90_latency=features["p90_latency"],
                    p95_latency=features["p95_latency"],
                    latency_variance=features["latency_variance"],
                    error_rate=features["error_rate"],
                    traffic_rps=features["traffic_rps"],
                    schema_entropy=features["schema_entropy"],
                )
            )
            rows.append(
                FeatureRow(
                    time=latest_ts,
                    org_id=key.org_id,
                    api_id=key.api_id,
                    endpoint=key.endpoint,
                    method=key.method,
                    features=features,
                    is_warmed_up=self._is_warmed_up.get(key, False),
                )
            )
        return rows

    def _prune_old(self, key: EventKey, now: datetime) -> None:
        """Remove events older than 15-minute window to manage memory."""
        cutoff = now - WINDOW_15M
        queue = self._history[key]
        while queue and queue[0].timestamp < cutoff:
            queue.popleft()

    def _events_in_window(self, key: EventKey, now: datetime, window: timedelta) -> list[EventSnapshot]:
        """Get events within sliding window relative to 'now' timestamp."""
        cutoff = now - window
        return [event for event in self._history[key] if event.timestamp >= cutoff]

    def _compute_features(self, key: EventKey, now: datetime) -> dict[str, float]:
        """
        Compute time-series features from endpoint's rolling event history.

        Features include: latency percentiles/variance/delta, error rate/delta,
        traffic rate/delta, and schema change indicators. Handles missing data
        by replacing inf/nan with 0.0.

        Args:
            key: Endpoint identifier.
            now: Reference timestamp for window calculations.

        Returns:
            Dict mapping feature names to float values.
        """
        events_1m = self._events_in_window(key, now, WINDOW_1M)
        events_5m = self._events_in_window(key, now, WINDOW_5M)
        events_15m = self._events_in_window(key, now, WINDOW_15M)
        historical = list(self._feature_history[key])

        latencies_1m = [float(e.latency_ms) for e in events_1m]
        latencies_5m = [float(e.latency_ms) for e in events_5m]

        p50_latency = float(np.percentile(latencies_1m, 50)) if latencies_1m else 0.0
        p90_latency = float(np.percentile(latencies_1m, 90)) if latencies_1m else 0.0
        p95_latency = float(np.percentile(latencies_1m, 95)) if latencies_1m else 0.0
        latency_variance = float(np.var(latencies_1m)) if len(latencies_1m) > 1 else 0.0

        latency_5m_mean = mean(latencies_5m) if latencies_5m else p50_latency
        latency_delta = p50_latency - latency_5m_mean

        error_rate_1m = self._error_rate(events_1m)
        error_rate_5m = self._error_rate(events_5m)
        error_rate_delta = error_rate_1m - error_rate_5m

        traffic_rps_1m = len(events_1m) / 60.0
        traffic_rps_5m = len(events_5m) / 300.0
        traffic_delta = traffic_rps_1m - traffic_rps_5m

        schema_fields_added, schema_fields_removed, schema_breaking_changes = self._schema_change_features(events_15m)
        schema_entropy = self._schema_entropy(events_15m)
        schema_entropy_delta = schema_entropy - historical[-1].schema_entropy if historical else 0.0
        recent_deploy = 1.0 if schema_fields_added > 0.0 else 0.0

        recent_p95 = [snapshot.p95_latency for snapshot in historical[-15:]]
        recent_variance = [snapshot.latency_variance for snapshot in historical[-15:]]
        recent_error_rate = [snapshot.error_rate for snapshot in historical[-15:]]
        recent_traffic = [snapshot.traffic_rps for snapshot in historical[-10:]]
        recent_p95_for_z = [snapshot.p95_latency for snapshot in historical[-30:]]

        p95_latency_roll_mean_15 = mean(recent_p95) if recent_p95 else p95_latency
        latency_variance_roll_std_15 = float(np.std(recent_variance)) if len(recent_variance) > 1 else 0.0
        error_rate_roll_mean_15 = mean(recent_error_rate) if recent_error_rate else error_rate_1m

        if len(historical) >= 3:
            d1 = historical[-1].error_rate - historical[-2].error_rate
            d0 = historical[-2].error_rate - historical[-3].error_rate
            error_rate_acceleration = d1 - d0
        else:
            error_rate_acceleration = 0.0

        traffic_utilization_proxy = (mean(recent_traffic) if recent_traffic else traffic_rps_1m) / 2000.0
        p95_to_p50_ratio = p95_latency / max(p50_latency, 1.0)

        if len(recent_p95_for_z) > 1:
            z_mean = mean(recent_p95_for_z)
            z_std = float(np.std(recent_p95_for_z))
            latency_p95_zscore = (recent_p95_for_z[-1] - z_mean) / z_std if z_std > 0.0 else 0.0
        else:
            latency_p95_zscore = 0.0

        error_rate_ewm = self._ewm([snapshot.error_rate for snapshot in historical], alpha=0.3)
        p95_latency_roll_max_15 = max(recent_p95) if recent_p95 else p95_latency
        error_high_streak = self._error_high_streak([snapshot.error_rate for snapshot in historical])

        features = {
            "p50_latency": p50_latency,
            "p90_latency": p90_latency,
            "p95_latency": p95_latency,
            "latency_variance": latency_variance,
            "latency_delta": latency_delta,
            "error_rate": error_rate_1m,
            "error_rate_delta": error_rate_delta,
            "traffic_rps": traffic_rps_1m,
            "traffic_delta": traffic_delta,
            "schema_fields_added": schema_fields_added,
            "schema_fields_removed": schema_fields_removed,
            "schema_breaking_changes": schema_breaking_changes,
            "schema_entropy": schema_entropy,
            "schema_entropy_delta": schema_entropy_delta,
            "recent_deploy": recent_deploy,
            "p95_latency_roll_mean_15": p95_latency_roll_mean_15,
            "latency_variance_roll_std_15": latency_variance_roll_std_15,
            "error_rate_roll_mean_15": error_rate_roll_mean_15,
            "error_rate_acceleration": error_rate_acceleration,
            "traffic_utilization_proxy": traffic_utilization_proxy,
            "p95_to_p50_ratio": p95_to_p50_ratio,
            "latency_p95_zscore": latency_p95_zscore,
            "error_rate_ewm": error_rate_ewm,
            "p95_latency_roll_max_15": p95_latency_roll_max_15,
            "error_high_streak": error_high_streak,
        }

        for alias, base_name in LEGACY_FEATURE_ALIASES.items():
            features[alias] = features.get(base_name, 0.0)

        return {
            name: float(np.nan_to_num(value, nan=0.0, posinf=0.0, neginf=0.0))
            for name, value in features.items()
        }

    @staticmethod
    def _error_rate(events: list[EventSnapshot]) -> float:
        """
        Calculate error rate as proportion of 5xx responses.

        Args:
            events: List of event snapshots.

        Returns:
            Error rate in [0.0, 1.0] or 0.0 if no events.
        """
        if not events:
            return 0.0
        error_count = sum(1 for event in events if event.status >= 500)
        return error_count / float(len(events))

    @staticmethod
    def _schema_change_features(events: list[EventSnapshot]) -> tuple[float, float, float]:
        """
        Detect schema changes (hash changes) and breaking changes (hash change + error).

        Returns:
            Tuple of (fields_added, fields_removed, breaking_changes).
        """
        if len(events) < 2:
            return 0.0, 0.0, 0.0

        changes = 0
        breaking = 0
        previous_hash = events[0].schema_hash

        for event in events[1:]:
            if previous_hash and event.schema_hash and previous_hash != event.schema_hash:
                changes += 1
                if event.status >= 500:
                    breaking = 1
            previous_hash = event.schema_hash

        fields_added = float(changes)
        fields_removed = float(max(0, changes - 1))
        return fields_added, fields_removed, float(breaking)

    @staticmethod
    def _schema_entropy(events: list[EventSnapshot]) -> float:
        """Compute entropy of schema hash values in event window."""
        hashes = [event.schema_hash for event in events if event.schema_hash]
        if not hashes:
            return 0.0
        counts: dict[str, int] = {}
        for value in hashes:
            counts[value] = counts.get(value, 0) + 1
        total = float(len(hashes))
        entropy = 0.0
        for count in counts.values():
            p = count / total
            entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def _ewm(values: list[float], alpha: float) -> float:
        """Exponentially weighted moving average for smoothing time series."""
        if not values:
            return 0.0
        value = values[0]
        for item in values[1:]:
            value = alpha * item + (1.0 - alpha) * value
        return float(value)

    @staticmethod
    def _error_high_streak(values: list[float]) -> float:
        """Count of recent error rates above 80th percentile (last 10 points)."""
        if len(values) < 3:
            return 0.0
        threshold = float(np.quantile(values, 0.8))
        recent = values[-10:]
        return float(sum(1.0 for value in recent if value > threshold))
