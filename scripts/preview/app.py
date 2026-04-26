from __future__ import annotations

import io
import pickle
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
MODEL_PATH = BASE_DIR / "model" / "xgboost_failure_prediction.pkl"
INDEX_PATH = BASE_DIR / "static" / "index.html"
SAMPLE_PATH = BASE_DIR / "demo_data_5000.csv"
MODEL_THRESHOLD = 0.73
WARNING_THRESHOLD = 0.4
REQUIRED_COLUMNS = [
    "timestamp",
    "window_duration_minutes",
    "p50_latency",
    "p90_latency",
    "p95_latency",
    "latency_variance",
    "latency_delta",
    "error_rate",
    "error_rate_delta",
    "traffic_rps",
    "traffic_delta",
    "schema_fields_added",
    "schema_fields_removed",
    "schema_breaking_changes",
    "schema_entropy",
    "schema_entropy_delta",
    "recent_deploy",
]

app = FastAPI(title="ApiCortex ML Preview", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def load_model():
    try:
        with MODEL_PATH.open("rb") as file_handle:
            return pickle.load(file_handle)
    except Exception:
        return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def model_feature_columns() -> list[str]:
    model = load_model()
    names = getattr(model, "feature_names_in_", None)
    if names is None:
        raise RuntimeError("Model does not expose feature_names_in_")
    return [str(name) for name in names]


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce")
    working = working.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    numeric_columns = [column for column in REQUIRED_COLUMNS if column != "timestamp"]
    for column in numeric_columns:
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    p95_shift = working["p95_latency"].shift(1)
    p50_shift = working["p50_latency"].shift(1).replace(0, np.nan)
    p95_roll_mean_15 = p95_shift.rolling(15, min_periods=5).mean().bfill()
    p95_roll_mean_30 = p95_shift.rolling(30, min_periods=8).mean().bfill()
    p95_roll_std_30 = p95_shift.rolling(30, min_periods=8).std().replace(0, np.nan)
    error_threshold = working["error_rate"].quantile(0.80)

    working["p95_latency_roll_mean_15"] = p95_roll_mean_15
    working["latency_variance_roll_std_15"] = working["latency_variance"].shift(1).rolling(15, min_periods=5).std().fillna(0)
    working["error_rate_roll_mean_15"] = working["error_rate"].shift(1).rolling(15, min_periods=5).mean().bfill()
    working["error_rate_acceleration"] = working["error_rate"].diff().diff().shift(1).fillna(0)
    working["traffic_utilization_proxy"] = (working["traffic_rps"].shift(1).rolling(10, min_periods=4).mean() / 2000.0).bfill()
    working["p95_to_p50_ratio"] = (p95_shift / p50_shift).replace([np.inf, -np.inf], np.nan).bfill().fillna(0)
    working["latency_p95_zscore"] = ((p95_shift - p95_roll_mean_30) / p95_roll_std_30).replace([np.inf, -np.inf], np.nan).fillna(0)
    working["error_rate_ewm"] = working["error_rate"].shift(1).ewm(alpha=0.3, adjust=False).mean().bfill()
    working["p95_latency_roll_max_15"] = p95_shift.rolling(15, min_periods=5).max().bfill()
    working["error_high_streak"] = (working["error_rate"].shift(1) > error_threshold).astype(float).rolling(10, min_periods=3).sum().fillna(0)

    feature_columns = model_feature_columns()
    working[feature_columns] = working[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return working


def risk_band(score: float) -> str:
    if score >= MODEL_THRESHOLD:
        return "high_failure_risk"
    if score >= WARNING_THRESHOLD:
        return "watch"
    return "stable"


def load_uploaded_frame(upload_id: str) -> pd.DataFrame:
    csv_path = UPLOAD_DIR / f"{upload_id}.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found")
    return pd.read_csv(csv_path)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_PATH)


@app.get("/demo-data")
def demo_data() -> FileResponse:
    return FileResponse(SAMPLE_PATH, filename="demo_data_5000.csv")


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    content = await file.read()
    try:
        frame = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to read CSV: {exc}") from exc

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise HTTPException(status_code=400, detail={"message": "Missing required columns", "columns": missing})

    upload_id = uuid4().hex
    destination = UPLOAD_DIR / f"{upload_id}.csv"
    destination.write_bytes(content)

    return {
        "upload_id": upload_id,
        "filename": file.filename,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
    }


@app.post("/api/process/{upload_id}")
def process_dataset(upload_id: str) -> dict:
    source = load_uploaded_frame(upload_id)
    if source.empty:
        raise HTTPException(status_code=400, detail="Uploaded CSV is empty")

    enriched = engineer_features(source)
    if enriched.empty:
        raise HTTPException(status_code=400, detail="No valid rows remain after parsing timestamps")

    feature_columns = model_feature_columns()
    model = load_model()
    probabilities = model.predict_proba(enriched[feature_columns])[:, 1]
    enriched["risk_score"] = probabilities
    enriched["risk_band"] = [risk_band(score) for score in probabilities]
    enriched["predicted_label"] = (enriched["risk_score"] >= MODEL_THRESHOLD).astype(int)

    total_rows = int(len(enriched))
    step = max(1, total_rows // 220)
    sampled = enriched.iloc[::step].copy()
    if sampled.index[-1] != enriched.index[-1]:
        sampled = pd.concat([sampled, enriched.tail(1)], ignore_index=True)

    summary = {
        "rows_processed": total_rows,
        "high_risk_rows": int((enriched["risk_score"] >= MODEL_THRESHOLD).sum()),
        "watch_rows": int(((enriched["risk_score"] >= WARNING_THRESHOLD) & (enriched["risk_score"] < MODEL_THRESHOLD)).sum()),
        "stable_rows": int((enriched["risk_score"] < WARNING_THRESHOLD).sum()),
        "peak_risk": round(float(enriched["risk_score"].max()), 4),
        "average_risk": round(float(enriched["risk_score"].mean()), 4),
    }

    metrics = {}
    if "label" in enriched.columns:
        actual = pd.to_numeric(enriched["label"], errors="coerce").fillna(0).astype(int)
        predicted = enriched["predicted_label"].astype(int)
        metrics = {
            "agreement": round(float((actual == predicted).mean()), 4),
            "true_positives": int(((actual == 1) & (predicted == 1)).sum()),
            "false_positives": int(((actual == 0) & (predicted == 1)).sum()),
            "false_negatives": int(((actual == 1) & (predicted == 0)).sum()),
        }

    top_alerts = enriched.sort_values("risk_score", ascending=False).head(8)
    alerts = [
        {
            "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
            "risk_score": round(float(row["risk_score"]), 4),
            "risk_band": row["risk_band"],
            "p95_latency": round(float(row["p95_latency"]), 2),
            "error_rate": round(float(row["error_rate"]), 4),
            "traffic_rps": round(float(row["traffic_rps"]), 2),
            "actual_label": int(row["label"]) if "label" in enriched.columns else None,
        }
        for _, row in top_alerts.iterrows()
    ]

    playback = [
        {
            "timestamp": row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"]),
            "risk_score": round(float(row["risk_score"]), 4),
            "risk_band": row["risk_band"],
            "p95_latency": round(float(row["p95_latency"]), 2),
            "error_rate": round(float(row["error_rate"]), 4),
            "traffic_rps": round(float(row["traffic_rps"]), 2),
            "actual_label": int(row["label"]) if "label" in enriched.columns else None,
        }
        for _, row in sampled.iterrows()
    ]

    latest = playback[-1]
    return {
        "summary": summary,
        "metrics": metrics,
        "playback": playback,
        "alerts": alerts,
        "latest": latest,
        "feature_columns": feature_columns,
    }
