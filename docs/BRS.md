# Business Requirements Specification (BRS)

## 1. Business Problem
Students preparing for technical placements often study without a clear mapping between their target job role and the skills required for that role. Existing preparation tools frequently either offer unorganised question lists or display arbitrary readiness scores without explaining how those scores were calculated or what evidence is missing.

## 2. Business Goals
1. **Clarity in Role Expectations:** Help students understand which skills are relevant to their target job role and how those skills are weighted.
2. **Evidence-Based Self-Assessment:** Provide structured assessments that measure performance per skill area using transparent scoring rules.
3. **Actionable Gap Closure:** Recommend concrete learning activities tied directly to low-scoring or unassessed skills and calibrated to the student's weekly available preparation hours.
4. **Longitudinal Progress Visibility:** Allow students to retake assessments, log study sessions, and compare scores across compatible assessment versions.
5. **Ethical & Honest Reporting:** Never represent readiness scores as hiring guarantees or probabilities, and never penalise or score students using demographic attributes.

## 3. Key Business Rules
- **BR-01 (No Fabricated Scores):** Unassessed skills must be reported as `Not Assessed` (`null`), never silently assigned `0%` or `100%`.
- **BR-02 (Complete Evidence for Overall Role Score):** An overall role readiness percentage is calculated only when all skills required for the selected role have been assessed; otherwise, the status must be `Incomplete Assessment Evidence`.
- **BR-03 (Activity Completion != Skill Mastery):** Completing a recommended learning activity records study effort in the progress tracker but does not alter skill scores until the student retakes an assessment.
- **BR-04 (Non-Guarantee Disclaimer):** All readiness dashboards and result reports must clearly explain that scores are preparation guidance, not hiring predictions.
