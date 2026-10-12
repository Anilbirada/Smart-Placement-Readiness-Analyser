# Changelog

## [1.0.0] - 2026-10-12
### Added
- **Relational Data Model (`backend/app/models/entities.py`):** 15 SQLAlchemy tables covering Users, StudentProfiles, JobRoles, Skills, RoleSkillRequirements, Assessments, Questions, QuestionOptions, AssessmentAttempts, AttemptAnswers, AssessmentResults, SkillAssessmentResults, LearningActivities, StudentRecommendations, and ProgressEvents.
- **Reference Dataset (`backend/app/repositories/seed_data.py`):** 6 active job roles, 10 skills, validated role-skill weights, 4 active diagnostic assessments, structured question bank (`mcq`, `multi_select`, `short_text`), and curated learning activities.
- **Assessment Engine (`backend/app/assessments/engine.py`):** Objective grading with proportional partial credit, role weight validation, `Not Assessed` missing-evidence policy, and version-aware retake comparison.
- **Recommendation Engine (`backend/app/recommendations/engine.py`):** Rule-based skill gap and missing-evidence recommender with completed-activity deduplication and optional schema-validated AI study-tip enrichment.
- **REST API (`backend/app/api/routes.py`):** Documented `/api/v1` endpoints for health, auth, roles, skills, profiles, assessments, attempts, dashboard, recommendations, and progress tracking.
- **React + TypeScript Frontend (`frontend/src/App.tsx`):** Responsive 8-screen student experience (Overview, Readiness Dashboard, Student Profile, Target Roles & Skills, Assessment Centre, Results & Skill Gaps, Learning Plan, Progress Tracker).
- **Automated Verification (`backend/tests/`):** 42 automated tests covering `TC-01` through `TC-42` plus legacy compatibility checks.
