from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.assessments.engine import (
    calculate_role_readiness,
    compare_attempts_logic,
    validate_question_configuration,
    validate_role_weights,
)
from backend.app.core.database import Base, get_db
from backend.app.core.security import sanitize_log_data
from backend.app.main import app
from backend.app.recommendations.engine import (
    enrich_with_optional_ai,
    validate_ai_recommendation_payload,
)
from backend.app.repositories.seed_data import seed_reference_data


@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        seed_reference_data(db)
    finally:
        db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================
# PROFILE AND ROLE TESTS (TC-01 to TC-05)
# ============================================================

def test_tc01_create_valid_student_profile(client: TestClient) -> None:
    """TC-01: Create a valid student profile."""
    headers = {"X-Student-ID": "student-tc01"}
    payload = {
        "display_name": "Aarav Sharma",
        "education_level": "B.E. Computer Science (Final Year)",
        "target_role_id": "role-swe",
        "current_skills": ["Python", "SQL", "Git"],
        "preferred_languages": ["Python", "TypeScript"],
        "preparation_goal": "Prepare for software developer campus placements with structured practice.",
        "available_preparation_time": 12,
    }
    resp = client.post("/api/v1/profile", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Aarav Sharma"
    assert data["target_role_id"] == "role-swe"
    assert data["target_role_name"] == "Software Developer"
    assert data["available_preparation_time"] == 12


def test_tc02_reject_invalid_profile_data(client: TestClient) -> None:
    """TC-02: Reject invalid profile data (empty goal, out-of-range hours, XSS payload)."""
    headers = {"X-Student-ID": "student-tc02"}
    invalid_payload = {
        "display_name": "<script>alert(1)</script>",
        "education_level": "B.Tech",
        "target_role_id": "role-swe",
        "current_skills": [],
        "preferred_languages": [],
        "preparation_goal": "ok",  # Too short (< 5 chars)
        "available_preparation_time": 0,  # Must be >= 1
    }
    resp = client.post("/api/v1/profile", json=invalid_payload, headers=headers)
    assert resp.status_code == 422


def test_tc03_select_supported_target_role(client: TestClient) -> None:
    """TC-03: Select a supported target role."""
    roles_resp = client.get("/api/v1/roles")
    assert roles_resp.status_code == 200
    roles = roles_resp.json()
    role_ids = {r["id"] for r in roles}
    assert "role-python" in role_ids
    assert "role-legacy-cobol" not in role_ids  # Inactive role excluded from active list

    headers = {"X-Student-ID": "student-tc03"}
    resp = client.post(
        "/api/v1/profile",
        json={
            "display_name": "Priya Nair",
            "education_level": "B.Tech IT",
            "target_role_id": "role-python",
            "current_skills": ["Python"],
            "preferred_languages": ["Python"],
            "preparation_goal": "Strengthen backend API and Python idioms.",
            "available_preparation_time": 10,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["target_role_name"] == "Python Developer"


def test_tc04_handle_inactive_or_unknown_job_role(client: TestClient) -> None:
    """TC-04: Handle an inactive or unknown job role."""
    unknown_resp = client.get("/api/v1/roles/role-does-not-exist")
    assert unknown_resp.status_code == 404

    inactive_resp = client.get("/api/v1/roles/role-legacy-cobol")
    assert inactive_resp.status_code == 400
    assert "inactive" in inactive_resp.json()["detail"].lower()

    # Also reject selecting inactive role in profile creation
    prof_resp = client.post(
        "/api/v1/profile",
        json={
            "display_name": "Test Student",
            "education_level": "B.E.",
            "target_role_id": "role-legacy-cobol",
            "current_skills": [],
            "preferred_languages": [],
            "preparation_goal": "Valid length preparation goal",
            "available_preparation_time": 8,
        },
        headers={"X-Student-ID": "student-tc04"},
    )
    assert prof_resp.status_code == 400


def test_tc05_confirm_role_skill_mappings_retrieved_correctly(client: TestClient) -> None:
    """TC-05: Confirm role-skill mappings are retrieved correctly."""
    resp = client.get("/api/v1/roles/role-swe")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "role-swe"
    assert abs(data["total_weight"] - 1.0) < 1e-4
    assert len(data["skills"]) == 5
    for skill_req in data["skills"]:
        assert skill_req["weight"] > 0
        assert skill_req["expected_level"] > 0
        assert len(skill_req["rationale"]) > 10


# ============================================================
# QUESTION BANK TESTS (TC-06 to TC-10)
# ============================================================

def test_tc06_retrieve_active_assessment(client: TestClient) -> None:
    """TC-06: Retrieve an active assessment."""
    list_resp = client.get("/api/v1/assessments")
    assert list_resp.status_code == 200
    assessments = list_resp.json()
    ids = {a["id"] for a in assessments}
    assert "assess-aptitude" in ids
    assert "assess-inactive" not in ids

    detail_resp = client.get("/api/v1/assessments/assess-aptitude")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == "assess-aptitude"
    assert len(detail["questions"]) == 3


def test_tc07_do_not_expose_correct_answers_before_submission(client: TestClient) -> None:
    """TC-07: Do not expose correct answers before submission."""
    resp = client.get("/api/v1/assessments/assess-aptitude")
    assert resp.status_code == 200
    raw_text = json.dumps(resp.json())
    assert "correct_answer" not in raw_text
    assert "explanation" not in raw_text
    for q in resp.json()["questions"]:
        assert "correct_answer" not in q
        assert "correct_answer_json" not in q
        assert "explanation" not in q


def test_tc08_handle_missing_or_inactive_question_and_assessment(client: TestClient) -> None:
    """TC-08: Handle a missing or inactive question/assessment."""
    missing_resp = client.get("/api/v1/assessments/assess-nonexistent")
    assert missing_resp.status_code == 404

    inactive_resp = client.get("/api/v1/assessments/assess-inactive")
    assert inactive_resp.status_code == 400

    # Ensure inactive question q-inactive-1 is not included in active assessment questions
    apt_resp = client.get("/api/v1/assessments/assess-aptitude")
    q_ids = {q["id"] for q in apt_resp.json()["questions"]}
    assert "q-inactive-1" not in q_ids

    # Submitting an answer to an inactive question ID must be rejected
    headers = {"X-Student-ID": "student-tc08"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    sub_resp = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-inactive-1", "answer_value": "A"}]},
        headers=headers,
    )
    assert sub_resp.status_code == 422


def test_tc09_validate_question_options_and_scoring_configuration() -> None:
    """TC-09: Validate question options and scoring configuration."""
    assert validate_question_configuration(
        question_id="q-test-1",
        question_type="mcq",
        score_value=10.0,
        correct_answer_raw=json.dumps("A"),
        option_identifiers=["A", "B", "C", "D"],
    )
    with pytest.raises(ValueError, match="positive score_value"):
        validate_question_configuration("q-bad", "mcq", 0.0, json.dumps("A"), ["A", "B"])
    with pytest.raises(ValueError, match="not in options"):
        validate_question_configuration("q-bad-opt", "mcq", 10.0, json.dumps("Z"), ["A", "B"])


def test_tc10_handle_invalid_assessment_version(client: TestClient) -> None:
    """TC-10: Handle an invalid assessment version."""
    headers = {"X-Student-ID": "student-tc10"}
    resp = client.post(
        "/api/v1/assessments/assess-aptitude/attempts",
        json={"expected_version": "9.9.9"},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "version" in resp.json()["detail"].lower()


# ============================================================
# ASSESSMENT ENGINE TESTS (TC-11 to TC-19)
# ============================================================

def test_tc11_calculate_score_for_known_answer_set(client: TestClient) -> None:
    """TC-11: Calculate the score for a known answer set."""
    headers = {"X-Student-ID": "student-tc11"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    sub = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "B"},  # Correct (10)
                {"question_id": "q-apt-2", "answer_value": "C"},  # Correct (10)
                {"question_id": "q-apt-3", "answer_value": ["A", "C"]},  # Correct (10)
            ]
        },
        headers=headers,
    )
    assert sub.status_code == 200
    res = sub.json()
    assert res["earned_points"] == 30.0
    assert res["maximum_points"] == 30.0
    assert res["overall_score"] == 100.0
    assert res["readiness_category"] == "Strong Performance on Assessed Areas"


def test_tc12_calculate_partial_scores_correctly(client: TestClient) -> None:
    """TC-12: Calculate partial scores correctly where supported (multi_select)."""
    headers = {"X-Student-ID": "student-tc12"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    sub = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "B"},  # 10 / 10
                {"question_id": "q-apt-2", "answer_value": "A"},  # 0 / 10 (wrong)
                {"question_id": "q-apt-3", "answer_value": ["A"]},  # 5 / 10 (1 of 2 correct options selected)
            ]
        },
        headers=headers,
    )
    assert sub.status_code == 200
    res = sub.json()
    assert res["earned_points"] == 15.0
    assert res["maximum_points"] == 30.0
    assert res["overall_score"] == 50.0


def test_tc13_reject_invalid_answer_identifiers(client: TestClient) -> None:
    """TC-13: Reject invalid answer identifiers."""
    headers = {"X-Student-ID": "student-tc13"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    sub = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "INVALID_OPTION_Z"},
            ]
        },
        headers=headers,
    )
    assert sub.status_code == 422
    assert "Invalid option identifier" in sub.json()["detail"]


def test_tc14_prevent_second_submission_from_corrupting_first_result(client: TestClient) -> None:
    """TC-14: Prevent a second submission from corrupting the first result."""
    headers = {"X-Student-ID": "student-tc14"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    first = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-apt-1", "answer_value": "B"}]},
        headers=headers,
    )
    assert first.status_code == 200
    first_score = first.json()["overall_score"]

    second = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-apt-1", "answer_value": "A"}]},
        headers=headers,
    )
    assert second.status_code == 409

    # Verify stored result is unchanged
    check = client.get(f"/api/v1/attempts/{att['attempt_id']}/results", headers=headers)
    assert check.json()["overall_score"] == first_score


def test_tc15_preserve_separate_attempts_for_repeated_assessments(client: TestClient) -> None:
    """TC-15: Preserve separate attempts for repeated assessments."""
    headers = {"X-Student-ID": "student-tc15"}
    att1 = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    client.post(
        f"/api/v1/attempts/{att1['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-apt-1", "answer_value": "A"}]},
        headers=headers,
    )

    att2 = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    assert att1["attempt_id"] != att2["attempt_id"]
    client.post(
        f"/api/v1/attempts/{att2['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "B"},
                {"question_id": "q-apt-2", "answer_value": "C"},
                {"question_id": "q-apt-3", "answer_value": ["A", "C"]},
            ]
        },
        headers=headers,
    )

    res1 = client.get(f"/api/v1/attempts/{att1['attempt_id']}/results", headers=headers).json()
    res2 = client.get(f"/api/v1/attempts/{att2['attempt_id']}/results", headers=headers).json()
    assert res1["overall_score"] == 0.0
    assert res2["overall_score"] == 100.0


def test_tc16_handle_unanswered_questions_according_to_policy(client: TestClient) -> None:
    """TC-16: Handle unanswered required questions according to policy."""
    headers = {"X-Student-ID": "student-tc16"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()

    # When require_all_questions=True, partial answers are rejected with 422
    strict_resp = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [{"question_id": "q-apt-1", "answer_value": "B"}],
            "require_all_questions": True,
        },
        headers=headers,
    )
    assert strict_resp.status_code == 422

    # When require_all_questions=False, unanswered questions receive 0 points with explicit feedback
    lenient_resp = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [{"question_id": "q-apt-1", "answer_value": "B"}],
            "require_all_questions": False,
        },
        headers=headers,
    )
    assert lenient_resp.status_code == 200
    data = lenient_resp.json()
    assert data["answered_questions"] == 1
    assert data["total_questions"] == 3
    assert data["earned_points"] == 10.0


def test_tc17_handle_missing_assessment_evidence_correctly() -> None:
    """TC-17: Handle missing assessment evidence correctly (Not Assessed, never silent 0 or 100)."""
    reqs = [
        {"skill_id": "skill-python", "skill_name": "Python", "skill_category": "Technical", "weight": 0.6, "expected_level": 75.0},
        {"skill_id": "skill-sql", "skill_name": "SQL", "skill_category": "Technical", "weight": 0.4, "expected_level": 70.0},
    ]
    # Only Python assessed at 80%; SQL not assessed
    latest = {"skill-python": {"score": 80.0, "evidence_summary": "80%"}}
    readiness = calculate_role_readiness(reqs, latest)

    assert readiness["readiness_status"] == "Incomplete Assessment Evidence"
    assert readiness["readiness_category"] == "Insufficient Assessment Evidence"
    assert readiness["overall_role_readiness_score"] is None  # Withheld due to missing evidence
    assert readiness["assessed_area_weighted_score"] == 80.0
    sql_item = next(item for item in readiness["role_skill_readiness"] if item["skill_id"] == "skill-sql")
    assert sql_item["assessment_status"] == "Not Assessed"
    assert sql_item["current_score"] is None


def test_tc18_confirm_overall_scoring_weights_are_valid() -> None:
    """TC-18: Confirm overall scoring weights are valid."""
    assert validate_role_weights([0.35, 0.25, 0.20, 0.20]) is True
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_role_weights([0.50, 0.20])
    with pytest.raises(ValueError, match="must be in"):
        validate_role_weights([-0.2, 1.2])


def test_tc19_verify_different_assessment_versions_handled_correctly() -> None:
    """TC-19: Verify that different assessment versions are handled correctly."""
    earlier = {
        "attempt_id": "att-old",
        "assessment_version": "0.9.0",
        "scoring_version": "1.0.0",
        "submitted_at": "2026-10-01T10:00:00Z",
        "overall_score": 60.0,
        "skill_results": [],
    }
    later = {
        "attempt_id": "att-new",
        "assessment_version": "1.0.0",
        "scoring_version": "1.0.0",
        "submitted_at": "2026-10-12T10:00:00Z",
        "overall_score": 85.0,
        "skill_results": [],
    }
    comparison = compare_attempts_logic("assess-aptitude", "Aptitude", earlier, later)
    assert comparison["comparable"] is False
    assert comparison["score_delta"] is None
    assert "different versions" in comparison["comparison_note"]


# ============================================================
# RECOMMENDATIONS TESTS (TC-20 to TC-25)
# ============================================================

def test_tc20_and_tc21_recommendations_and_explanations_for_skill_gap(client: TestClient) -> None:
    """TC-20 & TC-21: Return recommendations for an identified skill gap and explain why each was generated."""
    headers = {"X-Student-ID": "student-tc20"}
    client.post(
        "/api/v1/profile",
        json={
            "display_name": "Rohan Verma",
            "education_level": "B.E. CSE",
            "target_role_id": "role-swe",
            "current_skills": ["C++"],
            "preferred_languages": ["Python"],
            "preparation_goal": "Target Software Developer placement role.",
            "available_preparation_time": 10,
        },
        headers=headers,
    )
    # Submit low score on Aptitude assessment
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-apt-1", "answer_value": "A"}]},  # 0%
        headers=headers,
    )

    recs_resp = client.get("/api/v1/recommendations", headers=headers)
    assert recs_resp.status_code == 200
    recs = recs_resp.json()
    assert len(recs) > 0
    apt_rec = next(r for r in recs if r["skill_id"] == "skill-aptitude")
    assert "Identified skill gap" in apt_rec["reason"]
    assert "0.0%" in apt_rec["reason"]
    assert "Software Developer" in apt_rec["reason"]


def test_tc22_avoid_recommending_completed_activity_without_justification(client: TestClient) -> None:
    """TC-22: Avoid recommending a completed activity without justification."""
    headers = {"X-Student-ID": "student-tc22"}
    client.post(
        "/api/v1/profile",
        json={
            "display_name": "Meera Nair",
            "education_level": "B.E.",
            "target_role_id": "role-swe",
            "current_skills": [],
            "preferred_languages": ["Python"],
            "preparation_goal": "Prepare for placements.",
            "available_preparation_time": 10,
        },
        headers=headers,
    )
    recs = client.get("/api/v1/recommendations", headers=headers).json()
    target_rec = recs[0]

    # Mark activity as completed
    patch_resp = client.patch(
        f"/api/v1/recommendations/{target_rec['id']}",
        json={"status": "completed"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "completed"

    # Refresh recommendations and ensure a duplicate pending recommendation for the same activity is NOT created
    refreshed = client.get("/api/v1/recommendations?refresh=true", headers=headers).json()
    pending_for_same_activity = [
        r for r in refreshed
        if r["learning_activity_id"] == target_rec["learning_activity_id"] and r["status"] == "pending"
    ]
    assert len(pending_for_same_activity) == 0


def test_tc23_handle_skill_with_insufficient_assessment_evidence(client: TestClient) -> None:
    """TC-23: Handle a skill with insufficient assessment evidence."""
    headers = {"X-Student-ID": "student-tc23"}
    client.post(
        "/api/v1/profile",
        json={
            "display_name": "Kiran Rao",
            "education_level": "B.Tech",
            "target_role_id": "role-data",
            "current_skills": [],
            "preferred_languages": ["SQL"],
            "preparation_goal": "Prepare for Data Analyst role.",
            "available_preparation_time": 8,
        },
        headers=headers,
    )
    # Without taking any assessments, recommendations clearly state 'Insufficient assessment evidence'
    recs = client.get("/api/v1/recommendations", headers=headers).json()
    assert len(recs) > 0
    assert all("Insufficient assessment evidence" in r["reason"] for r in recs)


def test_tc24_work_when_optional_ai_provider_unavailable() -> None:
    """TC-24: Work when the optional AI provider is unavailable."""
    def failing_ai_provider(_input):
        raise RuntimeError("AI API connection timeout")

    is_ai, note = enrich_with_optional_ai("Python Core & Idioms", 25.0, ai_provider_callable=failing_ai_provider)
    assert is_ai is False
    assert note is None


def test_tc25_reject_malformed_ai_generated_recommendation_output() -> None:
    """TC-25: Reject malformed AI-generated recommendation output."""
    with pytest.raises(ValueError, match="missing required schema fields"):
        validate_ai_recommendation_payload({"unexpected_key": "value"})

    with pytest.raises(ValueError, match="unsupported placement guarantee claim"):
        validate_ai_recommendation_payload(
            {
                "study_tip": "Complete this module for a 100% placement guarantee!",
                "focus_subtopics": ["Generators"],
                "disclaimer_acknowledged": True,
            }
        )


# ============================================================
# DASHBOARD AND PROGRESS TESTS (TC-26 to TC-30)
# ============================================================

def test_tc26_and_tc30_show_empty_state_without_fabricated_stats(client: TestClient) -> None:
    """TC-26 & TC-30: Show the empty state before assessment and avoid fabricated statistics."""
    headers = {"X-Student-ID": "student-tc26"}
    dash = client.get("/api/v1/dashboard", headers=headers).json()
    assert dash["has_profile"] is False
    assert dash["has_completed_assessments"] is False
    assert dash["overall_role_readiness_score"] is None
    assert dash["recent_attempts"] == []
    assert dash["completed_activities_count"] == 0


def test_tc27_display_actual_assessment_results_on_dashboard(client: TestClient) -> None:
    """TC-27: Display actual assessment results on dashboard."""
    headers = {"X-Student-ID": "student-tc27"}
    client.post(
        "/api/v1/profile",
        json={
            "display_name": "Ananya Gupta",
            "education_level": "B.E. CSE",
            "target_role_id": "role-swe",
            "current_skills": ["Python"],
            "preferred_languages": ["Python"],
            "preparation_goal": "Software engineering placement prep",
            "available_preparation_time": 12,
        },
        headers=headers,
    )
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "B"},
                {"question_id": "q-apt-2", "answer_value": "C"},
                {"question_id": "q-apt-3", "answer_value": ["A", "C"]},
            ]
        },
        headers=headers,
    )
    dash = client.get("/api/v1/dashboard", headers=headers).json()
    assert dash["has_completed_assessments"] is True
    assert dash["assessed_skills_count"] == 1
    assert dash["assessed_area_weighted_score"] == 100.0
    assert dash["overall_role_readiness_score"] is None  # Because 4 of 5 role skills are still Not Assessed


def test_tc28_and_tc29_progress_events_and_compatible_version_comparison(client: TestClient) -> None:
    """TC-28 & TC-29: Calculate progress from real stored events and compare compatible assessment versions."""
    headers = {"X-Student-ID": "student-tc28"}
    client.post(
        "/api/v1/profile",
        json={
            "display_name": "Vikram Rao",
            "education_level": "B.Tech",
            "target_role_id": "role-python",
            "current_skills": ["Python"],
            "preferred_languages": ["Python"],
            "preparation_goal": "Track progress across retakes.",
            "available_preparation_time": 10,
        },
        headers=headers,
    )
    # First attempt: 10/30 (33.33%)
    att1 = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    client.post(
        f"/api/v1/attempts/{att1['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-apt-1", "answer_value": "B"}]},
        headers=headers,
    )
    # Second attempt: 30/30 (100.0%)
    att2 = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()
    client.post(
        f"/api/v1/attempts/{att2['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "B"},
                {"question_id": "q-apt-2", "answer_value": "C"},
                {"question_id": "q-apt-3", "answer_value": ["A", "C"]},
            ]
        },
        headers=headers,
    )
    # Log a practice session
    prac = client.post(
        "/api/v1/progress/practice",
        json={"skill_id": "skill-aptitude", "duration_minutes": 45, "notes": "Practiced probability problems"},
        headers=headers,
    )
    assert prac.status_code == 201

    prog = client.get("/api/v1/progress", headers=headers).json()
    assert prog["total_attempts_submitted"] == 2
    assert prog["practice_sessions_logged"] == 1
    assert len(prog["attempt_comparisons"]) == 1
    comp = prog["attempt_comparisons"][0]
    assert comp["comparable"] is True
    assert comp["score_delta"] == 66.67


# ============================================================
# SECURITY TESTS (TC-31 to TC-36)
# ============================================================

def test_tc31_prevent_one_user_accessing_another_users_results(client: TestClient) -> None:
    """TC-31: Prevent one user accessing another user's results."""
    user_a = {"X-Student-ID": "student-alice"}
    user_b = {"X-Student-ID": "student-bob"}

    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=user_a).json()
    client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={"answers": [{"question_id": "q-apt-1", "answer_value": "B"}]},
        headers=user_a,
    )

    # Bob tries to view Alice's results
    forbidden_res = client.get(f"/api/v1/attempts/{att['attempt_id']}/results", headers=user_b)
    assert forbidden_res.status_code == 403


def test_tc32_and_tc33_validate_answers_and_prevent_score_manipulation(client: TestClient) -> None:
    """TC-32 & TC-33: Validate all submitted answers server-side and prevent score manipulation from frontend."""
    headers = {"X-Student-ID": "student-tc33"}
    att = client.post("/api/v1/assessments/assess-aptitude/attempts", headers=headers).json()

    # Attempt to inject a fake 'awarded_score' or 'overall_score' field from client
    tampered_resp = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "overall_score": 100.0,
            "answers": [
                {"question_id": "q-apt-1", "answer_value": "A", "awarded_score": 999.0},
            ],
        },
        headers=headers,
    )
    assert tampered_resp.status_code == 422


def test_tc34_ensure_secrets_do_not_appear_in_api_responses(client: TestClient) -> None:
    """TC-34: Ensure secrets do not appear in API responses."""
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    raw = json.dumps(health.json()).lower()
    assert "secret_key" not in raw
    assert "password" not in raw
    assert "ai_api_key" not in raw


def test_tc35_verify_appropriate_deletion_and_retention_behaviour(client: TestClient) -> None:
    """TC-35: Verify appropriate deletion and retention behaviour."""
    headers = {"X-Student-ID": "student-delete-me"}
    client.post(
        "/api/v1/profile",
        json={
            "display_name": "Temporary User",
            "education_level": "B.E.",
            "target_role_id": "role-swe",
            "current_skills": [],
            "preferred_languages": [],
            "preparation_goal": "Test deletion policy.",
            "available_preparation_time": 5,
        },
        headers=headers,
    )
    del_resp = client.delete("/api/v1/profile", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Subsequent profile lookup should return 404
    get_resp = client.get("/api/v1/profile", headers=headers)
    assert get_resp.status_code == 404


def test_tc36_check_logs_do_not_expose_unnecessary_personal_information() -> None:
    """TC-36: Check logs do not expose unnecessary personal information."""
    raw_log = {
        "event": "user_login",
        "display_name": "Aarav Sharma",
        "login_identifier": "aarav@example.com",
        "password": "my-secret-password",
        "access_token": "tok-12345",
        "target_role_id": "role-swe",
    }
    sanitized = sanitize_log_data(raw_log)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["display_name"] == "[REDACTED_PII]"
    assert sanitized["login_identifier"] == "[REDACTED_PII]"
    assert sanitized["target_role_id"] == "role-swe"
