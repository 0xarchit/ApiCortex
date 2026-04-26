import gzip
import json
import logging
import threading
import time
import uuid
from typing import Any

from confluent_kafka import Consumer, KafkaError

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models.endpoint import Endpoint
from app.models.notification import Notification


class TelemetryTrackingSubscriber:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._logger = logging.getLogger("apicortex.telemetry-tracking-subscriber")
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._consumer: Consumer | None = None
        self._last_missing_topic_log_at = 0.0

    def start(self) -> None:
        if not self._settings.alert_subscriber_enabled:
            return

        config: dict[str, object] = {
            "bootstrap.servers": ",".join(self._settings.kafka_brokers),
            "group.id": self._settings.kafka_telemetry_tracking_group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }

        if self._settings.kafka_ca_cert and self._settings.kafka_service_cert and self._settings.kafka_service_key:
            config.update(
                {
                    "security.protocol": "ssl",
                    "ssl.ca.pem": self._settings.kafka_ca_cert,
                    "ssl.certificate.pem": self._settings.kafka_service_cert,
                    "ssl.key.pem": self._settings.kafka_service_key,
                }
            )

        self._consumer = Consumer(config)
        self._consumer.subscribe([self._settings.kafka_topic_raw])
        self._thread = threading.Thread(target=self._run, name="telemetry-tracking-subscriber", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._consumer:
            self._consumer.close()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self._consumer:
                return

            message = self._consumer.poll(self._settings.telemetry_poll_timeout_seconds)
            if message is None:
                continue

            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                unknown_topic_code = getattr(KafkaError, "UNKNOWN_TOPIC_OR_PART", None)
                if unknown_topic_code is not None and message.error().code() == unknown_topic_code:
                    now = time.monotonic()
                    if now - self._last_missing_topic_log_at >= 10:
                        self._logger.warning(
                            "Telemetry topic unavailable: %s. Waiting for topic to exist.",
                            self._settings.kafka_topic_raw,
                        )
                        self._last_missing_topic_log_at = now
                    continue
                self._logger.error("Telemetry topic consume error: %s", message.error())
                continue

            events = self._decode_events(message.value() or b"", message.headers() or [])
            if not events:
                self._consumer.commit(message=message, asynchronous=False)
                continue

            self._apply_tracking(events)
            self._consumer.commit(message=message, asynchronous=False)

    def _decode_events(self, payload: bytes, headers: list[tuple[str, bytes]]) -> list[dict[str, Any]]:
        header_map: dict[str, str] = {}
        if headers:
            for key, value in headers:
                lower = str(key).lower()
                if isinstance(value, (bytes, bytearray)):
                    header_map[lower] = value.decode("utf-8", errors="ignore")
                else:
                    header_map[lower] = str(value)

        encoding = header_map.get("content-encoding", "").lower()
        body = payload
        try:
            if encoding == "gzip" or payload[:2] == b"\x1f\x8b":
                body = gzip.decompress(payload)
            decoded = json.loads(body.decode("utf-8"))
        except Exception as exc:
            self._logger.error("Failed to decode telemetry payload: %s", exc)
            return []

        if isinstance(decoded, list):
            return [item for item in decoded if isinstance(item, dict)]
        if isinstance(decoded, dict):
            return [decoded]
        return []

    def _apply_tracking(self, events: list[dict[str, Any]]) -> None:
        db = SessionLocal()
        try:
            threshold = max(self._settings.tracking_error_pause_threshold, 1)
            for event in events:
                endpoint = self._match_endpoint(db, event)
                if endpoint is None:
                    continue

                status_raw = event.get("status")
                try:
                    status = int(status_raw)
                except (TypeError, ValueError):
                    continue

                is_failure = status == 404 or status >= 500
                if not is_failure:
                    if endpoint.consecutive_error_count != 0:
                        endpoint.consecutive_error_count = 0
                        if endpoint.monitoring_enabled:
                            endpoint.auto_paused = False
                        db.add(endpoint)
                    continue

                endpoint.consecutive_error_count = (endpoint.consecutive_error_count or 0) + 1
                if endpoint.monitoring_enabled and endpoint.consecutive_error_count >= threshold:
                    endpoint.monitoring_enabled = False
                    endpoint.auto_paused = True
                    db.add(
                        Notification(
                            org_id=endpoint.org_id,
                            title="Tracking paused automatically",
                            message=(
                                f"Tracking paused for {endpoint.method} {endpoint.path} after repeated polling failures "
                                f"(latest status {status})."
                            ),
                            severity="warning",
                            source="telemetry.poller",
                            extra_metadata={
                                "endpoint_id": str(endpoint.id),
                                "method": endpoint.method,
                                "path": endpoint.path,
                                "status": status,
                                "consecutive_error_count": endpoint.consecutive_error_count,
                            },
                        )
                    )
                db.add(endpoint)

            db.commit()
        except Exception as exc:
            db.rollback()
            self._logger.error("Failed to apply telemetry tracking policy: %s", exc)
        finally:
            db.close()

    def _match_endpoint(self, db, event: dict[str, Any]) -> Endpoint | None:
        endpoint_id_raw = str(event.get("endpoint_id") or "").strip()
        if endpoint_id_raw:
            try:
                endpoint_id = uuid.UUID(endpoint_id_raw)
                endpoint = db.get(Endpoint, endpoint_id)
                if endpoint is not None:
                    return endpoint
            except Exception:
                pass

        org_id_raw = str(event.get("org_id") or "").strip()
        api_id_raw = str(event.get("api_id") or "").strip()
        method = str(event.get("method") or "GET").strip().upper()
        path_raw = str(event.get("endpoint") or "").strip()
        if not org_id_raw or not api_id_raw or not path_raw:
            return None

        normalized_path = path_raw if path_raw.startswith("/") else f"/{path_raw}"

        try:
            org_id = uuid.UUID(org_id_raw)
            api_id = uuid.UUID(api_id_raw)
        except Exception:
            return None

        endpoint = db.query(Endpoint).filter(
            Endpoint.org_id == org_id,
            Endpoint.api_id == api_id,
            Endpoint.method == method,
            Endpoint.path == normalized_path,
        ).one_or_none()
        if endpoint is not None:
            return endpoint

        if path_raw != normalized_path:
            return db.query(Endpoint).filter(
                Endpoint.org_id == org_id,
                Endpoint.api_id == api_id,
                Endpoint.method == method,
                Endpoint.path == path_raw,
            ).one_or_none()

        return None