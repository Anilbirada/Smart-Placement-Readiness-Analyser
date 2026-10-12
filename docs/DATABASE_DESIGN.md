# Database Design — Smart Placement Readiness Analyser

## 1. Relational Schema Overview
The database is managed via SQLAlchemy 2.0 (`backend/app/models/entities.py`) with foreign-key integrity enforced (`PRAGMA foreign_keys=ON` in SQLite).

## 2. Entities & Columns

### A. `users`
- `id` (PK, String)
- `display_name` (String, Not Null)
- `login_identifier` (String, Unique, Indexed, Not Null)
- `password_hash` (String, Not Null — PBKDF2-HMAC-SHA256)
- `created_at`, `updated_at` (DateTime)

### B. `student_profiles`
- `id` (PK, String)
- `user_id` (FK -> `users.id` ON DELETE CASCADE, Unique)
- `education_level` (String)
- `target_role_id` (FK -> `job_roles.id`)
- `current_skills_json` (Text JSON array)
- `preferred_languages_json` (Text JSON array)
- `preparation_goal` (Text)
- `available_preparation_time` (Integer, 1–80 hours/week)
- `created_at`, `updated_at` (DateTime)

### C. `job_roles`
- `id` (PK, String), `name` (Unique), `description` (Text), `version` (String), `active` (Boolean)

### D. `skills`
- `id` (PK, String), `name` (Unique), `category` (String, Indexed), `description` (Text), `active` (Boolean)

### E. `role_skill_requirements`
- `id` (PK, Integer), `role_id` (FK -> `job_roles.id`), `skill_id` (FK -> `skills.id`), `weight` (Float), `expected_level` (Float), `rationale` (Text), `version` (String)
- Unique constraint on `(role_id, skill_id)`

### F. `assessments`
- `id` (PK, String), `title`, `description`, `instructions`, `assessment_type`, `skill_area`, `time_limit_minutes`, `version`, `status` (`active` | `inactive`)

### G. `questions` & H. `question_options`
- `questions`: `id` (PK), `assessment_id` (FK), `skill_id` (FK), `topic`, `skill_area`, `question_type` (`mcq` | `multi_select` | `short_text`), `question_text`, `difficulty`, `correct_answer_json` (never exposed before submission), `explanation`, `score_value`, `version`, `active`
- `question_options`: `id` (PK), `question_id` (FK), `option_identifier`, `option_text`

### I. `assessment_attempts` & J. `attempt_answers`
- `assessment_attempts`: `id` (PK), `user_id` (FK), `assessment_id` (FK), `assessment_version`, `started_at`, `submitted_at`, `status` (`in_progress` | `submitted`)
- `attempt_answers`: `id` (PK), `attempt_id` (FK), `question_id` (FK), `answer_value_json`, `awarded_score`, `maximum_score`, `is_correct`, `feedback`

### K. `assessment_results` & L. `skill_assessment_results`
- `assessment_results`: `id` (PK), `attempt_id` (Unique FK), `overall_score`, `earned_points`, `maximum_points`, `assessment_status`, `readiness_category`, `result_summary`, `limitations_note`, `scoring_version`, `created_at`
- `skill_assessment_results`: `id` (PK), `assessment_result_id` (FK), `skill_id` (FK), `score`, `earned_points`, `maximum_points`, `evidence_summary`, `assessment_status`

### M. `learning_activities`, N. `student_recommendations`, & O. `progress_events`
- `learning_activities`: `id` (PK), `skill_id` (FK), `title`, `description`, `activity_type`, `resource_url`, `estimated_effort`, `effort_hours`, `status`
- `student_recommendations`: `id` (PK), `user_id` (FK), `skill_id` (FK), `learning_activity_id` (FK), `reason`, `evidence_summary`, `priority`, `status`, `is_ai_enhanced`, `ai_note`, `created_at`, `completed_at`
- `progress_events`: `id` (PK), `user_id` (FK), `event_type`, `reference_id`, `event_timestamp`, `safe_metadata_json`

## 3. Data Retention & Deletion Policy
- Calling `DELETE /api/v1/profile` cascades deletion across `users`, `student_profiles`, `assessment_attempts`, `attempt_answers`, `assessment_results`, `skill_assessment_results`, `student_recommendations`, and `progress_events`.
