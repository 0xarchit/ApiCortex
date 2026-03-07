from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from confluent_kafka import Message

from app.config import Settings
from app.explainability.shap_explainer import ShapExplainer
from app.features.feature_engineering import RollingFeatureEngineer
from app.inference.model_loader import load_model
from app.inference.predictor import Predictor
from app.kafka.consumer import KafkaBatchConsumer, RetryableKafkaError
from app.storage.timescale_writer import PredictionRecord, TimescaleWriter


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("apicortex.ml-worker")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


@dataclass
class WorkerMetrics:
    batches_processed: int = 0
    events_processed: int = 0
    predictions_written: int = 0
    inference_errors: int = 0


class InferenceWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = configure_logging(settings.log_level)

        model = load_model(settings.model_path)
        explainer = ShapExplainer(
            model=model,
            enabled=settings.enable_shap,
            top_k=settings.shap_top_k,
            logger=self.logger,
        )

        self.predictor = Predictor(model=model, explainer=explainer)
        self.feature_engineer = RollingFeatureEngineer()
        self.consumer = KafkaBatchConsumer(settings)
        self.writer = TimescaleWriter(settings)

        self.metrics = WorkerMetrics()
        self._shutdown = asyncio.Event()

    def request_shutdown(self) -> None:
        self._shutdown.set()

    async def run(self) -> None:
        self.logger.info("ML inference worker started")

        while not self._shutdown.is_set():
            try:
                message = await asyncio.to_thread(self.consumer.poll_message, self.settings.kafka_poll_timeout_seconds)
            except RetryableKafkaError as exc:
                self.logger.warning(
                    "Kafka topic unavailable, waiting for topic creation",
                    extra={
                        "extra": {
                            "error": str(exc),
                            "topic": self.settings.kafka_topic_raw,
                        }
                    },
                )
                await asyncio.sleep(max(1.0, self.settings.kafka_poll_timeout_seconds))
                continue
            except Exception as exc:
                self.metrics.inference_errors += 1
                self.logger.exception(
                    "Kafka poll failed",
                    extra={
                        "extra": {
                            "error": str(exc),
                            "inference_errors": self.metrics.inference_errors,
                        }
                    },
                )
                await asyncio.sleep(max(1.0, self.settings.kafka_poll_timeout_seconds))
                continue

            if message is None:
                continue

            try:
                await self._handle_message(message)
            except Exception as exc:
                self.metrics.inference_errors += 1
                self.logger.exception(
                    "Failed to process telemetry batch",
                    extra={
                        "extra": {
                            "error": str(exc),
                            "inference_errors": self.metrics.inference_errors,
                        }
                    },
                )
                
                await asyncio.to_thread(self.consumer.commit_message, message)

        await self._shutdown_cleanup()

    async def _handle_message(self, message: Message) -> None:
        consume_started = time.perf_counter()
        kafka_lag = await asyncio.to_thread(self.consumer.lag_for_message, message)

        events = await asyncio.to_thread(self.consumer.decode_message, message)
        if not events:
            await asyncio.to_thread(self.consumer.commit_message, message)
            return

        feature_rows = self.feature_engineer.ingest(events)
        prediction_records: list[PredictionRecord] = []

        for feature_row in feature_rows:
            result = self.predictor.predict(feature_row.features)
            prediction_records.append(
                PredictionRecord(
                    time=feature_row.time,
                    org_id=feature_row.org_id,
                    api_id=feature_row.api_id,
                    endpoint=feature_row.endpoint,
                    risk_score=result.risk_score,
                    prediction=result.prediction,
                    confidence=result.confidence,
                    top_features=result.top_features,
                )
            )

            if result.risk_score >= self.settings.alert_threshold:
                alert_payload = {
                    "org_id": feature_row.org_id,
                    "api_id": feature_row.api_id,
                    "endpoint": feature_row.endpoint,
                    "risk_score": result.risk_score,
                    "severity": "high",
                    "timestamp": feature_row.time.isoformat(),
                }
                await asyncio.to_thread(self.consumer.publish_alert, alert_payload)

        await asyncio.to_thread(self.writer.write_predictions, prediction_records)
        await asyncio.to_thread(self.consumer.commit_message, message)

        duration_ms = round((time.perf_counter() - consume_started) * 1000, 2)
        self.metrics.batches_processed += 1
        self.metrics.events_processed += len(events)
        self.metrics.predictions_written += len(prediction_records)

        self.logger.info(
            "Processed telemetry batch",
            extra={
                "extra": {
                    "events_processed": len(events),
                    "predictions_written": len(prediction_records),
                    "prediction_latency_ms": duration_ms,
                    "kafka_lag": kafka_lag,
                    "totals": {
                        "batches": self.metrics.batches_processed,
                        "events": self.metrics.events_processed,
                        "predictions": self.metrics.predictions_written,
                        "inference_errors": self.metrics.inference_errors,
                    },
                }
            },
        )

    async def _shutdown_cleanup(self) -> None:
        self.logger.info("Shutting down ML inference worker")
        await asyncio.to_thread(self.writer.close)
        await asyncio.to_thread(self.consumer.close)


def install_signal_handlers(worker: InferenceWorker) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.request_shutdown)
        except NotImplementedError:
            
            signal.signal(sig, lambda _signo, _frame: worker.request_shutdown())
