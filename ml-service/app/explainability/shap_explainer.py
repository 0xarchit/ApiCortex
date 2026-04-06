from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd


class ShapExplainer:
    def __init__(self, model: Any, enabled: bool, top_k: int, logger: logging.Logger) -> None:
        self._model = model
        self._enabled = enabled
        self._top_k = top_k
        self._logger = logger
        self._explainer: Any | None = None

    def explain(self, feature_frame: pd.DataFrame) -> list[dict[str, float]]:
        if not self._enabled:
            return []
        try:
            import shap

            if self._explainer is None:
                self._explainer = shap.TreeExplainer(self._model)

            shap_values = self._explainer.shap_values(feature_frame)
            if isinstance(shap_values, list):
                # Multi-class output, take the last class (failure prediction)
                values = np.asarray(shap_values[-1])[0]
            else:
                values = np.asarray(shap_values)[0]

            # Get top features by absolute contribution
            abs_values = np.abs(values)
            top_indices = np.argsort(abs_values)[::-1][: self._top_k]
            features = []
            for idx in top_indices:
                feature_name = str(feature_frame.columns[idx])
                contribution = float(values[idx])
                abs_contribution = float(abs_values[idx])
                feature_value = float(feature_frame.iloc[0, idx])
                features.append({
                    "feature": feature_name,
                    "name": feature_name,
                    "value": feature_value,
                    "contribution": contribution,
                    "abs_contribution": abs_contribution,
                })
            return features
        except Exception as exc:
            self._logger.warning("SHAP explainability unavailable", extra={"extra": {"error": str(exc)}})
            return []
