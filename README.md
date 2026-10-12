# Smart Placement Readiness Analyser

**GitHub Repository:** [https://github.com/Anilbirada/Smart-Placement-Readiness-Analyser](https://github.com/Anilbirada/Smart-Placement-Readiness-Analyser)  
**Project Description:** An evidence-based, transparent career preparation and skill-gap analysis platform (FastAPI + React + TypeScript + SQLAlchemy) that helps students evaluate their readiness for technical placement roles, identify strengths and improvement areas, follow a personalised study plan, and track verified progress over time.

> **Important Guidance Disclaimer:** Placement readiness scores and categories are educational preparation indicators computed from completed assessment evidence. They do **not** predict hiring probabilities, guarantee employment, or replace company-specific recruitment processes.

---

## 1. Project Purpose

Students preparing for campus and entry-level industry placements often practice across aptitude, programming, role-specific technical topics, and interview communication without knowing:
- Which skills carry the highest weight for their target role.
- Which areas are verified strengths versus unassessed blind spots.
- How to allocate limited weekly preparation hours across identified skill gaps.
- Whether their preparation is leading to measurable score improvements over time.

**Smart Placement Readiness Analyser** addresses these needs through a rule-based, auditable backend assessment and recommendation engine paired with an accessible React + TypeScript dashboard.

---

## 2. Key Features

1. **Student Profile & Privacy Controls:** Configure education level, target job role, self-reported skills, preferred programming languages, weekly study availability (`1–80 hours/week`), and preparation goals—with full one-click account and data deletion (`DELETE /api/v1/profile`).
2. **Configurable Target Role-Skill Mapping:** Explore 6 active job roles with validated skill weights (`sum = 1.0`), expected proficiency benchmarks, and explicit rationales.
3. **Structured Assessment Centre:** Take versioned assessments covering multiple-choice (`mcq`), multiple-select (`multi_select` with proportional partial credit), and short-text (`short_text`) questions. Correct answers and explanations are never sent to the browser before submission.
4. **Transparent Backend Scoring Engine:** Computes area scores, skill-level breakdowns, and role-weighted readiness while strictly separating *assessed performance* from *missing assessment evidence* (`Not Assessed`).
5. **Personalised Rule-Based Learning Plan:** Generates prioritised learning recommendations (`High`, `Medium`, `Low`) linked to specific skill gaps or missing evidence, role weights, and weekly study hours, with optional schema-validated AI study tips.
6. **Progress Tracker & Version-Checked Retake Comparison:** Logs practice sessions, tracks recommendation completion, and compares repeated assessment attempts when assessment and scoring versions are compatible.

---

## 3. Supported Target Roles

| Role ID | Role Name | Key Weighted Skills |
| :--- | :--- | :--- |
| `role-swe` | **Software Developer** | Data Structures & Algorithms (30%), Programming Fundamentals (25%), System & API Design (20%), Quantitative & Logical Aptitude (15%), Technical Communication (10%) |
| `role-python` | **Python Developer** | Python Core & Idioms (35%), Programming Fundamentals (20%), System & API Design (20%), Data Structures & Algorithms (15%), Quantitative & Logical Aptitude (10%) |
| `role-data` | **Data Analyst** | SQL & Data Analysis (35%), Quantitative & Logical Aptitude (25%), Python Core & Idioms (20%), Technical Communication (20%) |
| `role-aiml` | **AI/ML Engineer** | Machine Learning & Data Science (35%), Python Core & Idioms (25%), Quantitative & Logical Aptitude (20%), Data Structures & Algorithms (20%) |
| `role-web` | **Web Developer** | Web & Frontend Engineering (35%), System & API Design (25%), Programming Fundamentals (20%), Technical Communication (20%) |
| `role-qa` | **QA Engineer** | Software Testing & QA (35%), Programming Fundamentals (25%), Quantitative & Logical Aptitude (20%), System & API Design (20%) |

*(An archived role `role-legacy-cobol` is also seeded with `active = False` to verify inactive-role handling.)*

---

## 4. Technology Stack & Architecture

- **Frontend:** React 18, TypeScript, Vite, Responsive CSS (`frontend/src/`)
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (`backend/app/`)
- **Database:** SQLite (`backend/data/placement_readiness.db` for local execution; configurable via `DATABASE_URL` for PostgreSQL in shared deployments)
- **Assessment & Recommendation Engines:** Pure, independently testable Python modules (`backend/app/assessments/engine.py` and `backend/app/recommendations/engine.py`)
- **Testing:** `pytest` + FastAPI `TestClient` (`backend/tests/`)

---

## 5. Prerequisites & Installation

### Prerequisites
- **Python:** `>= 3.11` (verified on Python `3.12.10`)
- **Node.js & npm:** `Node >= 18` (verified on Node `v26.7.0`, npm `11.19.0`)

### Installation

```powershell
# 1. Install backend Python dependencies
pip install -r backend/requirements.txt

# 2. Install frontend Node dependencies
cd frontend
npm.cmd install
cd ..
```

---

## 6. Environment Configuration & Database Initialisation

1. Copy `.env.example` to `.env` if customising ports, database paths, or secrets.
2. Relational tables and reference seed data (roles, skills, role-skill mappings, assessments, questions, and learning activities) are automatically initialised via `bootstrap_database()` on backend startup.

---

## 7. Running the Application

### Start the Backend API Server
From the repository root:
```powershell
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```
- API Base URL: `http://localhost:8000/api/v1`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### Start the Frontend Development Server
From the `frontend` directory:
```powershell
cd frontend
npm.cmd run dev
```
- Web Application URL: `http://localhost:5173`

### Build the Frontend for Production
```powershell
cd frontend
npm.cmd run build
```

---

## 8. Running Automated Tests

From the repository root:
```powershell
python -m pytest backend/tests -v
```

---

## 9. How Scoring & Recommendations Work

- **Area Score:** `(Earned Points / Maximum Available Points) × 100`.
- **Multiple-Select Partial Credit:** Selecting $k$ of $m$ correct options with zero incorrect options awards $(k / m) \times \text{score\_value}$. Selecting any incorrect option awards $0$ points.
- **Missing Evidence Policy:** Unassessed role skills are marked `Not Assessed` (`score = null`). Overall Role Readiness Score is computed only when 100% of required skills for the selected role have been assessed; otherwise, the dashboard reports `Incomplete Assessment Evidence` alongside the weighted average of completed areas.
- **Recommendation Engine:** Generates activities for skills where `assessed_score < expected_level` or `status == "Not Assessed"`, ordered by priority (`High`, `Medium`, `Low`) and role weight. Completed activities are not re-recommended without new post-completion evidence.

---

## 10. Documentation Index

All project documentation is maintained in `docs/`:
1. [Project Charter](docs/PROJECT_CHARTER.md)
2. [Business Requirements Specification (BRS)](docs/BRS.md)
3. [Software Requirements Specification (SRS)](docs/SRS.md)
4. [System Design](docs/SYSTEM_DESIGN.md)
5. [Database Design](docs/DATABASE_DESIGN.md)
6. [API Documentation](docs/API_DOCUMENTATION.md)
7. [Assessment Scoring Rules](docs/ASSESSMENT_SCORING_RULES.md)
8. [Test Plan and Test Cases (TC-01 to TC-42)](docs/TEST_PLAN_AND_CASES.md)
9. [Security and Privacy Controls](docs/SECURITY_AND_PRIVACY.md)
10. [Fairness and Limitations](docs/FAIRNESS_AND_LIMITATIONS.md)
11. [Setup and Deployment Guide](docs/SETUP_AND_DEPLOYMENT.md)
12. [User Guide](docs/USER_GUIDE.md)
13. [Decision Log](docs/DECISION_LOG.md)
14. [Risks and Mitigations](docs/RISKS_AND_MITIGATIONS.md)
15. [Changelog](docs/CHANGELOG.md)
