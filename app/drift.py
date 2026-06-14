import os


DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "5.0"))


def detect_drift(features: list[float]) -> bool:
    return any(abs(value) > DRIFT_THRESHOLD for value in features)
