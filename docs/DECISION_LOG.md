# Architectural Decision Log (ADR)

## ADR-01: Modular Monolith with Pure Domain Engines
- **Context:** The platform requires transparent assessment grading, role-skill mapping, and recommendation generation that can be tested independently of HTTP or UI layers.
- **Decision:** Implement a FastAPI + React modular monolith where `backend/app/assessments/engine.py` and `backend/app/recommendations/engine.py` are pure Python modules invoked by `placement_service.py`.
- **Consequence:** Fast unit and integration testing (`42 passed` in pytest) without microservice network overhead.

## ADR-02: Explicit `Not Assessed` State for Missing Evidence
- **Context:** Treating unassessed skills as `0%` unfairly penalises students who have only taken one assessment; treating them as `100%` inflates readiness.
- **Decision:** Represent unassessed skills with `current_score = None` and `assessment_status = "Not Assessed"`. Compute `assessed_area_weighted_score` for completed areas while withholding `overall_role_readiness_score` (`None`) until 100% of required role skills are assessed.
- **Consequence:** Students always see an honest distinction between skill performance and assessment coverage.

## ADR-03: Proportional Partial Credit on Multiple-Select Questions
- **Context:** Binary all-or-nothing grading on multi-select questions obscures partial understanding, while unconstrained partial credit allows guessing all options.
- **Decision:** Award $(k / m) \times \text{score\_value}$ when $k$ of $m$ correct options are chosen and zero wrong options are selected; award `0` if any wrong option is selected.
- **Consequence:** Fairly rewards partial knowledge while preventing option-spamming.

## ADR-04: Rule-Based Recommendations Primary, Schema-Validated Optional AI
- **Context:** LLMs can hallucinate unverified courses or make unsupported hiring promises.
- **Decision:** Make deterministic rule-based gap matching the primary recommendation engine. Optional AI enrichment is disabled by default, receives zero PII, and is validated against `validate_ai_recommendation_payload()`.
- **Consequence:** Core functionality works offline/without external API keys and rejects malformed or exaggerated AI outputs.
