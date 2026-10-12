from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator

from backend.app.core.security import sanitize_text


class AuthRegisterRequest(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
    login_identifier: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        cleaned = sanitize_text(v, max_length=100)
        if len(cleaned) < 2:
            raise ValueError("Display name must be at least 2 characters after sanitization.")
        return cleaned

    @field_validator("login_identifier")
    @classmethod
    def validate_login_id(cls, v: str) -> str:
        cleaned = sanitize_text(v, max_length=100).lower()
        if len(cleaned) < 3 or " " in cleaned:
            raise ValueError("Login identifier must be at least 3 characters without spaces.")
        return cleaned


class AuthLoginRequest(BaseModel):
    login_identifier: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    display_name: str
    login_identifier: str


class SkillResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    active: bool


class RoleSkillRequirementResponse(BaseModel):
    skill_id: str
    skill_name: str
    skill_category: str
    skill_description: str
    weight: float
    expected_level: float
    rationale: str
    version: str


class JobRoleSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str
    active: bool
    skill_count: int


class JobRoleDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str
    active: bool
    total_weight: float
    skills: List[RoleSkillRequirementResponse]
    disclaimer: str


class StudentProfileRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    education_level: str = Field(..., min_length=2, max_length=120)
    target_role_id: str = Field(..., min_length=2, max_length=64)
    current_skills: List[str] = Field(default_factory=list, max_length=30)
    preferred_languages: List[str] = Field(default_factory=list, max_length=20)
    preparation_goal: str = Field(..., min_length=5, max_length=500)
    available_preparation_time: int = Field(..., ge=1, le=80)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = sanitize_text(v, max_length=100)
        if len(cleaned) < 2:
            raise ValueError("Display name must contain at least 2 valid characters.")
        return cleaned

    @field_validator("education_level", "preparation_goal")
    @classmethod
    def clean_strings(cls, v: str) -> str:
        cleaned = sanitize_text(v, max_length=500)
        if not cleaned:
            raise ValueError("Field cannot be empty or contain only HTML tags.")
        return cleaned

    @field_validator("current_skills", "preferred_languages")
    @classmethod
    def clean_string_lists(cls, items: List[str]) -> List[str]:
        result: List[str] = []
        for item in items:
            cleaned = sanitize_text(str(item), max_length=64)
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result


class StudentProfileResponse(BaseModel):
    id: str
    user_id: str
    display_name: str
    education_level: str
    target_role_id: str
    target_role_name: str
    current_skills: List[str]
    preferred_languages: List[str]
    preparation_goal: str
    available_preparation_time: int
    created_at: str
    updated_at: str


class QuestionOptionPublicResponse(BaseModel):
    option_identifier: str
    option_text: str


class QuestionPublicResponse(BaseModel):
    id: str
    skill_id: str
    skill_name: str
    topic: str
    skill_area: str
    question_type: str
    question_text: str
    difficulty: str
    score_value: float
    version: str
    options: List[QuestionOptionPublicResponse]


class AssessmentSummaryResponse(BaseModel):
    id: str
    title: str
    description: str
    instructions: str
    assessment_type: str
    skill_area: str
    time_limit_minutes: int
    version: str
    status: str
    question_count: int
    total_points: float
    covered_skills: List[str]


class AssessmentDetailResponse(BaseModel):
    id: str
    title: str
    description: str
    instructions: str
    assessment_type: str
    skill_area: str
    time_limit_minutes: int
    version: str
    status: str
    total_points: float
    questions: List[QuestionPublicResponse]


class StartAttemptRequest(BaseModel):
    expected_version: Optional[str] = None


class StartAttemptResponse(BaseModel):
    attempt_id: str
    assessment_id: str
    assessment_title: str
    assessment_version: str
    started_at: str
    status: str


class SubmittedAnswerItem(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=64)
    answer_value: Union[str, List[str]]
    # Note: If a malicious client attempts to pass score overrides, extra fields are ignored/rejected
    model_config = {"extra": "forbid"}


class SubmitAttemptRequest(BaseModel):
    answers: List[SubmittedAnswerItem] = Field(default_factory=list)
    require_all_questions: bool = Field(default=False)
    model_config = {"extra": "forbid"}


class QuestionResultItem(BaseModel):
    question_id: str
    topic: str
    skill_id: str
    skill_name: str
    question_type: str
    question_text: str
    submitted_answer: Union[str, List[str], None]
    awarded_score: float
    maximum_score: float
    is_correct: bool
    feedback: str
    explanation: str


class SkillScoreBreakdownItem(BaseModel):
    skill_id: str
    skill_name: str
    score: Optional[float]
    earned_points: float
    maximum_points: float
    assessment_status: str
    evidence_summary: str


class AttemptResultResponse(BaseModel):
    result_id: str
    attempt_id: str
    assessment_id: str
    assessment_title: str
    assessment_version: str
    scoring_version: str
    submitted_at: str
    overall_score: Optional[float]
    earned_points: float
    maximum_points: float
    answered_questions: int
    total_questions: int
    assessment_status: str
    readiness_category: str
    result_summary: str
    scoring_formula_explanation: str
    strengths: List[str]
    improvement_areas: List[str]
    skill_results: List[SkillScoreBreakdownItem]
    question_results: List[QuestionResultItem]
    limitations_note: str


class RoleSkillReadinessItem(BaseModel):
    skill_id: str
    skill_name: str
    skill_category: str
    role_weight: float
    expected_level: float
    current_score: Optional[float]
    gap: Optional[float]
    assessment_status: str  # "Assessed" | "Not Assessed"
    status_label: str  # "Meets Target" | "Needs Improvement" | "Not Assessed"
    evidence_summary: str


class RecommendationResponse(BaseModel):
    id: str
    skill_id: str
    skill_name: str
    learning_activity_id: str
    activity_title: str
    activity_description: str
    activity_type: str
    resource_url: Optional[str]
    estimated_effort: str
    effort_hours: float
    reason: str
    evidence_summary: str
    priority: str
    status: str
    is_ai_enhanced: bool
    ai_note: Optional[str]
    created_at: str
    completed_at: Optional[str]


class UpdateRecommendationRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|in_progress|completed|dismissed)$")


class AttemptComparisonResponse(BaseModel):
    assessment_id: str
    assessment_title: str
    earlier_attempt_id: str
    earlier_version: str
    earlier_submitted_at: str
    earlier_score: Optional[float]
    later_attempt_id: str
    later_version: str
    later_submitted_at: str
    later_score: Optional[float]
    comparable: bool
    score_delta: Optional[float]
    comparison_note: str
    skill_deltas: List[Dict[str, Any]]


class DashboardResponse(BaseModel):
    user_id: str
    display_name: str
    has_profile: bool
    has_completed_assessments: bool
    profile: Optional[StudentProfileResponse]
    target_role: Optional[JobRoleDetailResponse]
    readiness_status: str
    readiness_category: str
    overall_role_readiness_score: Optional[float]
    assessed_area_weighted_score: Optional[float]
    assessed_weight_coverage_percent: float
    assessed_skills_count: int
    total_role_skills_count: int
    incomplete_evidence_explanation: str
    scoring_methodology_note: str
    role_skill_readiness: List[RoleSkillReadinessItem]
    recent_attempts: List[Dict[str, Any]]
    outstanding_recommendations: List[RecommendationResponse]
    completed_activities_count: int
    next_suggested_action: Dict[str, str]
    disclaimer: str


class RecordPracticeSessionRequest(BaseModel):
    skill_id: str = Field(..., min_length=2, max_length=64)
    duration_minutes: int = Field(..., ge=5, le=480)
    notes: str = Field(..., min_length=3, max_length=300)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, v: str) -> str:
        return sanitize_text(v, max_length=300)


class ProgressResponse(BaseModel):
    user_id: str
    total_attempts_submitted: int
    completed_recommendations_count: int
    pending_recommendations_count: int
    practice_sessions_logged: int
    attempt_history: List[Dict[str, Any]]
    skill_progress_summary: List[Dict[str, Any]]
    attempt_comparisons: List[AttemptComparisonResponse]
    progress_events: List[Dict[str, Any]]
    mastery_note: str
