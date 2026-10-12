from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from backend.app.features.url_features import extract_url_features


def build_feature_row(url: str, label: str) -> dict:
    features = extract_url_features(url)
    features["label"] = label
    return features


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a URL risk model from a CSV dataset.")
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--output-path", required=True, type=Path)
    args = parser.parse_args()

    if not args.dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {args.dataset_path}")

    data = pd.read_csv(args.dataset_path)
    required = {"url", "label"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    rows = [build_feature_row(url=row["url"], label=row["label"]) for _, row in data.iterrows()]
    feature_frame = pd.DataFrame(rows)
    X = feature_frame.drop(columns=["label"])
    y = feature_frame["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    metadata = {
        "model_type": "LogisticRegression",
        "dataset_path": str(args.dataset_path),
        "label_values": sorted(y.unique().tolist()),
        "classification_report": classification_report(y_test, preds, output_dict=True),
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
    }

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "metadata": metadata, "schema_version": "1.0"}, args.output_path)
    print(json.dumps({"output_path": str(args.output_path), "metrics": metadata["classification_report"]}, indent=2))


if __name__ == "__main__":
    main()
