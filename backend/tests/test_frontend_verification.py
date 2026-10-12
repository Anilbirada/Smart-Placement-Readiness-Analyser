from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT_DIR / "frontend" / "src"


def test_tc37_complete_primary_assessment_flow_e2e() -> None:
    """TC-37: Complete the primary assessment flow end-to-end (Profile -> Role -> Assessment -> Submit -> Results -> Plan)."""
    client = TestClient(app)
    headers = {"X-Student-ID": "student-e2e-tc37"}

    # 1. Create profile & select role
    prof = client.post(
        "/api/v1/profile",
        json={
            "display_name": "Siddharth Rao",
            "education_level": "B.E. CSE Final Year",
            "target_role_id": "role-swe",
            "current_skills": ["Python", "Data Structures"],
            "preferred_languages": ["Python"],
            "preparation_goal": "Complete end-to-end placement readiness diagnostic.",
            "available_preparation_time": 12,
        },
        headers=headers,
    )
    assert prof.status_code == 200

    # 2. Fetch assessment instructions & questions
    assess = client.get("/api/v1/assessments/assess-prog").json()
    assert len(assess["questions"]) == 4

    # 3. Start attempt & submit answers
    att = client.post("/api/v1/assessments/assess-prog/attempts", headers=headers).json()
    sub = client.post(
        f"/api/v1/attempts/{att['attempt_id']}/submit",
        json={
            "answers": [
                {"question_id": "q-prog-1", "answer_value": "A"},
                {"question_id": "q-prog-2", "answer_value": "short circuit"},
                {"question_id": "q-dsa-1", "answer_value": "B"},
                {"question_id": "q-dsa-2", "answer_value": ["A"]},  # Partial score on DSA
            ]
        },
        headers=headers,
    )
    assert sub.status_code == 200
    result = sub.json()
    assert result["overall_score"] == 87.5

    # 4. Verify dashboard & learning recommendations reflect the submitted attempt
    dash = client.get("/api/v1/dashboard", headers=headers).json()
    assert dash["has_completed_assessments"] is True
    assert dash["assessed_skills_count"] == 2


def test_tc38_and_tc39_frontend_validation_and_error_handling_contracts() -> None:
    """TC-38 & TC-39: Confirm frontend includes explicit client validation messages and backend error alert rendering."""
    app_tsx = (FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")
    api_ts = (FRONTEND_SRC / "services" / "api.ts").read_text(encoding="utf-8")

    # Verify client-side validation messages in App.tsx (TC-38)
    assert "Please enter a display name of at least 2 characters." in app_tsx
    assert "Please enter a preparation goal of at least 5 characters." in app_tsx
    assert "Available preparation time must be between 1 and 80 hours per week." in app_tsx

    # Verify backend error extraction and role="alert" rendering (TC-39)
    assert 'role="alert"' in app_tsx
    assert "payload.detail" in api_ts


def test_tc40_confirm_responsive_mobile_layout() -> None:
    """TC-40: Confirm responsive mobile layout rules in styles.css."""
    styles_css = (FRONTEND_SRC / "styles.css").read_text(encoding="utf-8")
    assert "@media (max-width: 900px)" in styles_css
    assert "grid-template-columns: 1fr;" in styles_css


def test_tc41_check_keyboard_navigation_and_accessible_labels() -> None:
    """TC-41: Check keyboard navigation focus styles and accessible form labels."""
    styles_css = (FRONTEND_SRC / "styles.css").read_text(encoding="utf-8")
    app_tsx = (FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")

    assert ":focus-visible" in styles_css
    for control_id in [
        "profile-display-name",
        "profile-education",
        "profile-target-role",
        "profile-current-skills",
        "profile-languages",
        "profile-prep-time",
        "profile-goal",
        "practice-skill",
        "practice-duration",
        "practice-notes",
    ]:
        assert f'htmlFor="{control_id}"' in app_tsx
        assert f'id="{control_id}"' in app_tsx


def test_tc42_confirm_charts_accurately_represent_stored_data() -> None:
    """TC-42: Confirm skill bars and dashboard charts bind strictly to stored current_score values without hardcoded percentages."""
    app_tsx = (FRONTEND_SRC / "App.tsx").read_text(encoding="utf-8")
    assert "item.current_score !== null ? Math.min(100, item.current_score) : 0" in app_tsx
    assert "Not Assessed" in app_tsx
