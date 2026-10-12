# Software Requirements Specification (SRS)

## 1. Functional Requirements

### FR-01: Student Authentication & Profile Management
- The system shall allow students to register/sign in (`POST /api/v1/auth/register`, `POST /api/v1/auth/login`) or operate within an isolated student session (`X-Student-ID`).
- The system shall allow students to create, view, update, and delete their profile (`POST /api/v1/profile`, `GET /api/v1/profile`, `DELETE /api/v1/profile`).
- Profile inputs shall validate display name (`2–100` chars), education level, active target job role, preparation goal (`5–500` chars), and available preparation time (`1–80` hours/week).

### FR-02: Role-Skill Mapping
- The system shall expose active job roles (`GET /api/v1/roles`) and detailed role-skill requirements (`GET /api/v1/roles/{role_id}`).
- Each active role shall have skill weights that are positive and sum to `1.0` (`100%`).
- Requests for unknown roles shall return `404 Not Found`; requests for inactive roles shall return `400 Bad Request`.

### FR-03: Question Bank & Assessment Delivery
- The system shall list active assessments (`GET /api/v1/assessments`) and return assessment questions (`GET /api/v1/assessments/{assessment_id}`).
- The backend shall never include `correct_answer` or post-submission `explanation` fields in pre-submission assessment payloads.
- Inactive assessments and inactive questions shall be excluded from active delivery.

### FR-04: Assessment Attempts & Backend Grading
- The system shall record each assessment attempt (`POST /api/v1/assessments/{assessment_id}/attempts`) with `assessment_version` and `started_at`.
- Submitting an attempt (`POST /api/v1/attempts/{attempt_id}/submit`) shall validate all question IDs and option identifiers server-side, reject client-injected score fields (`extra = "forbid"`), and prevent duplicate submissions (`409 Conflict`).
- Repeated assessments by the same student shall be stored as separate `AssessmentAttempt` records.

### FR-05: Personalised Recommendations
- The system shall generate rule-based recommendations (`GET /api/v1/recommendations`) linked to skills where `score < expected_level` or `status == "Not Assessed"`.
- Completed recommendations (`PATCH /api/v1/recommendations/{id}`) shall not be re-recommended as duplicate pending items.
- Optional AI enrichment shall be schema-validated and degrade gracefully if disabled or unavailable.

### FR-06: Dashboard & Progress Tracking
- `GET /api/v1/dashboard` shall return real stored profile, role skill coverage, assessed weighted score, overall role score (when 100% of role skills are assessed), recent attempts, and next suggested action.
- `GET /api/v1/progress` and `POST /api/v1/progress/practice` shall track attempt history, version-checked attempt comparisons, skill score deltas, and practice sessions.

## 2. Non-Functional Requirements
- **Security:** PBKDF2-HMAC-SHA256 password hashing, HMAC-SHA256 tokens, XSS tag stripping, ORM parameterised queries, cross-user authorization checks (`403 Forbidden`), and PII log redaction.
- **Usability & Accessibility:** Semantic HTML labels (`htmlFor`/`id`), keyboard `:focus-visible` outlines, high-contrast dark/neutral palette, and responsive layouts down to `320px` width.
- **Maintainability:** Modular separation between API routes, service orchestration, pure assessment/recommendation engines, and SQLAlchemy models.
