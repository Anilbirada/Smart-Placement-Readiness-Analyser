# Security and Privacy Controls

## 1. Authentication & Session Protection
- **Password Hashing:** Local student account passwords are hashed using `PBKDF2-HMAC-SHA256` with 120,000 iterations and a cryptographically random 16-byte salt (`backend/app/core/security.py`). Plain-text passwords are never stored or logged.
- **Signed Access Tokens:** Authenticated sessions use HMAC-SHA256 signed tokens containing `sub` (`user_id`), `iat`, `exp`, and a unique `jti` nonce, verified using constant-time comparison (`hmac.compare_digest`).
- **Server-Side Authorization:** Every profile, attempt submission, result lookup, and recommendation update verifies `attempt.user_id == current_user.id` (or `rec.user_id == current_user.id`), returning `403 Forbidden` on cross-user access attempts (verified by **TC-31**).

## 2. Input Validation & Injection Prevention
- **SQL Injection Prevention:** All database operations use SQLAlchemy 2.0 ORM parameterised queries.
- **Cross-Site Scripting (XSS) Prevention:** User text fields (`display_name`, `education_level`, `preparation_goal`, skill lists, practice notes, and AI outputs) pass through `sanitize_text()` which strips HTML tags and script attributes before storage, and React automatically escapes rendered text nodes.
- **Anti-Tampering Schema Enforcement:** `SubmitAttemptRequest` and `SubmittedAnswerItem` set `model_config = {"extra": "forbid"}` so clients cannot inject `awarded_score` or `overall_score` overrides (verified by **TC-33**).

## 3. HTTP Security Headers & CORS
- Every HTTP response includes:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- CORS origins are restricted via `ALLOWED_ORIGINS` configuration.

## 4. Data Minimization, Retention & Deletion
- Only educational and career-preparation fields (`display_name`, `education_level`, `target_role_id`, `current_skills`, `preferred_languages`, `preparation_goal`, `available_preparation_time`) are collected.
- Sensitive personal identifiers (caste, religion, gender, disability, financial status, government IDs) are never requested or stored.
- Students can permanently delete their profile, attempts, results, recommendations, and progress logs at any time via `DELETE /api/v1/profile` or the **Delete My Profile & Assessment Data** button in the UI (**TC-35**).
- `sanitize_log_data()` redacts passwords, tokens, and personal identifiers (`[REDACTED]`, `[REDACTED_PII]`) before structured logging (**TC-36**).
