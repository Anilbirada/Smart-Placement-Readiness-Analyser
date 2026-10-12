# Assessment & Readiness Scoring Rules

## 1. Question Grading Policy (`backend/app/assessments/engine.py`)

All objective question grading is performed on the backend during `POST /api/v1/attempts/{attempt_id}/submit`.

1. **Multiple-Choice (`mcq`):**
   - Full `score_value` is awarded if the selected option identifier matches the single correct option.
   - `0.0` points are awarded for an incorrect option or unanswered question.
   - Submitting an option identifier not in the question's configured options raises `422 Unprocessable Entity`.

2. **Multiple-Select (`multi_select`):**
   - Supports **proportional partial credit**:
     - If any incorrect option is selected: `0.0` points are awarded (prevents selecting all options to game partial credit).
     - If $k$ of $m$ correct options are selected and $0$ incorrect options are selected:
       $$\text{Awarded Score} = \text{round}\left(\frac{k}{m} \times \text{score\_value},\ 2\right)$$
   - Selecting all $m$ correct options with no wrong options awards `100%` of `score_value`.

3. **Short-Text (`short_text`):**
   - Input is trimmed, whitespace-normalised, and compared case-insensitively against the list of accepted technical terms.

4. **Unanswered Questions Policy:**
   - When `require_all_questions = false` (default), unanswered items receive `0.0` points with explicit feedback: `"Question was left unanswered (0 points awarded per grading policy)."`
   - When `require_all_questions = true`, missing answers return `422 Unprocessable Entity` listing the missing question IDs.

---

## 2. Assessment Area & Skill Score Formula

For each assessment attempt and each skill covered within that attempt:

$$\text{Area or Skill Score (\%)} = \text{round}\left(\frac{\sum \text{Earned Points}}{\sum \text{Maximum Available Points}} \times 100,\ 2\right)$$

---

## 3. Target Role Readiness & Missing Evidence Rules

Each active target job role defines $N$ required skills with importance weights $w_1, w_2, \dots, w_N$ validated such that:

$$w_i \in (0, 1] \quad \text{and} \quad \sum_{i=1}^{N} w_i = 1.0$$

### Separation of Concepts
1. **Skill Assessment Status:**
   - If the student has completed at least one assessment covering skill $i$, `assessment_status = "Assessed"` and `current_score` is the latest assessed score $s_i \in [0, 100]$.
   - If the student has **not** completed any assessment covering skill $i$, `assessment_status = "Not Assessed"` and `current_score = null`. **Missing evidence is never silently treated as `0%` or `100%`.**

2. **Assessed-Area Weighted Score:**
   - Across the subset of assessed role skills $A \subseteq \{1, \dots, N\}$:
     $$\text{Assessed Area Weighted Score} = \frac{\sum_{i \in A} s_i \cdot w_i}{\sum_{i \in A} w_i}$$

3. **Overall Role Readiness Score:**
   - Computed **only** when all required skills for the target role have been assessed ($|A| = N$, coverage $= 100\%$):
     $$\text{Overall Role Readiness Score} = \sum_{i=1}^{N} s_i \cdot w_i$$
   - When $|A| < N$, `overall_role_readiness_score` is `null`, `readiness_status = "Incomplete Assessment Evidence"`, and `readiness_category = "Insufficient Assessment Evidence"`.

---

## 4. Configurable Guidance Categories

When assessment evidence is complete:
- **`< 45.0%`:** `Needs More Preparation`
- **`45.0% – 64.99%`:** `Developing`
- **`65.0% – 79.99%`:** `Progressing Well`
- **`>= 80.0%`:** `Strong Performance on Assessed Areas`
- **Incomplete or missing evidence:** `Insufficient Assessment Evidence`

> **Mandatory Disclaimer:** These categories are educational preparation indicators based on completed practice items. They never represent a probability of being hired.
