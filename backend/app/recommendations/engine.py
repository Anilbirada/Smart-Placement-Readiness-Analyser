from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from backend.app.core.config import AI_PROVIDER_ENABLED
from backend.app.core.security import sanitize_text

_FORBIDDEN_AI_PHRASES = (
    "guaranteed job",
    "guarantee placement",
    "100% placement",
    "guaranteed hiring",
    "will definitely be hired",
)


def validate_ai_recommendation_payload(payload: Any) -> Dict[str, Any]:
    """
    Strictly validate optional AI-generated study guidance (TC-25).
    Raises ValueError if malformed, missing required keys, or contains prohibited claims.
    """
    if not isinstance(payload, dict):
        raise ValueError("AI payload must be a JSON object.")

    allowed_keys = {"study_tip", "focus_subtopics", "disclaimer_acknowledged"}
    if not allowed_keys.issubset(set(payload.keys())):
        raise ValueError("AI payload is missing required schema fields.")

    if payload.get("disclaimer_acknowledged") is not True:
        raise ValueError("AI payload must acknowledge placement guidance disclaimer.")

    study_tip = payload.get("study_tip")
    if not isinstance(study_tip, str) or len(study_tip.strip()) < 10 or len(study_tip) > 400:
        raise ValueError("AI study_tip must be a string between 10 and 400 characters.")

    cleaned_tip = sanitize_text(study_tip, max_length=400)
    lower_tip = cleaned_tip.lower()
    for phrase in _FORBIDDEN_AI_PHRASES:
        if phrase in lower_tip:
            raise ValueError(f"AI output contains unsupported placement guarantee claim: '{phrase}'.")

    subtopics = payload.get("focus_subtopics")
    if not isinstance(subtopics, list) or len(subtopics) == 0 or len(subtopics) > 5:
        raise ValueError("AI focus_subtopics must be a non-empty list of up to 5 strings.")

    cleaned_subtopics: List[str] = []
    for item in subtopics:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Each focus_subtopic must be a non-empty string.")
        cleaned_subtopics.append(sanitize_text(item, max_length=80))

    return {
        "study_tip": cleaned_tip,
        "focus_subtopics": cleaned_subtopics,
        "disclaimer_acknowledged": True,
    }


def enrich_with_optional_ai(
    skill_name: str,
    gap_Value: Optional[float],
    ai_provider_callable: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Attempt optional AI enrichment using only non-PII skill gap metadata.
    Gracefully falls back to (False, None) if AI is disabled, unavailable, or returns malformed data (TC-24, TC-25).
    """
    if not AI_PROVIDER_ENABLED and ai_provider_callable is None:
        return False, None

    if ai_provider_callable is None:
        return False, None

    try:
        # Send strictly non-PII skill metadata
        safe_prompt_input = {
            "skill_name": sanitize_text(skill_name, max_length=100),
            "gap_points": round(float(gap_Value), 2) if gap_Value is not None else None,
        }
        raw_output = ai_provider_callable(safe_prompt_input)
        validated = validate_ai_recommendation_payload(raw_output)
        topics_str = ", ".join(validated["focus_subtopics"])
        note = f"[AI-Generated Study Tip — Verify Independently]: {validated['study_tip']} (Focus: {topics_str})"
        return True, note
    except Exception:
        # Graceful fallback when AI provider fails or returns invalid data
        return False, None


def build_rule_based_recommendations(
    role_name: str,
    available_prep_hours: int,
    role_requirements: List[Dict[str, Any]],
    latest_skill_scores: Dict[str, Dict[str, Any]],
    activities_by_skill: Dict[str, List[Dict[str, Any]]],
    completed_activity_ids: Set[str],
    existing_active_activity_ids: Set[str],
    ai_provider_callable: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Generate transparent, rule-based learning recommendations from skill gaps and missing evidence.
    Avoids recommending already completed activities without new post-completion evidence (TC-20..TC-24).
    """
    candidates: List[Dict[str, Any]] = []

    # Sort requirements by importance weight descending
    sorted_reqs = sorted(role_requirements, key=lambda r: float(r["weight"]), reverse=True)

    for req in sorted_reqs:
        skill_id = req["skill_id"]
        skill_name = req["skill_name"]
        weight = float(req["weight"])
        expected = float(req["expected_level"])
        skill_activities = activities_by_skill.get(skill_id, [])
        if not skill_activities:
            continue

        evidence = latest_skill_scores.get(skill_id)
        selected_activity = None
        for act in skill_activities:
            if act["id"] not in completed_activity_ids and act["id"] not in existing_active_activity_ids:
                selected_activity = act
                break

        if selected_activity is None:
            # Activity already completed or already active on the student's list (TC-22)
            continue

        effort_hours = float(selected_activity.get("effort_hours", 4.0))
        pace_note = (
            f"Fits within a single week of your {available_prep_hours} hrs/week schedule."
            if effort_hours <= available_prep_hours
            else f"Can be split across two weeks given your {available_prep_hours} hrs/week availability."
        )

        if evidence is not None and evidence.get("score") is not None:
            score = float(evidence["score"])
            if score >= expected:
                # Meets or exceeds expected level for this role; no gap recommendation needed
                continue
            gap = round(expected - score, 2)
            priority = "High" if (gap >= 20.0 or weight >= 0.30) else "Medium"
            reason = (
                f"Identified skill gap in {skill_name}: your latest assessment score is {score:.1f}%, "
                f"which is {gap:.1f} percentage points below the {expected:.1f}% target for {role_name} "
                f"(role importance weight: {int(round(weight * 100))}%). {pace_note}"
            )
            evidence_summary = evidence.get(
                "evidence_summary",
                f"Assessed score {score:.1f}% vs target {expected:.1f}%.",
            )
            is_ai, ai_note = enrich_with_optional_ai(skill_name, gap, ai_provider_callable)
            candidates.append(
                {
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "learning_activity_id": selected_activity["id"],
                    "reason": reason,
                    "evidence_summary": evidence_summary,
                    "priority": priority,
                    "is_ai_enhanced": is_ai,
                    "ai_note": ai_note,
                    "sort_key": (0 if priority == "High" else 1, -weight, -gap),
                }
            )
        else:
            # Skill has insufficient assessment evidence (TC-23)
            priority = "High" if weight >= 0.30 else "Low"
            reason = (
                f"Insufficient assessment evidence for {skill_name} (role importance weight: "
                f"{int(round(weight * 100))}% for {role_name}). Complete an assessment covering {skill_name} "
                f"and use this structured activity to prepare. {pace_note}"
            )
            evidence_summary = "Status: Not Assessed (0 completed assessment items for this skill)."
            is_ai, ai_note = enrich_with_optional_ai(skill_name, None, ai_provider_callable)
            candidates.append(
                {
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "learning_activity_id": selected_activity["id"],
                    "reason": reason,
                    "evidence_summary": evidence_summary,
                    "priority": priority,
                    "is_ai_enhanced": is_ai,
                    "ai_note": ai_note,
                    "sort_key": (1 if priority == "High" else 2, -weight, 0.0),
                }
            )

    candidates.sort(key=lambda c: c["sort_key"])
    for c in candidates:
        c.pop("sort_key", None)
    return candidates
