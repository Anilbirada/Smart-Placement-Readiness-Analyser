from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from backend.app.core.config import DISCLAIMER_TEXT, READINESS_THRESHOLDS, SCORING_MODEL_VERSION


def validate_role_weights(weights: Sequence[float]) -> bool:
    """Validate that role skill weights are positive and sum to 1.0 (TC-18)."""
    if not weights:
        raise ValueError("Role must define at least one skill weight.")
    for w in weights:
        if w <= 0.0 or w > 1.0:
            raise ValueError(f"Invalid skill weight {w}: each weight must be in (0, 1].")
    total = sum(weights)
    if abs(total - 1.0) > 1e-4:
        raise ValueError(f"Role skill weights must sum to 1.0, but summed to {total:.4f}.")
    return True


def validate_question_configuration(
    question_id: str,
    question_type: str,
    score_value: float,
    correct_answer_raw: str,
    option_identifiers: Sequence[str],
) -> bool:
    """Validate question options and grading configuration (TC-09)."""
    if score_value <= 0:
        raise ValueError(f"Question {question_id} must have a positive score_value.")
    if question_type not in {"mcq", "multi_select", "short_text"}:
        raise ValueError(f"Unsupported question_type '{question_type}' for question {question_id}.")

    correct = json.loads(correct_answer_raw)
    if question_type in {"mcq", "multi_select"}:
        if len(option_identifiers) < 2:
            raise ValueError(f"Question {question_id} must have at least 2 options.")
        if len(set(option_identifiers)) != len(option_identifiers):
            raise ValueError(f"Question {question_id} has duplicate option identifiers.")
        valid_set = set(option_identifiers)
        if question_type == "mcq":
            if not isinstance(correct, str) or correct not in valid_set:
                raise ValueError(f"MCQ {question_id} correct answer '{correct}' is not in options {valid_set}.")
        else:
            if not isinstance(correct, list) or not correct or not all(c in valid_set for c in correct):
                raise ValueError(f"Multi-select {question_id} correct answers {correct} invalid for options {valid_set}.")
    elif question_type == "short_text":
        if not (isinstance(correct, str) or (isinstance(correct, list) and len(correct) > 0)):
            raise ValueError(f"Short-text question {question_id} must define accepted answer string(s).")

    return True


def categorize_readiness(score: Optional[float], is_complete_evidence: bool = True) -> str:
    """Map an assessment or role score to a transparent guidance category."""
    if score is None or not is_complete_evidence:
        return "Insufficient Assessment Evidence"
    if score < READINESS_THRESHOLDS["needs_more_preparation"]:
        return "Needs More Preparation"
    if score < READINESS_THRESHOLDS["developing"]:
        return "Developing"
    if score < READINESS_THRESHOLDS["progressing_well"]:
        return "Progressing Well"
    return "Strong Performance on Assessed Areas"


def grade_question(
    question_id: str,
    question_type: str,
    score_value: float,
    correct_answer_json: str,
    valid_option_ids: Sequence[str],
    submitted_answer: Union[str, List[str], None],
) -> Tuple[float, bool, str]:
    """
    Grade a single objective question on the backend.
    Returns (awarded_score, is_correct, feedback).
    Raises ValueError if submitted option identifiers are invalid (TC-13).
    """
    correct = json.loads(correct_answer_json)
    valid_set = set(valid_option_ids)

    # Handle unanswered question (TC-16)
    if submitted_answer is None or submitted_answer == "" or submitted_answer == []:
        return 0.0, False, "Question was left unanswered (0 points awarded per grading policy)."

    if question_type == "mcq":
        if not isinstance(submitted_answer, str):
            raise ValueError(f"Question {question_id} expects a single option string identifier.")
        ans = submitted_answer.strip()
        if ans not in valid_set:
            raise ValueError(f"Invalid option identifier '{ans}' for question {question_id}.")
        if ans == correct:
            return float(score_value), True, "Correct answer selected."
        return 0.0, False, f"Incorrect option '{ans}' selected."

    if question_type == "multi_select":
        if not isinstance(submitted_answer, list):
            raise ValueError(f"Question {question_id} expects a list of option identifiers.")
        cleaned_selections: List[str] = []
        for item in submitted_answer:
            if not isinstance(item, str):
                raise ValueError(f"Invalid option identifier type in question {question_id}.")
            opt = item.strip()
            if opt not in valid_set:
                raise ValueError(f"Invalid option identifier '{opt}' for question {question_id}.")
            if opt not in cleaned_selections:
                cleaned_selections.append(opt)

        if not cleaned_selections:
            return 0.0, False, "Question was left unanswered (0 points awarded per grading policy)."

        correct_set = set(correct)
        selected_set = set(cleaned_selections)
        wrong_selected = selected_set - correct_set
        if wrong_selected:
            return 0.0, False, "Incorrect option(s) selected; no partial credit when wrong options are chosen."

        matched_count = len(selected_set & correct_set)
        total_correct = len(correct_set)
        if matched_count == total_correct:
            return float(score_value), True, "All correct options selected."

        partial_score = round((matched_count / total_correct) * float(score_value), 2)
        return (
            partial_score,
            False,
            f"Partial credit awarded: selected {matched_count} of {total_correct} correct options with no wrong options.",
        )

    if question_type == "short_text":
        if not isinstance(submitted_answer, str):
            raise ValueError(f"Question {question_id} expects a text string answer.")
        normalized = " ".join(submitted_answer.strip().lower().split())
        if not normalized:
            return 0.0, False, "Question was left unanswered (0 points awarded per grading policy)."
        accepted = [correct.lower()] if isinstance(correct, str) else [str(c).strip().lower() for c in correct]
        if normalized in accepted:
            return float(score_value), True, "Correct response."
        return 0.0, False, "Response did not match expected technical term."

    raise ValueError(f"Unsupported question type: {question_type}")


def calculate_role_readiness(
    role_requirements: List[Dict[str, Any]],
    latest_skill_scores: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Calculate role readiness while strictly separating:
    1. Assessed skill performance
    2. Missing assessment evidence ("Not Assessed" — never silently 0 or 100)
    3. Overall role readiness (only computed when all required role skills are assessed)
    """
    if not role_requirements:
        return {
            "readiness_status": "Not Configured",
            "readiness_category": "Insufficient Assessment Evidence",
            "overall_role_readiness_score": None,
            "assessed_area_weighted_score": None,
            "assessed_weight_coverage_percent": 0.0,
            "assessed_skills_count": 0,
            "total_role_skills_count": 0,
            "incomplete_evidence_explanation": "No skill requirements configured for this role.",
            "role_skill_readiness": [],
        }

    weights = [float(r["weight"]) for r in role_requirements]
    validate_role_weights(weights)
    total_weight = sum(weights)

    assessed_weight = 0.0
    weighted_score_sum = 0.0
    assessed_skills_count = 0
    breakdown: List[Dict[str, Any]] = []

    for req in role_requirements:
        s_id = req["skill_id"]
        weight = float(req["weight"])
        expected = float(req["expected_level"])
        skill_evidence = latest_skill_scores.get(s_id)

        if skill_evidence is not None and skill_evidence.get("score") is not None:
            score = float(skill_evidence["score"])
            assessed_weight += weight
            weighted_score_sum += score * weight
            assessed_skills_count += 1
            gap = round(max(0.0, expected - score), 2)
            status_label = "Meets Target" if score >= expected else "Needs Improvement"
            breakdown.append(
                {
                    "skill_id": s_id,
                    "skill_name": req["skill_name"],
                    "skill_category": req["skill_category"],
                    "role_weight": weight,
                    "expected_level": expected,
                    "current_score": round(score, 2),
                    "gap": gap,
                    "assessment_status": "Assessed",
                    "status_label": status_label,
                    "evidence_summary": skill_evidence.get(
                        "evidence_summary",
                        f"Assessed score: {score:.1f}% (target: {expected:.1f}%).",
                    ),
                }
            )
        else:
            # Missing evidence is explicitly marked Not Assessed — never silently 0 or 100 (TC-17)
            breakdown.append(
                {
                    "skill_id": s_id,
                    "skill_name": req["skill_name"],
                    "skill_category": req["skill_category"],
                    "role_weight": weight,
                    "expected_level": expected,
                    "current_score": None,
                    "gap": None,
                    "assessment_status": "Not Assessed",
                    "status_label": "Not Assessed",
                    "evidence_summary": "Not Assessed: Complete an assessment covering this skill to generate evidence.",
                }
            )

    coverage_pct = round((assessed_weight / total_weight) * 100.0, 2) if total_weight > 0 else 0.0
    total_skills = len(role_requirements)

    if assessed_skills_count == 0:
        return {
            "readiness_status": "Not Assessed",
            "readiness_category": "Insufficient Assessment Evidence",
            "overall_role_readiness_score": None,
            "assessed_area_weighted_score": None,
            "assessed_weight_coverage_percent": 0.0,
            "assessed_skills_count": 0,
            "total_role_skills_count": total_skills,
            "incomplete_evidence_explanation": (
                f"0 of {total_skills} required skills for this role have been assessed. "
                "Unassessed skills are marked 'Not Assessed' rather than treated as 0%."
            ),
            "role_skill_readiness": breakdown,
        }

    assessed_weighted_score = round(weighted_score_sum / assessed_weight, 2)

    if assessed_skills_count < total_skills:
        unassessed_names = [b["skill_name"] for b in breakdown if b["assessment_status"] == "Not Assessed"]
        return {
            "readiness_status": "Incomplete Assessment Evidence",
            "readiness_category": "Insufficient Assessment Evidence",
            "overall_role_readiness_score": None,
            "assessed_area_weighted_score": assessed_weighted_score,
            "assessed_weight_coverage_percent": coverage_pct,
            "assessed_skills_count": assessed_skills_count,
            "total_role_skills_count": total_skills,
            "incomplete_evidence_explanation": (
                f"Assessed {assessed_skills_count} of {total_skills} required role skills "
                f"({coverage_pct:.1f}% of role weight). Overall role score is withheld until "
                f"missing skills ({', '.join(unassessed_names)}) are assessed. "
                f"Your weighted score across completed areas is {assessed_weighted_score:.1f}%."
            ),
            "role_skill_readiness": breakdown,
        }

    overall_score = round(weighted_score_sum / total_weight, 2)
    return {
        "readiness_status": "Complete Assessment Evidence",
        "readiness_category": categorize_readiness(overall_score, is_complete_evidence=True),
        "overall_role_readiness_score": overall_score,
        "assessed_area_weighted_score": overall_score,
        "assessed_weight_coverage_percent": 100.0,
        "assessed_skills_count": assessed_skills_count,
        "total_role_skills_count": total_skills,
        "incomplete_evidence_explanation": (
            f"All {total_skills} required skills for this target role have been assessed "
            f"(100% weight coverage, scoring model v{SCORING_MODEL_VERSION})."
        ),
        "role_skill_readiness": breakdown,
    }


def compare_attempts_logic(
    assessment_id: str,
    assessment_title: str,
    earlier: Dict[str, Any],
    later: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare two attempts of the same assessment, checking version compatibility (TC-19, TC-29)."""
    same_assessment_version = earlier["assessment_version"] == later["assessment_version"]
    same_scoring_version = earlier.get("scoring_version", "1.0.0") == later.get("scoring_version", "1.0.0")
    comparable = bool(same_assessment_version and same_scoring_version)

    if not comparable:
        comparison_note = (
            f"Attempts used different versions (earlier: assessment v{earlier['assessment_version']} / "
            f"scoring v{earlier.get('scoring_version', '1.0.0')}; later: assessment v{later['assessment_version']} / "
            f"scoring v{later.get('scoring_version', '1.0.0')}). Direct score comparison is disabled because "
            "question bank or scoring criteria changed between versions."
        )
        score_delta = None
        skill_deltas: List[Dict[str, Any]] = []
    else:
        e_score = earlier.get("overall_score") or 0.0
        l_score = later.get("overall_score") or 0.0
        score_delta = round(float(l_score) - float(e_score), 2)
        direction = "improved" if score_delta > 0 else ("declined" if score_delta < 0 else "remained unchanged")
        comparison_note = (
            f"Both attempts used compatible assessment v{later['assessment_version']}. "
            f"Overall score {direction} by {abs(score_delta):.2f} percentage points."
        )
        earlier_skills = {s["skill_id"]: s for s in earlier.get("skill_results", [])}
        later_skills = {s["skill_id"]: s for s in later.get("skill_results", [])}
        skill_deltas = []
        for s_id, l_skill in later_skills.items():
            e_skill = earlier_skills.get(s_id)
            if e_skill and e_skill.get("score") is not None and l_skill.get("score") is not None:
                s_delta = round(float(l_skill["score"]) - float(e_skill["score"]), 2)
                skill_deltas.append(
                    {
                        "skill_id": s_id,
                        "skill_name": l_skill.get("skill_name", s_id),
                        "earlier_score": round(float(e_skill["score"]), 2),
                        "later_score": round(float(l_skill["score"]), 2),
                        "delta": s_delta,
                    }
                )

    return {
        "assessment_id": assessment_id,
        "assessment_title": assessment_title,
        "earlier_attempt_id": earlier["attempt_id"],
        "earlier_version": earlier["assessment_version"],
        "earlier_submitted_at": earlier["submitted_at"],
        "earlier_score": earlier.get("overall_score"),
        "later_attempt_id": later["attempt_id"],
        "later_version": later["assessment_version"],
        "later_submitted_at": later["submitted_at"],
        "later_score": later.get("overall_score"),
        "comparable": comparable,
        "score_delta": score_delta,
        "comparison_note": comparison_note,
        "skill_deltas": skill_deltas,
        "disclaimer": DISCLAIMER_TEXT,
    }
