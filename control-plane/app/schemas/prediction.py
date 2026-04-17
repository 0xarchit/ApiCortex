"""Response schemas for anomaly prediction and failure likelihood endpoints."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PredictionFeatureOut(BaseModel):
    """Feature contribution information for a prediction."""
    name: str
    value: float
    contribution: float

class PredictionRecordOut(BaseModel):
    """Response schema for a single prediction record."""
    model_config = ConfigDict(from_attributes=True)

    time: datetime
    api_id: uuid.UUID
    endpoint: str
    risk_score: float
    prediction: str
    confidence: float
    top_features: list[PredictionFeatureOut]
