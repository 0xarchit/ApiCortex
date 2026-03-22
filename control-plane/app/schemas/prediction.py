import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class PredictionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    time: datetime
    api_id: uuid.UUID
    endpoint: str
    risk_score: float
    prediction: str
    confidence: float
    top_features: list[dict[str, Any]]
