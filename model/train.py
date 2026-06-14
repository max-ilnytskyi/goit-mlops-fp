import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_PATH = BASE_DIR / "model.pkl"
DEFAULT_METADATA_PATH = BASE_DIR / "model_metadata.json"


def generate_dataset(random_state: int = 42):
    X, y = make_classification(
        n_samples=1000,
        n_features=4,
        n_informative=3,
        n_redundant=0,
        n_classes=2,
        random_state=random_state,
    )
    return X, y


def train_model(random_state: int = 42):
    X, y = generate_dataset(random_state=random_state)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_state,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    metadata = {
        "model_type": "RandomForestClassifier",
        "n_features": X.shape[1],
        "accuracy": round(float(accuracy), 4),
        "random_state": random_state,
    }

    return model, metadata


def save_model(model, metadata, model_path: Path, metadata_path: Path):
    model_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_path)

    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Model saved to: {model_path}")
    print(f"Metadata saved to: {metadata_path}")
    print(f"Accuracy: {metadata['accuracy']}")


def parse_args():
    parser = argparse.ArgumentParser(description="Train and save ML model.")
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Path where trained model will be saved.",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help="Path where model metadata will be saved.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random state for reproducible training.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    trained_model, model_metadata = train_model(random_state=args.random_state)
    save_model(
        model=trained_model,
        metadata=model_metadata,
        model_path=args.model_path,
        metadata_path=args.metadata_path,
    )
