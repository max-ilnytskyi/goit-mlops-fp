import json
import logging
import os
import time
from pathlib import Path

import joblib
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.drift import detect_drift
from app.schemas import PredictionRequest, PredictionResponse


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "model" / "model.pkl"))

app = FastAPI(title="goit-mlops-fp inference service")

model = None

REQUEST_COUNTER = Counter(
    "inference_requests_total",
    "Total number of inference requests.",
)

DRIFT_COUNTER = Counter(
    "drift_detected_total",
    "Total number of detected drift events.",
)

PREDICTION_LATENCY = Histogram(
    "prediction_latency_seconds",
    "Prediction latency in seconds.",
)


@app.on_event("startup")
def load_model():
    global model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)
    logger.info("Model loaded from %s", MODEL_PATH)


def predict(data: list[float]) -> int:
    prediction = model.predict([data])[0]
    return int(prediction)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict_endpoint(request: PredictionRequest):
    start_time = time.time()
    REQUEST_COUNTER.inc()

    drift_detected = detect_drift(request.features)

    if drift_detected:
        DRIFT_COUNTER.inc()
        logger.warning("Drift detected")

    prediction = predict(request.features)

    latency = time.time() - start_time
    PREDICTION_LATENCY.observe(latency)

    log_payload = {
        "features": request.features,
        "prediction": prediction,
        "drift_detected": drift_detected,
        "latency_seconds": round(latency, 6),
    }

    logger.info("Prediction request: %s", json.dumps(log_payload))

    return PredictionResponse(
        prediction=prediction,
        drift_detected=drift_detected,
    )


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/retrain-webhook")
def retrain_webhook():
    logger.info("Retrain webhook received")
    return {"status": "retrain_requested"}
