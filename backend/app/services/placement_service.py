from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.assessments.engine import (
    calculate_role_readiness,
    categorize_readiness,
    compare_attempts_logic,
    grade_question,
    validate_question_configuration,
    validate_role_weights,
)
from backend.app.core.config import DISCLAIMER_TEXT, SCORING_MODEL_VERSION
from backend.app.models.entities import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AttemptAnswer,
    JobRole,
    LearningActivity,
    ProgressEvent,
    Question,
    QuestionOption,
    RoleSkillRequirement,
    Skill,
    SkillAssessmentResult,
    StudentProfile,
    StudentRecommendation,
    User,
)
from backend.app.recommendations.engine import build_rule_based_recommendations
from backend.app.schemas.placement import StudentProfileRequest, SubmitAttemptRequest


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def record_progress_event(
    db: Session,
    user_id: str,
    event_type: str,
    reference_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    event = ProgressEvent(
        id=f"evt-{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
        event_timestamp=_utc_now(),
        safe_metadata_json=json.dumps(metadata or {}),
    )
    db.add(event)


def list_active_roles(db: Session) -> List[Dict[str, Any]]:
    roles = db.query(JobRole).filter(JobRole.active.is_(True)).order_by(JobRole.name.asc()).all()
    results: List[Dict[str, Any]] = []
    for role in roles:
        req_count = db.query(RoleSkillRequirement).filter(RoleSkillRequirement.role_id == role.id).count()
        results.append(
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "version": role.version,
                "active": role.active,
                "skill_count": req_count,
            }
        )
    return results


def get_role_detail(db: Session, role_id: str) -> Dict[str, Any]:
    role = db.query(JobRole).filter(JobRole.id == role_id).one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job role '{role_id}' was not found.",
        )
    if not role.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job role '{role_id}' ({role.name}) is currently inactive and cannot be selected.",
        )

    reqs = (
        db.query(RoleSkillRequirement, Skill)
        .join(Skill, RoleSkillRequirement.skill_id == Skill.id)
        .filter(RoleSkillRequirement.role_id == role.id)
        .order_by(RoleSkillRequirement.weight.desc())
        .all()
    )
    weights = [float(r.weight) for r, _ in reqs]
    validate_role_weights(weights)

    skills_list = [
        {
            "skill_id": s.id,
            "skill_name": s.name,
            "skill_category": s.category,
            "skill_description": s.description,
            "weight": float(r.weight),
            "expected_level": float(r.expected_level),
            "rationale": r.rationale,
            "version": r.version,
        }
        for r, s in reqs
    ]

    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "version": role.version,
        "active": role.active,
        "total_weight": round(sum(weights), 4),
        "skills": skills_list,
        "disclaimer": (
            "Role skill profiles represent typical industry expectations for educational benchmarking. "
            "Individual employers may weigh skills differently."
        ),
    }


def list_active_skills(db: Session) -> List[Dict[str, Any]]:
    skills = db.query(Skill).filter(Skill.active.is_(True)).order_by(Skill.category.asc(), Skill.name.asc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "category": s.category,
            "description": s.description,
            "active": s.active,
        }
        for s in skills
    ]


def upsert_student_profile(db: Session, user: User, payload: StudentProfileRequest) -> Dict[str, Any]:
    # Validate target role exists and is active (TC-03, TC-04)
    role_detail = get_role_detail(db, payload.target_role_id)

    if payload.display_name:
        user.display_name = payload.display_name
        user.updated_at = _utc_now()

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).one_or_none()
    is_new = profile is None
    if profile is None:
        profile = StudentProfile(
            id=f"prof-{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            education_level=payload.education_level,
            target_role_id=payload.target_role_id,
            current_skills_json=json.dumps(payload.current_skills),
            preferred_languages_json=json.dumps(payload.preferred_languages),
            preparation_goal=payload.preparation_goal,
            available_preparation_time=payload.available_preparation_time,
        )
        db.add(profile)
    else:
        profile.education_level = payload.education_level
        profile.target_role_id = payload.target_role_id
        profile.current_skills_json = json.dumps(payload.current_skills)
        profile.preferred_languages_json = json.dumps(payload.preferred_languages)
        profile.preparation_goal = payload.preparation_goal
        profile.available_preparation_time = payload.available_preparation_time
        profile.updated_at = _utc_now()

    record_progress_event(
        db,
        user_id=user.id,
        event_type="profile_created" if is_new else "profile_updated",
        reference_id=profile.id,
        metadata={"target_role_id": payload.target_role_id, "available_hours": payload.available_preparation_time},
    )
    db.commit()
    db.refresh(profile)

    return format_profile_response(user, profile, role_detail["name"])


def get_student_profile(db: Session, user: User) -> Dict[str, Any]:
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile has not been created yet.",
        )
    role = db.query(JobRole).filter(JobRole.id == profile.target_role_id).one_or_none()
    role_name = role.name if role else profile.target_role_id
    return format_profile_response(user, profile, role_name)


def format_profile_response(user: User, profile: StudentProfile, role_name: str) -> Dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": user.id,
        "display_name": user.display_name,
        "education_level": profile.education_level,
        "target_role_id": profile.target_role_id,
        "target_role_name": role_name,
        "current_skills": json.loads(profile.current_skills_json or "[]"),
        "preferred_languages": json.loads(profile.preferred_languages_json or "[]"),
        "preparation_goal": profile.preparation_goal,
        "available_preparation_time": profile.available_preparation_time,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


def list_active_assessments(db: Session) -> List[Dict[str, Any]]:
    assessments = db.query(Assessment).filter(Assessment.status == "active").all()
    output: List[Dict[str, Any]] = []
    for a in assessments:
        questions = (
            db.query(Question, Skill)
            .join(Skill, Question.skill_id == Skill.id)
            .filter(Question.assessment_id == a.id, Question.active.is_(True))
            .all()
        )
        total_points = sum(float(q.score_value) for q, _ in questions)
        covered_skills = sorted({s.name for _, s in questions})
        output.append(
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "instructions": a.instructions,
                "assessment_type": a.assessment_type,
                "skill_area": a.skill_area,
                "time_limit_minutes": a.time_limit_minutes,
                "version": a.version,
                "status": a.status,
                "question_count": len(questions),
                "total_points": round(total_points, 2),
                "covered_skills": covered_skills,
            }
        )
    return output


def get_assessment_public_detail(db: Session, assessment_id: str) -> Dict[str, Any]:
    """
    Return assessment metadata and active questions WITHOUT exposing correct answers or explanations (TC-06, TC-07, TC-08).
    """
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' was not found.",
        )
    if assessment.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment '{assessment_id}' is inactive and not available for attempts.",
        )

    rows = (
        db.query(Question, Skill)
        .join(Skill, Question.skill_id == Skill.id)
        .filter(Question.assessment_id == assessment.id, Question.active.is_(True))
        .order_by(Question.id.asc())
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment '{assessment_id}' has no active questions configured.",
        )

    questions_public: List[Dict[str, Any]] = []
    total_points = 0.0
    for q, s in rows:
        opts = (
            db.query(QuestionOption)
            .filter(QuestionOption.question_id == q.id)
            .order_by(QuestionOption.option_identifier.asc())
            .all()
        )
        validate_question_configuration(
            question_id=q.id,
            question_type=q.question_type,
            score_value=float(q.score_value),
            correct_answer_raw=q.correct_answer_json,
            option_identifiers=[o.option_identifier for o in opts],
        )
        total_points += float(q.score_value)
        questions_public.append(
            {
                "id": q.id,
                "skill_id": q.skill_id,
                "skill_name": s.name,
                "topic": q.topic,
                "skill_area": q.skill_area,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "difficulty": q.difficulty,
                "score_value": float(q.score_value),
                "version": q.version,
                "options": [
                    {
                        "option_identifier": o.option_identifier,
                        "option_text": o.option_text,
                    }
                    for o in opts
                ],
            }
        )

    return {
        "id": assessment.id,
        "title": assessment.title,
        "description": assessment.description,
        "instructions": assessment.instructions,
        "assessment_type": assessment.assessment_type,
        "skill_area": assessment.skill_area,
        "time_limit_minutes": assessment.time_limit_minutes,
        "version": assessment.version,
        "status": assessment.status,
        "total_points": round(total_points, 2),
        "questions": questions_public,
    }


def start_assessment_attempt(
    db: Session,
    user: User,
    assessment_id: str,
    expected_version: Optional[str] = None,
) -> Dict[str, Any]:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).one_or_none()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment '{assessment_id}' was not found.",
        )
    if assessment.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment '{assessment_id}' is inactive.",
        )
    if expected_version is not None and expected_version != assessment.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Requested assessment version '{expected_version}' does not match "
                f"active assessment version '{assessment.version}'."
            ),
        )

    attempt = AssessmentAttempt(
        id=f"att-{uuid.uuid4().hex[:12]}",
        user_id=user.id,
        assessment_id=assessment.id,
        assessment_version=assessment.version,
        started_at=_utc_now(),
        status="in_progress",
    )
    db.add(attempt)
    record_progress_event(
        db,
        user_id=user.id,
        event_type="attempt_started",
        reference_id=attempt.id,
        metadata={"assessment_id": assessment.id, "version": assessment.version},
    )
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "assessment_version": attempt.assessment_version,
        "started_at": attempt.started_at.isoformat(),
        "status": attempt.status,
    }


def submit_assessment_attempt(
    db: Session,
    user: User,
    attempt_id: str,
    payload: SubmitAttemptRequest,
) -> Dict[str, Any]:
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).one_or_none()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment attempt '{attempt_id}' was not found.",
        )
    # Enforce cross-user authorization (TC-31)
    if attempt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access or submit another student's assessment attempt.",
        )
    # Prevent duplicate submission from corrupting first result (TC-14)
    if attempt.status == "submitted":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment attempt has already been submitted and cannot be modified. Start a new attempt to retake.",
        )

    active_questions = (
        db.query(Question, Skill)
        .join(Skill, Question.skill_id == Skill.id)
        .filter(Question.assessment_id == attempt.assessment_id, Question.active.is_(True))
        .order_by(Question.id.asc())
        .all()
    )
    question_map = {q.id: (q, s) for q, s in active_questions}

    # Check for unknown/inactive question IDs in submission (TC-08, TC-13)
    submitted_map: Dict[str, Any] = {}
    for item in payload.answers:
        if item.question_id not in question_map:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Question '{item.question_id}' is not an active question in this assessment.",
            )
        if item.question_id in submitted_map:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate answer submitted for question '{item.question_id}'.",
            )
        submitted_map[item.question_id] = item.answer_value

    if payload.require_all_questions and len(submitted_map) < len(question_map):
        missing_q = sorted(set(question_map.keys()) - set(submitted_map.keys()))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"All questions are required when require_all_questions is enabled. Missing: {', '.join(missing_q)}",
        )

    total_earned = 0.0
    total_max = 0.0
    answered_count = 0
    skill_buckets: Dict[str, Dict[str, Any]] = {}

    for q, s in active_questions:
        opts = (
            db.query(QuestionOption)
            .filter(QuestionOption.question_id == q.id)
            .order_by(QuestionOption.option_identifier.asc())
            .all()
        )
        valid_opt_ids = [o.option_identifier for o in opts]
        raw_ans = submitted_map.get(q.id)
        is_answered = raw_ans is not None and raw_ans != "" and raw_ans != []
        if is_answered:
            answered_count += 1

        try:
            awarded, is_correct, feedback = grade_question(
                question_id=q.id,
                question_type=q.question_type,
                score_value=float(q.score_value),
                correct_answer_json=q.correct_answer_json,
                valid_option_ids=valid_opt_ids,
                submitted_answer=raw_ans,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        q_max = float(q.score_value)
        total_earned += awarded
        total_max += q_max

        ans_record = AttemptAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            answer_value_json=json.dumps(raw_ans),
            awarded_score=awarded,
            maximum_score=q_max,
            is_correct=is_correct,
            feedback=feedback,
        )
        db.add(ans_record)

        bucket = skill_buckets.setdefault(
            s.id,
            {
                "skill_id": s.id,
                "skill_name": s.name,
                "earned": 0.0,
                "max": 0.0,
                "questions": 0,
            },
        )
        bucket["earned"] += awarded
        bucket["max"] += q_max
        bucket["questions"] += 1

    overall_score = round((total_earned / total_max) * 100.0, 2) if total_max > 0 else 0.0
    readiness_cat = categorize_readiness(overall_score, is_complete_evidence=True)
    assessment = db.query(Assessment).filter(Assessment.id == attempt.assessment_id).one()

    result_summary = (
        f"Completed {assessment.title} (v{attempt.assessment_version}): earned "
        f"{total_earned:.2f} / {total_max:.2f} points ({overall_score:.2f}%). "
        f"Category on this assessment: {readiness_cat}."
    )

    result_record = AssessmentResult(
        id=f"res-{uuid.uuid4().hex[:12]}",
        attempt_id=attempt.id,
        overall_score=overall_score,
        earned_points=round(total_earned, 2),
        maximum_points=round(total_max, 2),
        assessment_status="Completed",
        readiness_category=readiness_cat,
        result_summary=result_summary,
        limitations_note=DISCLAIMER_TEXT,
        scoring_version=SCORING_MODEL_VERSION,
        created_at=_utc_now(),
    )
    db.add(result_record)
    db.flush()

    for s_id, b in skill_buckets.items():
        s_score = round((b["earned"] / b["max"]) * 100.0, 2) if b["max"] > 0 else 0.0
        ev_summary = (
            f"Earned {b['earned']:.2f}/{b['max']:.2f} pts ({s_score:.1f}%) across "
            f"{b['questions']} question(s) in {assessment.title}."
        )
        db.add(
            SkillAssessmentResult(
                assessment_result_id=result_record.id,
                skill_id=s_id,
                score=s_score,
                earned_points=round(b["earned"], 2),
                maximum_points=round(b["max"], 2),
                evidence_summary=ev_summary,
                assessment_status="Assessed",
            )
        )

    attempt.submitted_at = _utc_now()
    attempt.status = "submitted"

    record_progress_event(
        db,
        user_id=user.id,
        event_type="attempt_submitted",
        reference_id=attempt.id,
        metadata={
            "assessment_id": attempt.assessment_id,
            "overall_score": overall_score,
            "answered_questions": answered_count,
            "total_questions": len(active_questions),
        },
    )
    db.commit()

    # Automatically refresh student recommendations based on new evidence
    sync_student_recommendations(db, user)

    return get_attempt_results(db, user, attempt.id)


def get_attempt_results(db: Session, user: User, attempt_id: str) -> Dict[str, Any]:
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).one_or_none()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment attempt '{attempt_id}' was not found.",
        )
    if attempt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another student's assessment results.",
        )
    if attempt.status != "submitted" or attempt.result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment attempt has not been submitted yet.",
        )

    res = attempt.result
    assessment = db.query(Assessment).filter(Assessment.id == attempt.assessment_id).one()

    skill_rows = (
        db.query(SkillAssessmentResult, Skill)
        .join(Skill, SkillAssessmentResult.skill_id == Skill.id)
        .filter(SkillAssessmentResult.assessment_result_id == res.id)
        .all()
    )
    skill_results: List[Dict[str, Any]] = []
    strengths: List[str] = []
    improvement_areas: List[str] = []

    for sr, skill in skill_rows:
        score_val = float(sr.score) if sr.score is not None else 0.0
        skill_results.append(
            {
                "skill_id": skill.id,
                "skill_name": skill.name,
                "score": score_val,
                "earned_points": float(sr.earned_points),
                "maximum_points": float(sr.maximum_points),
                "assessment_status": sr.assessment_status,
                "evidence_summary": sr.evidence_summary,
            }
        )
        if score_val >= 70.0:
            strengths.append(f"{skill.name} ({score_val:.1f}% — meets or exceeds 70% benchmark)")
        else:
            improvement_areas.append(f"{skill.name} ({score_val:.1f}% — below 70% benchmark; targeted practice recommended)")

    ans_rows = (
        db.query(AttemptAnswer, Question, Skill)
        .join(Question, AttemptAnswer.question_id == Question.id)
        .join(Skill, Question.skill_id == Skill.id)
        .filter(AttemptAnswer.attempt_id == attempt.id)
        .order_by(Question.id.asc())
        .all()
    )

    question_results: List[Dict[str, Any]] = []
    answered_questions = 0
    for ans, q, skill in ans_rows:
        parsed_ans = json.loads(ans.answer_value_json)
        if parsed_ans is not None and parsed_ans != "" and parsed_ans != []:
            answered_questions += 1
        question_results.append(
            {
                "question_id": q.id,
                "topic": q.topic,
                "skill_id": skill.id,
                "skill_name": skill.name,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "submitted_answer": parsed_ans,
                "awarded_score": float(ans.awarded_score),
                "maximum_score": float(ans.maximum_score),
                "is_correct": bool(ans.is_correct),
                "feedback": ans.feedback or "",
                "explanation": q.explanation,
            }
        )

    return {
        "result_id": res.id,
        "attempt_id": attempt.id,
        "assessment_id": assessment.id,
        "assessment_title": assessment.title,
        "assessment_version": attempt.assessment_version,
        "scoring_version": res.scoring_version,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else res.created_at.isoformat(),
        "overall_score": float(res.overall_score) if res.overall_score is not None else None,
        "earned_points": float(res.earned_points),
        "maximum_points": float(res.maximum_points),
        "answered_questions": answered_questions,
        "total_questions": len(question_results),
        "assessment_status": res.assessment_status,
        "readiness_category": res.readiness_category,
        "result_summary": res.result_summary,
        "scoring_formula_explanation": (
            "Area Score = (Earned Points / Maximum Available Points) × 100. "
            "Multiple-select questions award proportional partial credit when only correct options are chosen."
        ),
        "strengths": strengths,
        "improvement_areas": improvement_areas,
        "skill_results": skill_results,
        "question_results": question_results,
        "limitations_note": res.limitations_note,
    }


def get_latest_skill_scores_for_user(db: Session, user_id: str) -> Dict[str, Dict[str, Any]]:
    """Return the most recent assessed score for each skill across the student's submitted attempts."""
    attempts = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.user_id == user_id, AssessmentAttempt.status == "submitted")
        .order_by(AssessmentAttempt.submitted_at.asc())
        .all()
    )
    latest_by_skill: Dict[str, Dict[str, Any]] = {}
    for att in attempts:
        if not att.result:
            continue
        s_rows = (
            db.query(SkillAssessmentResult, Skill)
            .join(Skill, SkillAssessmentResult.skill_id == Skill.id)
            .filter(SkillAssessmentResult.assessment_result_id == att.result.id)
            .all()
        )
        for sr, skill in s_rows:
            latest_by_skill[skill.id] = {
                "skill_id": skill.id,
                "skill_name": skill.name,
                "score": float(sr.score) if sr.score is not None else None,
                "earned_points": float(sr.earned_points),
                "maximum_points": float(sr.maximum_points),
                "evidence_summary": sr.evidence_summary,
                "assessment_id": att.assessment_id,
                "attempt_id": att.id,
                "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
            }
    return latest_by_skill


def sync_student_recommendations(
    db: Session,
    user: User,
    ai_provider_callable: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate or update personalized recommendations based on the student's profile and latest skill evidence.
    """
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).one_or_none()
    if profile is None:
        return []

    role = db.query(JobRole).filter(JobRole.id == profile.target_role_id).one_or_none()
    if role is None or not role.active:
        return []

    reqs = (
        db.query(RoleSkillRequirement, Skill)
        .join(Skill, RoleSkillRequirement.skill_id == Skill.id)
        .filter(RoleSkillRequirement.role_id == role.id)
        .all()
    )
    role_requirements = [
        {
            "skill_id": s.id,
            "skill_name": s.name,
            "skill_category": s.category,
            "weight": float(r.weight),
            "expected_level": float(r.expected_level),
        }
        for r, s in reqs
    ]

    latest_scores = get_latest_skill_scores_for_user(db, user.id)

    all_activities = db.query(LearningActivity).filter(LearningActivity.status == "active").all()
    activities_by_skill: Dict[str, List[Dict[str, Any]]] = {}
    for act in all_activities:
        activities_by_skill.setdefault(act.skill_id, []).append(
            {
                "id": act.id,
                "skill_id": act.skill_id,
                "title": act.title,
                "description": act.description,
                "activity_type": act.activity_type,
                "resource_url": act.resource_url,
                "estimated_effort": act.estimated_effort,
                "effort_hours": float(act.effort_hours),
            }
        )

    existing_recs = db.query(StudentRecommendation).filter(StudentRecommendation.user_id == user.id).all()
    completed_activity_ids: Set[str] = {r.learning_activity_id for r in existing_recs if r.status == "completed"}

    # Remove stale pending recommendations that were not started yet so updated scores refresh reasons cleanly
    for rec in list(existing_recs):
        if rec.status == "pending":
            db.delete(rec)
    db.flush()

    remaining_recs = db.query(StudentRecommendation).filter(StudentRecommendation.user_id == user.id).all()
    existing_active_ids: Set[str] = {
        r.learning_activity_id for r in remaining_recs if r.status in {"pending", "in_progress"}
    }

    generated = build_rule_based_recommendations(
        role_name=role.name,
        available_prep_hours=profile.available_preparation_time,
        role_requirements=role_requirements,
        latest_skill_scores=latest_scores,
        activities_by_skill=activities_by_skill,
        completed_activity_ids=completed_activity_ids,
        existing_active_activity_ids=existing_active_ids,
        ai_provider_callable=ai_provider_callable,
    )

    for item in generated:
        db.add(
            StudentRecommendation(
                id=f"rec-{uuid.uuid4().hex[:12]}",
                user_id=user.id,
                skill_id=item["skill_id"],
                learning_activity_id=item["learning_activity_id"],
                reason=item["reason"],
                evidence_summary=item["evidence_summary"],
                priority=item["priority"],
                status="pending",
                is_ai_enhanced=item["is_ai_enhanced"],
                ai_note=item["ai_note"],
                created_at=_utc_now(),
            )
        )
    db.commit()
    return list_student_recommendations(db, user)


def list_student_recommendations(db: Session, user: User) -> List[Dict[str, Any]]:
    rows = (
        db.query(StudentRecommendation, Skill, LearningActivity)
        .join(Skill, StudentRecommendation.skill_id == Skill.id)
        .join(LearningActivity, StudentRecommendation.learning_activity_id == LearningActivity.id)
        .filter(StudentRecommendation.user_id == user.id)
        .order_by(StudentRecommendation.created_at.desc())
        .all()
    )
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    status_rank = {"in_progress": 0, "pending": 1, "completed": 2, "dismissed": 3}

    formatted = [
        {
            "id": rec.id,
            "skill_id": skill.id,
            "skill_name": skill.name,
            "learning_activity_id": act.id,
            "activity_title": act.title,
            "activity_description": act.description,
            "activity_type": act.activity_type,
            "resource_url": act.resource_url,
            "estimated_effort": act.estimated_effort,
            "effort_hours": float(act.effort_hours),
            "reason": rec.reason,
            "evidence_summary": rec.evidence_summary,
            "priority": rec.priority,
            "status": rec.status,
            "is_ai_enhanced": bool(rec.is_ai_enhanced),
            "ai_note": rec.ai_note,
            "created_at": rec.created_at.isoformat(),
            "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
            "_sort": (status_rank.get(rec.status, 9), priority_rank.get(rec.priority, 9)),
        }
        for rec, skill, act in rows
    ]
    formatted.sort(key=lambda r: r["_sort"])
    for item in formatted:
        item.pop("_sort", None)
    return formatted


def update_recommendation_status(
    db: Session,
    user: User,
    recommendation_id: str,
    new_status: str,
) -> Dict[str, Any]:
    rec = db.query(StudentRecommendation).filter(StudentRecommendation.id == recommendation_id).one_or_none()
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{recommendation_id}' was not found.",
        )
    if rec.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify another student's recommendation.",
        )

    rec.status = new_status
    if new_status == "completed":
        rec.completed_at = _utc_now()
    elif new_status in {"pending", "in_progress"}:
        rec.completed_at = None

    record_progress_event(
        db,
        user_id=user.id,
        event_type=f"recommendation_{new_status}",
        reference_id=rec.id,
        metadata={"skill_id": rec.skill_id, "learning_activity_id": rec.learning_activity_id},
    )
    db.commit()

    all_recs = list_student_recommendations(db, user)
    for item in all_recs:
        if item["id"] == recommendation_id:
            return item
    raise HTTPException(status_code=404, detail="Recommendation not found after update.")


def get_student_dashboard(db: Session, user: User) -> Dict[str, Any]:
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).one_or_none()
    attempts = (
        db.query(AssessmentAttempt, Assessment)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .filter(AssessmentAttempt.user_id == user.id, AssessmentAttempt.status == "submitted")
        .order_by(AssessmentAttempt.submitted_at.desc())
        .all()
    )

    if profile is None:
        return {
            "user_id": user.id,
            "display_name": user.display_name,
            "has_profile": False,
            "has_completed_assessments": False,
            "profile": None,
            "target_role": None,
            "readiness_status": "Profile Required",
            "readiness_category": "Insufficient Assessment Evidence",
            "overall_role_readiness_score": None,
            "assessed_area_weighted_score": None,
            "assessed_weight_coverage_percent": 0.0,
            "assessed_skills_count": 0,
            "total_role_skills_count": 0,
            "incomplete_evidence_explanation": (
                "No student profile or assessment evidence exists yet. Create your profile and select a "
                "target job role to view required skills and start your first assessment."
            ),
            "scoring_methodology_note": (
                "Overall role score is calculated as the weighted sum of role skill scores only after all "
                "required skills for the selected role have been assessed."
            ),
            "role_skill_readiness": [],
            "recent_attempts": [],
            "outstanding_recommendations": [],
            "completed_activities_count": 0,
            "next_suggested_action": {
                "title": "Create Your Student Profile",
                "description": "Select your target job role, current skills, and weekly preparation availability.",
                "action_target": "profile",
            },
            "disclaimer": DISCLAIMER_TEXT,
        }

    role_detail = get_role_detail(db, profile.target_role_id)
    profile_resp = format_profile_response(user, profile, role_detail["name"])
    latest_skill_scores = get_latest_skill_scores_for_user(db, user.id)
    readiness = calculate_role_readiness(role_detail["skills"], latest_skill_scores)

    recommendations = list_student_recommendations(db, user)
    if not recommendations:
        recommendations = sync_student_recommendations(db, user)

    outstanding_recs = [r for r in recommendations if r["status"] in {"pending", "in_progress"}]
    completed_count = sum(1 for r in recommendations if r["status"] == "completed")

    recent_attempts_list = [
        {
            "attempt_id": att.id,
            "assessment_id": assess.id,
            "assessment_title": assess.title,
            "assessment_version": att.assessment_version,
            "submitted_at": att.submitted_at.isoformat() if att.submitted_at else None,
            "overall_score": float(att.result.overall_score) if (att.result and att.result.overall_score is not None) else None,
            "readiness_category": att.result.readiness_category if att.result else "Insufficient Assessment Evidence",
        }
        for att, assess in attempts[:10]
    ]

    if not attempts:
        next_action = {
            "title": "Take Your First Diagnostic Assessment",
            "description": f"Start an assessment in the Assessment Centre to establish baseline skill evidence for {role_detail['name']}.",
            "action_target": "assessments",
        }
    elif readiness["assessed_skills_count"] < readiness["total_role_skills_count"]:
        unassessed = [s["skill_name"] for s in readiness["role_skill_readiness"] if s["assessment_status"] == "Not Assessed"]
        next_action = {
            "title": "Complete Remaining Role Skill Assessments",
            "description": f"You still have unassessed skills for {role_detail['name']}: {', '.join(unassessed[:3])}.",
            "action_target": "assessments",
        }
    elif outstanding_recs:
        top_rec = outstanding_recs[0]
        next_action = {
            "title": f"Work on High-Priority Gap: {top_rec['skill_name']}",
            "description": f"Recommended activity: {top_rec['activity_title']} ({top_rec['estimated_effort']}).",
            "action_target": "learning-plan",
        }
    else:
        next_action = {
            "title": "Retake Assessments to Measure Progress",
            "description": "Review your progress timeline and retake assessments to verify skill mastery over time.",
            "action_target": "progress",
        }

    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "has_profile": True,
        "has_completed_assessments": len(attempts) > 0,
        "profile": profile_resp,
        "target_role": role_detail,
        "readiness_status": readiness["readiness_status"],
        "readiness_category": readiness["readiness_category"],
        "overall_role_readiness_score": readiness["overall_role_readiness_score"],
        "assessed_area_weighted_score": readiness["assessed_area_weighted_score"],
        "assessed_weight_coverage_percent": readiness["assessed_weight_coverage_percent"],
        "assessed_skills_count": readiness["assessed_skills_count"],
        "total_role_skills_count": readiness["total_role_skills_count"],
        "incomplete_evidence_explanation": readiness["incomplete_evidence_explanation"],
        "scoring_methodology_note": (
            "Area Score = (Points Earned / Maximum Points) × 100. Overall Role Readiness Score = "
            "Sum(Skill Score × Role Weight), computed only when all required role skills have assessment evidence."
        ),
        "role_skill_readiness": readiness["role_skill_readiness"],
        "recent_attempts": recent_attempts_list,
        "outstanding_recommendations": outstanding_recs,
        "completed_activities_count": completed_count,
        "next_suggested_action": next_action,
        "disclaimer": DISCLAIMER_TEXT,
    }


def get_student_progress(db: Session, user: User) -> Dict[str, Any]:
    attempts = (
        db.query(AssessmentAttempt, Assessment)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .filter(AssessmentAttempt.user_id == user.id, AssessmentAttempt.status == "submitted")
        .order_by(AssessmentAttempt.submitted_at.asc())
        .all()
    )

    attempt_history: List[Dict[str, Any]] = []
    attempts_by_assessment: Dict[str, List[Dict[str, Any]]] = {}
    skill_history: Dict[str, List[Dict[str, Any]]] = {}

    for att, assess in attempts:
        if not att.result:
            continue
        s_rows = (
            db.query(SkillAssessmentResult, Skill)
            .join(Skill, SkillAssessmentResult.skill_id == Skill.id)
            .filter(SkillAssessmentResult.assessment_result_id == att.result.id)
            .all()
        )
        s_list = []
        for sr, skill in s_rows:
            s_val = float(sr.score) if sr.score is not None else None
            s_item = {
                "skill_id": skill.id,
                "skill_name": skill.name,
                "score": s_val,
            }
            s_list.append(s_item)
            if s_val is not None:
                skill_history.setdefault(skill.id, []).append(
                    {
                        "skill_id": skill.id,
                        "skill_name": skill.name,
                        "score": s_val,
                        "attempt_id": att.id,
                        "submitted_at": att.submitted_at.isoformat() if att.submitted_at else "",
                        "assessment_version": att.assessment_version,
                    }
                )

        entry = {
            "attempt_id": att.id,
            "assessment_id": assess.id,
            "assessment_title": assess.title,
            "assessment_version": att.assessment_version,
            "scoring_version": att.result.scoring_version,
            "submitted_at": att.submitted_at.isoformat() if att.submitted_at else "",
            "overall_score": float(att.result.overall_score) if att.result.overall_score is not None else None,
            "earned_points": float(att.result.earned_points),
            "maximum_points": float(att.result.maximum_points),
            "readiness_category": att.result.readiness_category,
            "skill_results": s_list,
        }
        attempt_history.append(entry)
        attempts_by_assessment.setdefault(assess.id, []).append(entry)

    comparisons: List[Dict[str, Any]] = []
    for assess_id, att_list in attempts_by_assessment.items():
        if len(att_list) >= 2:
            earlier = att_list[-2]
            later = att_list[-1]
            comparisons.append(
                compare_attempts_logic(
                    assessment_id=assess_id,
                    assessment_title=later["assessment_title"],
                    earlier=earlier,
                    later=later,
                )
            )

    skill_progress_summary: List[Dict[str, Any]] = []
    for s_id, history in skill_history.items():
        first_entry = history[0]
        latest_entry = history[-1]
        delta = round(latest_entry["score"] - first_entry["score"], 2) if len(history) > 1 else 0.0
        skill_progress_summary.append(
            {
                "skill_id": s_id,
                "skill_name": latest_entry["skill_name"],
                "attempts_count": len(history),
                "initial_score": first_entry["score"],
                "latest_score": latest_entry["score"],
                "score_change": delta,
                "trend": "Improved" if delta > 0 else ("Declined" if delta < 0 else "Stable"),
            }
        )

    recs = db.query(StudentRecommendation).filter(StudentRecommendation.user_id == user.id).all()
    completed_recs = sum(1 for r in recs if r.status == "completed")
    pending_recs = sum(1 for r in recs if r.status in {"pending", "in_progress"})

    events = (
        db.query(ProgressEvent)
        .filter(ProgressEvent.user_id == user.id)
        .order_by(ProgressEvent.event_timestamp.desc())
        .limit(50)
        .all()
    )
    practice_sessions = sum(1 for e in events if e.event_type == "practice_session_logged")

    events_list = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "reference_id": e.reference_id,
            "event_timestamp": e.event_timestamp.isoformat(),
            "metadata": json.loads(e.safe_metadata_json or "{}"),
        }
        for e in events
    ]

    return {
        "user_id": user.id,
        "total_attempts_submitted": len(attempt_history),
        "completed_recommendations_count": completed_recs,
        "pending_recommendations_count": pending_recs,
        "practice_sessions_logged": practice_sessions,
        "attempt_history": list(reversed(attempt_history)),
        "skill_progress_summary": skill_progress_summary,
        "attempt_comparisons": comparisons,
        "progress_events": events_list,
        "mastery_note": (
            "Completing a recommended learning activity or logging a practice session records study effort, "
            "not skill mastery. Retake the corresponding assessment to measure verified score changes."
        ),
    }


def delete_student_account_data(db: Session, user: User) -> Dict[str, str]:
    """Delete a student's profile, assessment attempts, recommendations, and account record (TC-35)."""
    user_id = user.id
    db.delete(user)
    db.commit()
    return {
        "status": "deleted",
        "user_id": user_id,
        "detail": "All personal profile data, assessment attempts, recommendations, and progress records for this user have been permanently deleted.",
    }
