from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from app.explainability.shap_explainer import ShapExplainer
from app.features.feature_engineering import FEATURE_COLUMNS


@dataclass
class PredictionResult:
    risk_score: float
    prediction: str
    confidence: float
    top_features: list[dict[str, float]]


class Predictor:
    def __init__(self, model: Any, explainer: ShapExplainer | None = None) -> None:
        self._model = model
        self._explainer = explainer
        model_features = getattr(model, "feature_names_in_", None)
        self._feature_order = list(model_features) if model_features is not None else list(FEATURE_COLUMNS)

    def predict(self, features: dict[str, float]) -> PredictionResult:
        frame = pd.DataFrame([{name: float(features.get(name, 0.0)) for name in self._feature_order}])

        risk_score = self._predict_probability(frame)
        prediction = self._label_for_score(risk_score)
        confidence = float(max(risk_score, 1.0 - risk_score))

        top_features: list[dict[str, float]] = []
        if self._explainer is not None:
            top_features = self._explainer.explain(frame)

        return PredictionResult(
            risk_score=risk_score,
            prediction=prediction,
            confidence=confidence,
            top_features=top_features,
        )

    def _predict_probability(self, frame: pd.DataFrame) -> float:
        if hasattr(self._model, "predict_proba"):
            output = self._model.predict_proba(frame)
            probability = float(output[0][1])
        else:
            output = self._model.predict(frame)
            probability = float(np.asarray(output)[0])
        return float(np.clip(probability, 0.0, 1.0))

    @staticmethod
    def _label_for_score(score: float) -> str:
        if score < 0.4:
            return "normal"
        if score < 0.7:
            return "degraded"
        return "high_failure_risk"
