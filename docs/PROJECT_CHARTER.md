# Project Charter — Smart Placement Readiness Analyser

## 1. Project Overview
**Smart Placement Readiness Analyser** is an educational software platform designed to help university and college students evaluate their preparation for technical placement opportunities through transparent, rule-based assessments, configurable role-skill mappings, personalised learning plans, and longitudinal progress tracking.

## 2. Vision & Objectives
- Provide students with an honest, explainable diagnostic of their current skill proficiency across Aptitude, Programming Fundamentals, Role-Specific Technical Concepts, and Interview/Portfolio Communication.
- Eliminate opaque "black-box" readiness percentages by showing exact point breakdowns, role skill weights, and explicit `Not Assessed` indicators for missing evidence.
- Translate identified skill gaps into prioritised, time-calibrated learning activities.
- Enable students to measure real score progression across repeated assessment attempts.

## 3. Scope
### In Scope (MVP & Core Release v1.0.0)
- Student profile creation, update, and self-service data deletion.
- 6 configurable target job roles with weighted skill matrices.
- 4 active diagnostic assessments covering 10 technical and career skills.
- Backend objective grading engine supporting single-choice (`mcq`), multiple-select (`multi_select` with partial credit), and short-text (`short_text`) questions.
- Rule-based recommendation engine with optional schema-validated AI study-tip enrichment.
- Readiness dashboard and progress tracker backed by SQLite/SQLAlchemy persistence.

### Out of Scope / Exclusions
- Predicting company-specific hiring probabilities or guaranteeing employment outcomes.
- Automated execution of untrusted arbitrary user code in a sandboxed container (objective code-reading and technical concept items are used in v1.0.0).
- Collection or scoring of protected demographic attributes.

## 4. Stakeholders
- **Students (Primary Users):** Use assessments, dashboards, and learning plans to structure placement preparation.
- **Career Mentors / Educators:** Review role-skill mappings and assessment criteria.
- **Engineering & QA Team:** Maintain scoring rules, question bank versions, security controls, and automated tests.
