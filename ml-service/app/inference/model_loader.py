from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import joblib


def load_model(model_path: Path) -> Any:
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_path}")

    try:
        with model_path.open("rb") as file_handle:
            return pickle.load(file_handle)
    except Exception:
        
        return joblib.load(model_path)
