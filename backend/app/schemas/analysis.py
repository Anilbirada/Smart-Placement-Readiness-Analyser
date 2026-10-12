from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.features.url_features import normalize_url_for_analysis


class RiskCategory(str, Enum):
    POTENTIALLY_MALICIOUS = "Potentially Malicious"
    SUSPICIOUS = "Suspicious"
    LOWER_RISK_INDICATORS_FOUND = "Lower Risk Indicators Found"
    UNABLE_TO_DETERMINE = "Unable to Determine"


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("URL must not be empty.")
        return normalize_url_for_analysis(value)


class FeatureSummary(BaseModel):
    total_url_length: int
    hostname_length: int
    path_length: int
    number_of_dots: int
    number_of_hyphens: int
    number_of_digits: int
    number_of_parameters: int
    is_ip_address: bool
    has_at_sign: bool
    scheme: str
    punycode_indicator: bool
    unusual_hostname_pattern: bool
    number_of_subdomains: int
    suspicious_encoding_pattern: bool


class ModelStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    model_loaded: bool
    model_version: Optional[str] = None
    feature_schema_version: Optional[str] = None
    fallback_mode_active: bool
    available_evaluation_metadata: Dict[str, Any] = {}
    is_compatible: bool = True


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), extra="forbid")

    analysis_id: Optional[str] = None
    submitted_url: str
    risk_category: RiskCategory
    analysis_method: str
    model_version: Optional[str] = None
    score: Optional[float] = None
    features: FeatureSummary
    indicators: List[str]
    recommendations: List[str]
    timestamp: str
    limitations: str
    confidence_note: str
    model_status: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
