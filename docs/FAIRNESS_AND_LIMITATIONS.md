# Fairness Principles and System Limitations

## 1. Fairness Guarantees
1. **Zero Protected Attribute Collection or Inference:** The application never collects, infers, or scores caste, religion, gender, age, disability, ethnicity, socioeconomic status, or institution tier.
2. **Identical Transparent Criteria:** Two students who select the same target job role and submit the same assessment answers receive identical points, skill scores, and readiness categories.
3. **Constructive Educational Framing:** Readiness categories (`Insufficient Assessment Evidence`, `Needs More Preparation`, `Developing`, `Progressing Well`, `Strong Performance on Assessed Areas`) are framed as constructive study guidance—never labelling a student as "unemployable" or "incapable."
4. **Editable Profile Information:** Students can update their target role, skills, and preparation time at any time, and recommendations automatically recalibrate.

## 2. Known System Limitations
1. **Not a Hiring Predictor:** Placement readiness scores measure performance on the application's configured question bank only. Real recruitment outcomes depend on employer-specific requirements, live coding interviews, team fit, market conditions, and candidate pools outside this system's scope.
2. **Non-Psychometric Practice Items:** The built-in question bank consists of authored computer science, aptitude, and career-readiness practice items (`v1.0.0`); they are not psychometrically calibrated standardized examinations.
3. **Role-Skill Profiles are General Benchmarks:** While each of the 6 supported roles (`Software Developer`, `Python Developer`, `Data Analyst`, `AI/ML Engineer`, `Web Developer`, `QA Engineer`) defines transparent skill weights, individual companies may weight skills differently for the same job title.
4. **Activity Completion Does Not Equal Mastery:** Marking a recommended learning activity as `completed` or logging a practice session records study effort. Verified skill scores update only when the student retakes an assessment covering that skill.
