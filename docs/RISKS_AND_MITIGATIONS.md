# Risks and Mitigations

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Implemented |
| :--- | :--- | :--- | :--- | :--- |
| **R-01** | Students misinterpret a high assessment score as a guarantee of placement. | Medium | High | Persistent disclaimer banner across the UI, explicit `limitations_note` on every result payload, and guidance-only category labels. |
| **R-02** | Missing assessment evidence distorts overall role readiness score. | High | High | Unassessed skills are marked `Not Assessed` (`score = null`), and overall role score is withheld until all required role skills are assessed (**TC-17**). |
| **R-03** | Client-side tampering with answer scores or viewing answers before submission. | Medium | High | `correct_answer` is stripped from pre-submission endpoints (**TC-07**), grading runs solely on the backend, and `extra="forbid"` blocks injected score fields (**TC-33**). |
| **R-04** | Cross-user data leakage between students. | Low | High | Server-side ownership checks on attempts, results, and recommendations return `403 Forbidden` (**TC-31**). |
| **R-05** | Assessment version changes invalidate historical score comparisons. | Medium | Medium | `compare_attempts_logic()` verifies both `assessment_version` and `scoring_version`, disabling direct delta calculation when versions differ (**TC-19**). |
| **R-06** | Optional AI provider outage or hallucinated guarantees. | Medium | Medium | `enrich_with_optional_ai()` catches all provider errors (**TC-24**) and `validate_ai_recommendation_payload()` rejects forbidden guarantee phrases (**TC-25**). |
