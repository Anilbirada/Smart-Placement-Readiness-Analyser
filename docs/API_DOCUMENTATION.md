# API Documentation — Smart Placement Readiness Analyser

All endpoints are versioned under `/api/v1`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

## Authentication & Session Headers
- **Bearer Token:** `Authorization: Bearer <access_token>` (obtained from `/api/v1/auth/register` or `/api/v1/auth/login`).
- **Session Isolation Header:** `X-Student-ID: <student_id>` (isolates local workspace sessions when no Bearer token is provided).
- Cross-user access to attempts, results, or recommendations returns `403 Forbidden`.

---

## Endpoints

### 1. Health & Auth
- **`GET /api/v1/health`** — Returns service status, application version, scoring model version (`1.0.0`), and question bank version (`1.0.0`). Never exposes secrets.
- **`POST /api/v1/auth/register`** — Creates a student account with PBKDF2-HMAC-SHA256 password hashing and returns an HMAC-signed Bearer token (`201 Created`).
- **`POST /api/v1/auth/login`** — Authenticates credentials and returns a Bearer token (`200 OK` or `401 Unauthorized`).

### 2. Roles & Skills
- **`GET /api/v1/roles`** — Lists all active target job roles (`Software Developer`, `Python Developer`, `Data Analyst`, `AI/ML Engineer`, `Web Developer`, `QA Engineer`).
- **`GET /api/v1/roles/{role_id}`** — Returns role metadata, validated skill weights (`total_weight = 1.0`), expected proficiency levels, and rationales (`404` if unknown, `400` if inactive).
- **`GET /api/v1/skills`** — Lists all active skills across categories (`Aptitude`, `Programming`, `Technical`, `Communication & Career`).

### 3. Student Profile
- **`POST /api/v1/profile`** — Creates or updates the authenticated student's profile and triggers recommendation synchronisation (`200 OK`, `400` for inactive role, `422` for invalid inputs).
- **`GET /api/v1/profile`** — Retrieves the current student's profile (`200 OK` or `404 Not Found`).
- **`DELETE /api/v1/profile`** — Permanently deletes the student's profile, attempts, results, recommendations, and progress records (`200 OK`).

### 4. Assessments & Attempts
- **`GET /api/v1/assessments`** — Lists active assessments with question counts, covered skills, and time limits.
- **`GET /api/v1/assessments/{assessment_id}`** — Returns assessment instructions and active questions. **Security guarantee:** `correct_answer` and `explanation` are excluded prior to submission.
- **`POST /api/v1/assessments/{assessment_id}/attempts`** — Starts a new `in_progress` attempt (`201 Created`; returns `409 Conflict` if `expected_version` does not match).
- **`POST /api/v1/attempts/{attempt_id}/submit`** — Validates answers server-side, rejects extra score-tampering fields (`422`), prevents duplicate submissions (`409 Conflict`), computes scores, and returns the full diagnostic report (`200 OK`).
- **`GET /api/v1/attempts/{attempt_id}/results`** — Retrieves a submitted attempt's results, question explanations, strengths, and improvement areas (`200 OK`, `403` for another user's attempt).

### 5. Dashboard, Recommendations & Progress
- **`GET /api/v1/dashboard`** — Returns real stored readiness metrics, role skill breakdown (with `Not Assessed` status for missing evidence), recent attempts, and next suggested action.
- **`GET /api/v1/recommendations`** — Returns personalised learning activities linked to skill gaps or missing evidence. Pass `?refresh=true` to force recalculation.
- **`PATCH /api/v1/recommendations/{recommendation_id}`** — Updates recommendation status (`pending`, `in_progress`, `completed`, `dismissed`).
- **`GET /api/v1/progress`** — Returns submitted attempt history, skill score progression, version-checked retake comparisons, and event logs.
- **`POST /api/v1/progress/practice`** — Logs a self-study practice session (`201 Created`).
