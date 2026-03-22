import uuid
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.schemas.prediction import PredictionRecordOut
from app.services.dashboard_service import timescale_engine

router = APIRouter()

@router.get("/", response_model=list[PredictionRecordOut])
def get_predictions(request: Request, limit: int = 50):
    org_id = uuid.UUID(str(request.state.org_id))
    limit = max(1, min(limit, 100))

    query = text(
        """
        SELECT
            time, api_id, endpoint, risk_score, prediction, confidence, top_features
        FROM api_failure_predictions
        WHERE org_id = :org_id
        ORDER BY time DESC
        LIMIT :limit
        """
    )
    with timescale_engine.connect() as conn:
        rows = conn.execute(query, {"org_id": str(org_id), "limit": limit}).mappings().all()

    return [
        PredictionRecordOut(
            time=row["time"],
            api_id=row["api_id"],
            endpoint=row["endpoint"],
            risk_score=float(row["risk_score"]),
            prediction=row["prediction"],
            confidence=float(row["confidence"]),
            top_features=row["top_features"] if isinstance(row["top_features"], list) else [],
        )
        for row in rows
    ]
