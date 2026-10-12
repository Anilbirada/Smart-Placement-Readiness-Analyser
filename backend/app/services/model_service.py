from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import MODEL_PATH, MODEL_SCHEMA_VERSION, DEFAULT_FALLBACK_MODE
from backend.app.features.url_features import extract_url_features


@dataclass
class ModelStatus:
    model_loaded: bool
    model_version: Optional[str] = None
    feature_schema_version: Optional[str] = None
    fallback_mode_active: bool = True
    available_evaluation_metadata: Dict[str, Any] = None
    is_compatible: bool = True


class RuleBasedModel:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or MODEL_PATH
        self.model_version = "rule-based-demo"
        self.feature_schema_version = MODEL_SCHEMA_VERSION
        self.available_evaluation_metadata = {
            "mode": "rule-based", 
            "dataset_reference": "No trusted dataset loaded",
            "evaluation_status": "Not run; fallback mode is active",
        }

    def is_available(self) -> bool:
        return False

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        indicators: List[str] = []

        if features["number_of_dots"] > 3:
            score += 1
            indicators.append("Multiple dots in hostname")
        if features["number_of_hyphens"] > 3:
            score += 1
            indicators.append("Multiple hyphens in hostname")
        if features["number_of_parameters"] >= 2:
            score += 1
            indicators.append("Multiple query parameters")
        if features["has_at_sign"]:
            score += 1
            indicators.append("User information or at-sign detected")
        if features["hostname_length"] > 30:
            score += 1
            indicators.append("Hostname length is unusually long")
        if features["is_ip_address"]:
            score += 1
            indicators.append("Raw IP address used as hostname")
        if features["punycode_indicator"]:
            score += 1
            indicators.append("Punycode hostname indicator")
        if features["unusual_hostname_pattern"]:
            score += 1
            indicators.append("Unusual hostname pattern")
        if features["path_length"] > 120:
            score += 1
            indicators.append("Long path fragment")
        if features["suspicious_encoding_pattern"]:
            score += 1
            indicators.append("Encoded URL artifacts detected")

        if score >= 5:
            category = "Potentially Malicious"
        elif score >= 3:
            category = "Suspicious"
        elif score >= 1:
            category = "Lower Risk Indicators Found"
        else:
            category = "Unable to Determine"

        recommendations = [
            "Check whether the site uses a trusted domain, secure certificate, and consistent branding.",
            "Review the destination for signs of credential theft, fake login pages, or impersonation.",
            "Do not enter personal data unless the site is independently verified.",
        ]

        return {
            "risk_category": category,
            "score": round(score / 10, 3),
            "indicators": indicators,
            "recommendations": recommendations,
            "analysis_method": "rule-based fallback",
            "model_version": self.model_version,
            "model_status": "fallback-mode-active",
            "limitations": "This is a transparent heuristic assessment only. It does not establish malicious intent and should not be treated as a calibrated probability.",
            "confidence_note": "No trained model is currently loaded; this fallback is explanatory only.",
        }


def get_model_status() -> ModelStatus:
    return ModelStatus(
        model_loaded=False,
        model_version=None,
        feature_schema_version=MODEL_SCHEMA_VERSION,
        fallback_mode_active=True,
        available_evaluation_metadata={
            "mode": DEFAULT_FALLBACK_MODE,
            "dataset_reference": "No approved dataset is configured in this workspace",
            "evaluation_status": "Not run; model not trained or loaded",
        },
        is_compatible=True,
    )


def analyze_with_available_model(raw_url: str) -> Dict[str, Any]:
    features = extract_url_features(raw_url)
    model = RuleBasedModel()
    result = model.predict(features)
    result["submitted_url"] = raw_url
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["features"] = features
    return result
