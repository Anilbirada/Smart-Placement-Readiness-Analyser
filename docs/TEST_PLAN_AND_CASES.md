# Test Plan and Verification Cases (TC-01 to TC-42)

## Execution Summary
- **Test Command:** `python -m pytest backend/tests -v`
- **Frontend Build Verification Command:** `npm.cmd run build` (in `frontend/`)
- **Actual Result:** **42 passed in pytest** (`test_placement_system.py`, `test_frontend_verification.py`, and `test_api.py`), **0 failed**, **0 blocked**.

---

## Detailed Test Case Execution Log

| Test ID | Purpose | Preconditions | Steps | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Create a valid student profile | Seeded DB | `POST /api/v1/profile` with valid fields and `role-swe` | `200 OK`, profile persisted with role name | `200 OK`, `Software Developer` returned | **Pass** |
| **TC-02** | Reject invalid profile data | Seeded DB | `POST /api/v1/profile` with XSS display name, short goal, 0 hours | `422 Unprocessable Entity` | `422` returned | **Pass** |
| **TC-03** | Select a supported target role | Seeded DB | `GET /api/v1/roles` then `POST /api/v1/profile` with `role-python` | Active roles listed; profile bound to `Python Developer` | Verified `Python Developer` | **Pass** |
| **TC-04** | Handle inactive or unknown job role | Seeded DB (`role-legacy-cobol` inactive) | `GET /api/v1/roles/role-does-not-exist` & `GET /api/v1/roles/role-legacy-cobol` | `404` for unknown role; `400` for inactive role | `404` and `400` verified | **Pass** |
| **TC-05** | Confirm role-skill mappings retrieved | Seeded DB | `GET /api/v1/roles/role-swe` | Returns 5 skills, weights summing to `1.0`, rationales | 5 skills, `total_weight = 1.0` | **Pass** |
| **TC-06** | Retrieve an active assessment | Seeded DB | `GET /api/v1/assessments` and `/assessments/assess-aptitude` | Active assessments listed; 3 active questions returned | Verified 3 questions | **Pass** |
| **TC-07** | Do not expose correct answers before submission | Seeded DB | Inspect JSON payload of `GET /api/v1/assessments/assess-aptitude` | `correct_answer` and `explanation` absent from response | Confirmed absent | **Pass** |
| **TC-08** | Handle missing or inactive question/assessment | `q-inactive-1` & `assess-inactive` seeded | Request inactive assessment; submit answer to `q-inactive-1` | `404`/`400` on assessment; `422` on inactive question | Verified `404`, `400`, `422` | **Pass** |
| **TC-09** | Validate question options & scoring config | Engine loaded | Call `validate_question_configuration` with valid/invalid configs | Valid config passes; 0 score or invalid option raises `ValueError` | Verified | **Pass** |
| **TC-10** | Handle invalid assessment version | Seeded DB | `POST /api/v1/assessments/assess-aptitude/attempts` with `expected_version="9.9.9"` | `409 Conflict` | `409 Conflict` returned | **Pass** |
| **TC-11** | Calculate score for known answer set | Active attempt | Submit all correct answers (`B`, `C`, `["A","C"]`) | `30/30` points (`100.0%`) | `100.0%` calculated | **Pass** |
| **TC-12** | Calculate partial scores correctly | Active attempt | Submit `["A"]` (1 of 2 correct options) on `q-apt-3` | `5.0 / 10.0` partial credit awarded (`15/30 = 50.0%`) | `15.0` pts (`50.0%`) verified | **Pass** |
| **TC-13** | Reject invalid answer identifiers | Active attempt | Submit `answer_value: "INVALID_OPTION_Z"` | `422 Unprocessable Entity` | `422` returned | **Pass** |
| **TC-14** | Prevent second submission corrupting first | Submitted attempt | Re-submit different answers to same `attempt_id` | `409 Conflict`; original score unchanged | `409` returned; original score intact | **Pass** |
| **TC-15** | Preserve separate attempts for retakes | Student session | Complete attempt 1 (`0%`) and attempt 2 (`100%`) | Both attempts stored with distinct IDs and scores | Both attempts verified | **Pass** |
| **TC-16** | Handle unanswered questions per policy | Active attempt | Submit partial answers with `require_all_questions=True` then `False` | `422` when strict; `0` pts awarded for unanswered when lenient | Verified both modes | **Pass** |
| **TC-17** | Handle missing assessment evidence | Partial role coverage | Call `calculate_role_readiness` with 1 of 2 skills assessed | Unassessed skill marked `Not Assessed`; overall score `None` | Verified `Not Assessed` & `None` | **Pass** |
| **TC-18** | Confirm overall scoring weights are valid | Engine loaded | Call `validate_role_weights` with valid (`sum=1.0`) and invalid weights | Raises `ValueError` when sum != 1.0 or weight <= 0 | Verified | **Pass** |
| **TC-19** | Handle different assessment versions | Two attempts (`v0.9.0` vs `v1.0.0`) | Call `compare_attempts_logic` | `comparable = False`, `score_delta = None` with explanation | Verified | **Pass** |
| **TC-20** | Return recommendations for skill gap | Low score (`0%`) in Aptitude | `GET /api/v1/recommendations` | Returns high-priority Aptitude learning activity | Verified | **Pass** |
| **TC-21** | Explain why recommendation was generated | Low score in Aptitude | Inspect `reason` field of generated recommendation | Cites exact score (`0.0%`), target, and role weight | Verified | **Pass** |
| **TC-22** | Avoid recommending completed activity | Activity marked `completed` | `PATCH /api/v1/recommendations/{id}` to `completed`, then refresh | Completed activity not duplicated as pending | Verified | **Pass** |
| **TC-23** | Handle skill with insufficient evidence | Profile created, 0 attempts | `GET /api/v1/recommendations` | Recommendations state `Insufficient assessment evidence` | Verified | **Pass** |
| **TC-24** | Work when optional AI provider unavailable | Failing AI callable | Call `enrich_with_optional_ai` with failing provider | Gracefully returns `(False, None)` without crashing | Verified | **Pass** |
| **TC-25** | Reject malformed AI recommendation output | Malformed/guarantee AI JSON | Call `validate_ai_recommendation_payload` | Raises `ValueError` for missing fields or guarantee claims | Verified | **Pass** |
| **TC-26** | Show empty state before assessment | New student session | `GET /api/v1/dashboard` | `has_profile=False`, `has_completed_assessments=False` | Verified | **Pass** |
| **TC-27** | Display actual assessment results | 1 completed attempt | `GET /api/v1/dashboard` | Shows real attempt score (`100.0%`) and `1/5` skill coverage | Verified | **Pass** |
| **TC-28** | Calculate progress from real stored events | 2 attempts + 1 practice session | `GET /api/v1/progress` | `total_attempts_submitted=2`, `practice_sessions_logged=1` | Verified | **Pass** |
| **TC-29** | Compare compatible assessment versions | 2 attempts on `v1.0.0` (`33.33%` -> `100%`) | Inspect `attempt_comparisons` in `GET /api/v1/progress` | `comparable=True`, `score_delta=+66.67` | Verified | **Pass** |
| **TC-30** | Avoid fabricated activity or statistics | Fresh session | Inspect dashboard and progress responses | Zero attempts, zero completed activities, `null` overall score | Verified | **Pass** |
| **TC-31** | Prevent cross-user access to results | Alice & Bob sessions | Bob requests Alice's `/api/v1/attempts/{id}/results` | `403 Forbidden` | `403 Forbidden` returned | **Pass** |
| **TC-32** | Validate all submitted answers server-side | Active attempt | Submit invalid option ID or unknown question ID | `422 Unprocessable Entity` | `422` returned | **Pass** |
| **TC-33** | Prevent score manipulation from frontend | Active attempt | Inject `awarded_score: 999` and `overall_score: 100` in JSON body | Rejected with `422 Unprocessable Entity` (`extra="forbid"`) | `422` returned | **Pass** |
| **TC-34** | Ensure secrets do not appear in API responses | Running API | `GET /api/v1/health` | No `secret_key`, `password`, or `ai_api_key` in response | Verified | **Pass** |
| **TC-35** | Verify deletion and retention behaviour | Existing student profile | `DELETE /api/v1/profile` then `GET /api/v1/profile` | `200 OK` on delete; subsequent `GET` returns `404` | Verified | **Pass** |
| **TC-36** | Check logs do not expose PII or secrets | Log dictionary with PII/secrets | Call `sanitize_log_data` | Redacts `password`, `access_token`, `display_name`, `login_identifier` | Verified `[REDACTED]` | **Pass** |
| **TC-37** | Complete primary assessment flow E2E | Full app stack | Profile -> Role -> Assessment -> Submit -> Dashboard | End-to-end journey completes with `87.5%` score | Verified | **Pass** |
| **TC-38** | Show useful validation messages | Frontend source & API | Inspect validation handlers in `App.tsx` and API | Explicit messages for short name, goal, and hours range | Verified | **Pass** |
| **TC-39** | Handle backend errors | Frontend source & API client | Inspect `api.ts` error parser and `role="alert"` banner | Backend `detail` rendered inside accessible alert banner | Verified | **Pass** |
| **TC-40** | Confirm responsive mobile layout | `frontend/src/styles.css` | Check `@media (max-width: 900px)` rules | Multi-column grids collapse to `1fr` on mobile viewports | Verified | **Pass** |
| **TC-41** | Check keyboard navigation & accessible labels | `App.tsx` & `styles.css` | Check `:focus-visible` and `<label htmlFor>` bindings | All 10 form inputs have matching `htmlFor`/`id` and focus outlines | Verified | **Pass** |
| **TC-42** | Confirm charts represent stored data | `App.tsx` | Verify progress bar width binding | Bound strictly to `item.current_score`; `0%` when `Not Assessed` | Verified | **Pass** |
