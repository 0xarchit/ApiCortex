"""Service for cleaning up time-series data in TimescaleDB."""
import uuid

from sqlalchemy import text

from app.services.dashboard_service import timescale_engine


class TimescaleCleanupService:
    """Service for deleting telemetry and prediction data for APIs."""
    @staticmethod
    def delete_api_data(org_id: uuid.UUID, api_id: uuid.UUID) -> dict[str, int]:
        """Delete all telemetry and prediction data for an API.
        
        Args:
            org_id: Organization UUID.
            api_id: API UUID.
            
        Returns:
            Dictionary with counts of deleted records by type.
        """
        params = {"org_id": str(org_id), "api_id": str(api_id)}
        with timescale_engine.begin() as conn:
            predictions_result = conn.execute(
                text(
                    """
                    DELETE FROM api_failure_predictions
                    WHERE org_id = :org_id AND api_id = :api_id
                    """
                ),
                params,
            )
            telemetry_result = conn.execute(
                text(
                    """
                    DELETE FROM api_telemetry
                    WHERE org_id = :org_id AND api_id = :api_id
                    """
                ),
                params,
            )

        deleted_predictions = predictions_result.rowcount if predictions_result.rowcount and predictions_result.rowcount > 0 else 0
        deleted_telemetry = telemetry_result.rowcount if telemetry_result.rowcount and telemetry_result.rowcount > 0 else 0
        return {
            "predictions": deleted_predictions,
            "telemetry": deleted_telemetry,
        }

    @staticmethod
    def delete_endpoint_data(org_id: uuid.UUID, api_id: uuid.UUID, endpoint: str, method: str) -> dict[str, int]:
        """Delete telemetry and prediction data for a single endpoint.

        Args:
            org_id: Organization UUID.
            api_id: API UUID.
            endpoint: Endpoint path stored in TimescaleDB.
            method: HTTP method stored in TimescaleDB.

        Returns:
            Dictionary with counts of deleted records by type.
        """
        params = {
            "org_id": str(org_id),
            "api_id": str(api_id),
            "endpoint": endpoint,
            "method": method.upper(),
        }
        with timescale_engine.begin() as conn:
            predictions_result = conn.execute(
                text(
                    """
                    DELETE FROM api_failure_predictions
                    WHERE org_id = :org_id
                      AND api_id = :api_id
                      AND endpoint = :endpoint
                      AND method = :method
                    """
                ),
                params,
            )
            telemetry_result = conn.execute(
                text(
                    """
                    DELETE FROM api_telemetry
                    WHERE org_id = :org_id
                      AND api_id = :api_id
                      AND endpoint = :endpoint
                      AND method = :method
                    """
                ),
                params,
            )

        deleted_predictions = predictions_result.rowcount if predictions_result.rowcount and predictions_result.rowcount > 0 else 0
        deleted_telemetry = telemetry_result.rowcount if telemetry_result.rowcount and telemetry_result.rowcount > 0 else 0
        return {
            "predictions": deleted_predictions,
            "telemetry": deleted_telemetry,
        }
