from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import (
    AI_PROVIDER_ENABLED,
    APP_NAME,
    APP_VERSION,
    QUESTION_BANK_VERSION,
    SCORING_MODEL_VERSION,
)
from backend.app.core.database import get_db
from backend.app.core.security import (
    create_access_token,
    hash_password,
    sanitize_text,
    verify_access_token,
    verify_password,
)
from backend.app.models.entities import Skill, User
from backend.app.schemas.analysis import AnalyzeRequest, AnalysisResponse, ModelStatusResponse
from backend.app.schemas.placement import (
    AssessmentDetailResponse,
    AssessmentSummaryResponse,
    AttemptResultResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    DashboardResponse,
    JobRoleDetailResponse,
    JobRoleSummaryResponse,
    ProgressResponse,
    RecommendationResponse,
    RecordPracticeSessionRequest,
    SkillResponse,
    StartAttemptRequest,
    StartAttemptResponse,
    StudentProfileRequest,
    StudentProfileResponse,
    SubmitAttemptRequest,
    UpdateRecommendationRequest,
)
from backend.app.services.model_service import analyze_with_available_model, get_model_status
from backend.app.services.placement_service import (
    delete_student_account_data,
    get_assessment_public_detail,
    get_attempt_results,
    get_role_detail,
    get_student_dashboard,
    get_student_profile,
    get_student_progress,
    list_active_assessments,
    list_active_roles,
    list_active_skills,
    list_student_recommendations,
    record_progress_event,
    start_assessment_attempt,
    submit_assessment_attempt,
    sync_student_recommendations,
    update_recommendation_status,
    upsert_student_profile,
)

router = APIRouter(prefix="/api/v1", tags=["Smart Placement Readiness Analyser"])


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_student_id: Optional[str] = Header(default=None),
) -> User:
    """
    Resolve and authenticate the current student user.
    1. If Authorization: Bearer <token> is provided, verify cryptographic signature and expiry.
    2. Else if X-Student-ID header is provided, isolate session to that student ID.
    3. Else use or initialize the local default student session.
    """
    if authorization:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            )
        token = authorization.split(" ", 1)[1].strip()
        user_id = verify_access_token(token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token.",
            )
        user = db.query(User).filter(User.id == user_id).one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account associated with this token no longer exists.",
            )
        return user

    if x_student_id:
        cleaned_id = sanitize_text(x_student_id, max_length=64)
        if not cleaned_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Student-ID header.",
            )
        user = db.query(User).filter(User.id == cleaned_id).one_or_none()
        if user is None:
            user = User(
                id=cleaned_id,
                display_name=f"Student ({cleaned_id})",
                login_identifier=f"{cleaned_id}@local.student",
                password_hash=hash_password(f"local-{cleaned_id}-pass"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    default_id = "student-default"
    user = db.query(User).filter(User.id == default_id).one_or_none()
    if user is None:
        user = User(
            id=default_id,
            display_name="Student",
            login_identifier="student@local.app",
            password_hash=hash_password("default-local-password"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Report system health and version metadata without exposing secrets (TC-34)."""
    return {
        "status": "ok",
        "service": APP_NAME,
        "version": APP_VERSION,
        "scoring_model_version": SCORING_MODEL_VERSION,
        "question_bank_version": QUESTION_BANK_VERSION,
        "ai_enrichment_enabled": AI_PROVIDER_ENABLED,
    }


@router.get("/model/status", response_model=ModelStatusResponse)
def get_analysis_model_status() -> Dict[str, Any]:
    status_payload = get_model_status()
    return {
        "model_loaded": status_payload.model_loaded,
        "model_version": status_payload.model_version,
        "feature_schema_version": status_payload.feature_schema_version,
        "fallback_mode_active": status_payload.fallback_mode_active,
        "available_evaluation_metadata": status_payload.available_evaluation_metadata,
        "is_compatible": status_payload.is_compatible,
    }


@router.post("/analyze", response_model=AnalysisResponse)
def analyze_url(payload: AnalyzeRequest) -> Dict[str, Any]:
    result = analyze_with_available_model(payload.url)
    return result


@router.post("/auth/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_student(payload: AuthRegisterRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    existing = db.query(User).filter(User.login_identifier == payload.login_identifier).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this login identifier already exists.",
        )
    user = User(
        id=f"usr-{uuid.uuid4().hex[:12]}",
        display_name=payload.display_name,
        login_identifier=payload.login_identifier,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return AuthTokenResponse(
        access_token=token,
        user_id=user.id,
        display_name=user.display_name,
        login_identifier=user.login_identifier,
    )


@router.post("/auth/login", response_model=AuthTokenResponse)
def login_student(payload: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    ident = payload.login_identifier.strip().lower()
    user = db.query(User).filter(User.login_identifier == ident).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login identifier or password.",
        )
    token = create_access_token(user.id)
    return AuthTokenResponse(
        access_token=token,
        user_id=user.id,
        display_name=user.display_name,
        login_identifier=user.login_identifier,
    )


@router.get("/roles", response_model=List[JobRoleSummaryResponse])
def get_roles(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return list_active_roles(db)


@router.get("/roles/{role_id}", response_model=JobRoleDetailResponse)
def get_role(role_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return get_role_detail(db, role_id)


@router.get("/skills", response_model=List[SkillResponse])
def get_skills(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return list_active_skills(db)


@router.post("/profile", response_model=StudentProfileResponse)
def create_or_update_profile(
    payload: StudentProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    result = upsert_student_profile(db, current_user, payload)
    sync_student_recommendations(db, current_user)
    return result


@router.get("/profile", response_model=StudentProfileResponse)
def read_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_student_profile(db, current_user)


@router.delete("/profile")
def delete_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    return delete_student_account_data(db, current_user)


@router.get("/assessments", response_model=List[AssessmentSummaryResponse])
def get_assessments(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    return list_active_assessments(db)


@router.get("/assessments/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment(assessment_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    return get_assessment_public_detail(db, assessment_id)


@router.post(
    "/assessments/{assessment_id}/attempts",
    response_model=StartAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_attempt(
    assessment_id: str,
    payload: Optional[StartAttemptRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    expected_version = payload.expected_version if payload else None
    return start_assessment_attempt(db, current_user, assessment_id, expected_version=expected_version)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
def submit_attempt(
    attempt_id: str,
    payload: SubmitAttemptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return submit_assessment_attempt(db, current_user, attempt_id, payload)


@router.get("/attempts/{attempt_id}/results", response_model=AttemptResultResponse)
def read_attempt_results(
    attempt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_attempt_results(db, current_user, attempt_id)


@router.get("/dashboard", response_model=DashboardResponse)
def read_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_student_dashboard(db, current_user)


@router.get("/recommendations", response_model=List[RecommendationResponse])
def read_recommendations(
    refresh: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    if refresh:
        return sync_student_recommendations(db, current_user)
    recs = list_student_recommendations(db, current_user)
    if not recs:
        return sync_student_recommendations(db, current_user)
    return recs


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def patch_recommendation(
    recommendation_id: str,
    payload: UpdateRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return update_recommendation_status(db, current_user, recommendation_id, payload.status)


@router.get("/progress", response_model=ProgressResponse)
def read_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return get_student_progress(db, current_user)


@router.post("/progress/practice", status_code=status.HTTP_201_CREATED)
def log_practice_session(
    payload: RecordPracticeSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    skill = db.query(Skill).filter(Skill.id == payload.skill_id, Skill.active.is_(True)).one_or_none()
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{payload.skill_id}' was not found.",
        )
    record_progress_event(
        db,
        user_id=current_user.id,
        event_type="practice_session_logged",
        reference_id=skill.id,
        metadata={
            "skill_name": skill.name,
            "duration_minutes": payload.duration_minutes,
            "notes": payload.notes,
        },
    )
    db.commit()
    return {
        "status": "recorded",
        "skill_id": skill.id,
        "skill_name": skill.name,
        "duration_minutes": payload.duration_minutes,
        "note": "Practice session logged. Retake an assessment to verify skill score improvement.",
    }
