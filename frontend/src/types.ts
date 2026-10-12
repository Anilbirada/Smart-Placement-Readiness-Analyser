export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  scoring_model_version: string;
  question_bank_version: string;
  ai_enrichment_enabled: boolean;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  display_name: string;
  login_identifier: string;
}

export interface SkillItem {
  id: string;
  name: string;
  category: string;
  description: string;
  active: boolean;
}

export interface RoleSkillRequirement {
  skill_id: string;
  skill_name: string;
  skill_category: string;
  skill_description: string;
  weight: number;
  expected_level: number;
  rationale: string;
  version: string;
}

export interface JobRoleSummary {
  id: string;
  name: string;
  description: string;
  version: string;
  active: boolean;
  skill_count: number;
}

export interface JobRoleDetail {
  id: string;
  name: string;
  description: string;
  version: string;
  active: boolean;
  total_weight: number;
  skills: RoleSkillRequirement[];
  disclaimer: string;
}

export interface StudentProfile {
  id: string;
  user_id: string;
  display_name: string;
  education_level: string;
  target_role_id: string;
  target_role_name: string;
  current_skills: string[];
  preferred_languages: string[];
  preparation_goal: string;
  available_preparation_time: number;
  created_at: string;
  updated_at: string;
}

export interface StudentProfileInput {
  display_name: string;
  education_level: string;
  target_role_id: string;
  current_skills: string[];
  preferred_languages: string[];
  preparation_goal: string;
  available_preparation_time: number;
}

export interface QuestionOption {
  option_identifier: string;
  option_text: string;
}

export interface QuestionPublic {
  id: string;
  skill_id: string;
  skill_name: string;
  topic: string;
  skill_area: string;
  question_type: 'mcq' | 'multi_select' | 'short_text';
  question_text: string;
  difficulty: string;
  score_value: number;
  version: string;
  options: QuestionOption[];
}

export interface AssessmentSummary {
  id: string;
  title: string;
  description: string;
  instructions: string;
  assessment_type: string;
  skill_area: string;
  time_limit_minutes: number;
  version: string;
  status: string;
  question_count: number;
  total_points: number;
  covered_skills: string[];
}

export interface AssessmentDetail {
  id: string;
  title: string;
  description: string;
  instructions: string;
  assessment_type: string;
  skill_area: string;
  time_limit_minutes: number;
  version: string;
  status: string;
  total_points: number;
  questions: QuestionPublic[];
}

export interface StartAttemptResponse {
  attempt_id: string;
  assessment_id: string;
  assessment_title: string;
  assessment_version: string;
  started_at: string;
  status: string;
}

export interface QuestionResultItem {
  question_id: string;
  topic: string;
  skill_id: string;
  skill_name: string;
  question_type: string;
  question_text: string;
  submitted_answer: string | string[] | null;
  awarded_score: number;
  maximum_score: number;
  is_correct: boolean;
  feedback: string;
  explanation: string;
}

export interface SkillScoreBreakdownItem {
  skill_id: string;
  skill_name: string;
  score: number | null;
  earned_points: number;
  maximum_points: number;
  assessment_status: string;
  evidence_summary: string;
}

export interface AttemptResult {
  result_id: string;
  attempt_id: string;
  assessment_id: string;
  assessment_title: string;
  assessment_version: string;
  scoring_version: string;
  submitted_at: string;
  overall_score: number | null;
  earned_points: number;
  maximum_points: number;
  answered_questions: number;
  total_questions: number;
  assessment_status: string;
  readiness_category: string;
  result_summary: string;
  scoring_formula_explanation: string;
  strengths: string[];
  improvement_areas: string[];
  skill_results: SkillScoreBreakdownItem[];
  question_results: QuestionResultItem[];
  limitations_note: string;
}

export interface RoleSkillReadinessItem {
  skill_id: string;
  skill_name: string;
  skill_category: string;
  role_weight: number;
  expected_level: number;
  current_score: number | null;
  gap: number | null;
  assessment_status: 'Assessed' | 'Not Assessed';
  status_label: 'Meets Target' | 'Needs Improvement' | 'Not Assessed';
  evidence_summary: string;
}

export interface RecommendationItem {
  id: string;
  skill_id: string;
  skill_name: string;
  learning_activity_id: string;
  activity_title: string;
  activity_description: string;
  activity_type: string;
  resource_url: string | null;
  estimated_effort: string;
  effort_hours: number;
  reason: string;
  evidence_summary: string;
  priority: 'High' | 'Medium' | 'Low';
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed';
  is_ai_enhanced: boolean;
  ai_note: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface DashboardData {
  user_id: string;
  display_name: string;
  has_profile: boolean;
  has_completed_assessments: boolean;
  profile: StudentProfile | null;
  target_role: JobRoleDetail | null;
  readiness_status: string;
  readiness_category: string;
  overall_role_readiness_score: number | null;
  assessed_area_weighted_score: number | null;
  assessed_weight_coverage_percent: number;
  assessed_skills_count: number;
  total_role_skills_count: number;
  incomplete_evidence_explanation: string;
  scoring_methodology_note: string;
  role_skill_readiness: RoleSkillReadinessItem[];
  recent_attempts: Array<{
    attempt_id: string;
    assessment_id: string;
    assessment_title: string;
    assessment_version: string;
    submitted_at: string;
    overall_score: number | null;
    readiness_category: string;
  }>;
  outstanding_recommendations: RecommendationItem[];
  completed_activities_count: number;
  next_suggested_action: {
    title: string;
    description: string;
    action_target: string;
  };
  disclaimer: string;
}

export interface AttemptComparison {
  assessment_id: string;
  assessment_title: string;
  earlier_attempt_id: string;
  earlier_version: string;
  earlier_submitted_at: string;
  earlier_score: number | null;
  later_attempt_id: string;
  later_version: string;
  later_submitted_at: string;
  later_score: number | null;
  comparable: boolean;
  score_delta: number | null;
  comparison_note: string;
  skill_deltas: Array<{
    skill_id: string;
    skill_name: string;
    earlier_score: number;
    later_score: number;
    delta: number;
  }>;
}

export interface ProgressData {
  user_id: string;
  total_attempts_submitted: number;
  completed_recommendations_count: number;
  pending_recommendations_count: number;
  practice_sessions_logged: number;
  attempt_history: Array<{
    attempt_id: string;
    assessment_id: string;
    assessment_title: string;
    assessment_version: string;
    scoring_version: string;
    submitted_at: string;
    overall_score: number | null;
    earned_points: number;
    maximum_points: number;
    readiness_category: string;
  }>;
  skill_progress_summary: Array<{
    skill_id: string;
    skill_name: string;
    attempts_count: number;
    initial_score: number;
    latest_score: number;
    score_change: number;
    trend: string;
  }>;
  attempt_comparisons: AttemptComparison[];
  progress_events: Array<{
    id: string;
    event_type: string;
    reference_id: string | null;
    event_timestamp: string;
    metadata: Record<string, unknown>;
  }>;
  mastery_note: string;
}
