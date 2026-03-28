from __future__ import annotations

import asyncio
import gzip
import json
import logging
import base64
from dataclasses import dataclass
from threading import Lock
from typing import Any

from confluent_kafka import Consumer, KafkaError, Message, Producer, TopicPartition

from app.config import Settings
from app.schemas.telemetry_event import TelemetryEvent


class RetryableKafkaError(RuntimeError):
    """Represents Kafka errors that should not terminate the worker loop."""


@dataclass
class DecodeResult:
    valid_events: list[TelemetryEvent]
    invalid_payloads: list[dict[str, Any]]
    payload_corruption_count: int
    

class KafkaBatchConsumer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._consumer = Consumer(settings.consumer_config)
        self._consumer.subscribe([settings.kafka_topic_raw])
        self._producer = Producer(settings.producer_config)
        self._logger = logging.getLogger(__name__)
        self._delivery_errors: list[str] = []
        self._pending_deliveries: int = 0
        self._delivery_lock = Lock()

    def _on_alert_delivery(self, err, msg) -> None:
        with self._delivery_lock:
            self._pending_deliveries = max(0, self._pending_deliveries - 1)
        if err:
            error_msg = f"Alert delivery failed: {err}"
            with self._delivery_lock:
                self._delivery_errors.append(error_msg)
            self._logger.error(error_msg)

    def poll_message(self, timeout_seconds: float) -> Message | None:
        message = self._consumer.poll(timeout_seconds)
        if message is None:
            return None
        if message.error():
            code = message.error().code()
            if code == KafkaError._PARTITION_EOF:
                return None
            unknown_topic_code = getattr(KafkaError, "UNKNOWN_TOPIC_OR_PART", None)
            if unknown_topic_code is not None and code == unknown_topic_code:
                raise RetryableKafkaError(
                    f"Kafka topic unavailable: {self._settings.kafka_topic_raw}: {message.error()}"
                )
            raise RuntimeError(f"Kafka consume error: {message.error()}")
        return message

    def decode_message(self, message: Message) -> DecodeResult:
        payload = message.value()
        if payload is None:
            return DecodeResult(valid_events=[], invalid_payloads=[], payload_corruption_count=0)

        try:
            payload = self._decompress_if_needed(payload, message.headers())
        except Exception as exc:
            return DecodeResult(
                valid_events=[],
                invalid_payloads=[{
                    "original_payload": None,
                    "reason": f"Decompression failed: {exc}",
                }],
                payload_corruption_count=1,
            )

        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            return DecodeResult(
                valid_events=[],
                invalid_payloads=[{
                    "original_payload": None,
                    "reason": f"JSON decode failed: {exc}",
                }],
                payload_corruption_count=1,
            )

        if not isinstance(data, list):
            return DecodeResult(
                valid_events=[],
                invalid_payloads=[{
                    "original_payload": data,
                    "reason": "Expected JSON array, got single object or other type",
                }],
                payload_corruption_count=1,
            )

        valid_events: list[TelemetryEvent] = []
        invalid_payloads: list[dict[str, Any]] = []

        for item in data:
            try:
                event = TelemetryEvent.model_validate(item)
                valid_events.append(event)
            except Exception as exc:
                invalid_payloads.append({
                    "original_payload": item,
                    "reason": str(exc),
                })

        return DecodeResult(valid_events=valid_events, invalid_payloads=invalid_payloads, payload_corruption_count=0)

    @staticmethod
    def _decompress_if_needed(payload: bytes, headers: list[tuple[str, bytes]] | None) -> bytes:
        header_map: dict[str, str] = {}
        if headers:
            header_map = {
                key.lower(): (value.decode("utf-8") if isinstance(value, (bytes, bytearray)) else str(value))
                for key, value in headers
            }

        content_encoding = header_map.get("content-encoding", "").lower()
        if content_encoding == "gzip" or payload[:2] == b"\x1f\x8b":
            return gzip.decompress(payload)

        if content_encoding == "snappy":
            try:
                import snappy

                return snappy.decompress(payload)
            except Exception as exc:
                raise RuntimeError(f"snappy decode failed: {exc}") from exc

        return payload

    def lag_for_message(self, message: Message) -> int:
        topic_partition = TopicPartition(message.topic(), message.partition())
        low, high = self._consumer.get_watermark_offsets(
            topic_partition,
            timeout=1.0,
            cached=False,
        )
        return max(0, high - message.offset() - 1)

    def commit_message(self, message: Message) -> None:
        self._consumer.commit(message=message, asynchronous=False)

    def publish_alert(self, alert: dict[str, Any], callback=None) -> None:
        payload = json.dumps(alert, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        delivery_callback = callback if callback is not None else self._on_alert_delivery
        with self._delivery_lock:
            self._pending_deliveries += 1
        try:
            self._producer.produce(
                topic=self._settings.kafka_topic_alerts,
                value=payload,
                headers=[("content-type", "application/json"), ("schema", "alerts.failure-risk.v1")],
                on_delivery=delivery_callback,
            )
            self._producer.poll(0)
        except Exception as exc:
            with self._delivery_lock:
                self._pending_deliveries = max(0, self._pending_deliveries - 1)
            error_msg = f"Failed to produce alert: {exc}"
            with self._delivery_lock:
                self._delivery_errors.append(error_msg)
            self._logger.error(error_msg)
            raise

    def wait_for_pending_alerts(self, timeout_seconds: float = 5.0) -> bool:
        import time
        start_time = time.time()
        while (time.time() - start_time) < timeout_seconds:
            with self._delivery_lock:
                pending = self._pending_deliveries
            if pending <= 0:
                return True
            self._producer.poll(0.1)
        with self._delivery_lock:
            pending = self._pending_deliveries
        if pending > 0:
            self._logger.warning(
                f"Timeout waiting for pending alerts: {pending} still pending"
            )
            return False
        return True

    def get_and_clear_delivery_errors(self) -> list[str]:
        with self._delivery_lock:
            errors = self._delivery_errors.copy()
            self._delivery_errors.clear()
        return errors

    def pending_deliveries(self) -> int:
        with self._delivery_lock:
            return self._pending_deliveries

    def publish_invalid_payload(self, original_payload: Any, reason: str, source_topic: str, source_offset: int) -> None:
        dlq_topic = f"{source_topic}.dlq"
        dlq_message = {
            "source_topic": source_topic,
            "source_offset": source_offset,
            "failure_reason": reason,
            "original_payload": original_payload,
        }
        payload = json.dumps(dlq_message, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
        try:
            self._producer.produce(
                topic=dlq_topic,
                value=payload,
                headers=[("content-type", "application/json"), ("schema", "dlq.invalid-payload.v1")],
            )
            self._producer.poll(0)
        except Exception as exc:
            self._logger.warning(
                "Failed to publish to DLQ",
                extra={"extra": {"dlq_topic": dlq_topic, "reason": str(exc)}}
            )

    def publish_processing_failure(self, message: Message, reason: str) -> None:
        topic = self._settings.processing_failure_dlq_topic or f"{message.topic()}.processing-failure.dlq"
        raw_payload = message.value() or b""
        encoded_payload = base64.b64encode(raw_payload).decode("ascii")
        payload = {
            "source_topic": message.topic(),
            "source_partition": message.partition(),
            "source_offset": message.offset(),
            "failure_reason": reason,
            "payload_base64": encoded_payload,
        }
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self._producer.produce(
            topic=topic,
            value=body,
            headers=[("content-type", "application/json"), ("schema", "dlq.processing-failure.v1")],
        )
        self._producer.poll(0)

    def flush_producer(self, timeout_seconds: float = 5.0) -> None:
        remaining = self._producer.flush(timeout_seconds)
        if remaining > 0:
            self._logger.warning(
                "Producer flush timeout: messages still in queue",
                extra={"extra": {"remaining_messages": remaining}}
            )

    def close(self) -> None:
        pending = self.pending_deliveries()
        if pending > 0:
            self._logger.info(
                f"Waiting for {pending} pending alert deliveries before closing"
            )
            self.wait_for_pending_alerts(timeout_seconds=self._settings.kafka_alert_delivery_timeout_seconds)
            remaining = self._producer.flush(self._settings.kafka_alert_delivery_timeout_seconds)
            if remaining > 0:
                self._logger.warning(
                    f"Flush timeout: {remaining} messages still in producer queue"
                )

        delivery_errors = self.get_and_clear_delivery_errors()
        if delivery_errors:
            self._logger.warning(
                "Alert delivery errors occurred",
                extra={"extra": {"error_count": len(delivery_errors), "errors": delivery_errors}}
            )

        self._consumer.close()
        self._logger.info("Kafka consumer and producer closed")

