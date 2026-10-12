import type {
  AssessmentDetail,
  AssessmentSummary,
  AttemptResult,
  AuthTokenResponse,
  DashboardData,
  HealthStatus,
  JobRoleDetail,
  JobRoleSummary,
  ProgressData,
  RecommendationItem,
  SkillItem,
  StartAttemptResponse,
  StudentProfile,
  StudentProfileInput,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const TOKEN_STORAGE_KEY = 'spra_access_token';
const STUDENT_ID_STORAGE_KEY = 'spra_student_id';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function getStudentSessionId(): string {
  let id = localStorage.getItem(STUDENT_ID_STORAGE_KEY);
  if (!id) {
    id = 'student-local-1';
    localStorage.setItem(STUDENT_ID_STORAGE_KEY, id);
  }
  return id;
}

export function setStudentSessionId(id: string): void {
  localStorage.setItem(STUDENT_ID_STORAGE_KEY, id.trim() || 'student-local-1');
}

function buildHeaders(includeJson = true): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers['Content-Type'] = 'application/json';
  }
  const token = getStoredToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  } else {
    headers['X-Student-ID'] = getStudentSessionId();
  }
  return headers;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...buildHeaders(options.body !== undefined),
      ...(options.headers || {}),
    },
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof payload.detail === 'string'
        ? payload.detail
        : Array.isArray(payload.detail)
          ? payload.detail.map((e: { msg?: string }) => e.msg || JSON.stringify(e)).join('; ')
          : 'Request failed. Please check your input and try again.';
    throw new Error(detail);
  }
  return payload as T;
}

export function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>('/health');
}

export function registerStudent(
  display_name: string,
  login_identifier: string,
  password: string,
): Promise<AuthTokenResponse> {
  return request<AuthTokenResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ display_name, login_identifier, password }),
  });
}

export function loginStudent(
  login_identifier: string,
  password: string,
): Promise<AuthTokenResponse> {
  return request<AuthTokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ login_identifier, password }),
  });
}

export function fetchRoles(): Promise<JobRoleSummary[]> {
  return request<JobRoleSummary[]>('/roles');
}

export function fetchRoleDetail(roleId: string): Promise<JobRoleDetail> {
  return request<JobRoleDetail>(`/roles/${encodeURIComponent(roleId)}`);
}

export function fetchSkills(): Promise<SkillItem[]> {
  return request<SkillItem[]>('/skills');
}

export function fetchProfile(): Promise<StudentProfile> {
  return request<StudentProfile>('/profile');
}

export function saveProfile(payload: StudentProfileInput): Promise<StudentProfile> {
  return request<StudentProfile>('/profile', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function deleteProfileData(): Promise<{ status: string; user_id: string; detail: string }> {
  return request<{ status: string; user_id: string; detail: string }>('/profile', {
    method: 'DELETE',
  });
}

export function fetchAssessments(): Promise<AssessmentSummary[]> {
  return request<AssessmentSummary[]>('/assessments');
}

export function fetchAssessmentDetail(assessmentId: string): Promise<AssessmentDetail> {
  return request<AssessmentDetail>(`/assessments/${encodeURIComponent(assessmentId)}`);
}

export function startAssessmentAttempt(assessmentId: string): Promise<StartAttemptResponse> {
  return request<StartAttemptResponse>(`/assessments/${encodeURIComponent(assessmentId)}/attempts`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

export function submitAssessmentAttempt(
  attemptId: string,
  answers: Array<{ question_id: string; answer_value: string | string[] }>,
  requireAllQuestions = false,
): Promise<AttemptResult> {
  return request<AttemptResult>(`/attempts/${encodeURIComponent(attemptId)}/submit`, {
    method: 'POST',
    body: JSON.stringify({
      answers,
      require_all_questions: requireAllQuestions,
    }),
  });
}

export function fetchAttemptResult(attemptId: string): Promise<AttemptResult> {
  return request<AttemptResult>(`/attempts/${encodeURIComponent(attemptId)}/results`);
}

export function fetchDashboard(): Promise<DashboardData> {
  return request<DashboardData>('/dashboard');
}

export function fetchRecommendations(refresh = false): Promise<RecommendationItem[]> {
  return request<RecommendationItem[]>(`/recommendations${refresh ? '?refresh=true' : ''}`);
}

export function updateRecommendationStatus(
  recommendationId: string,
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed',
): Promise<RecommendationItem> {
  return request<RecommendationItem>(`/recommendations/${encodeURIComponent(recommendationId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

export function fetchProgress(): Promise<ProgressData> {
  return request<ProgressData>('/progress');
}

export function logPracticeSession(
  skill_id: string,
  duration_minutes: number,
  notes: string,
): Promise<{ status: string; skill_id: string; skill_name: string; duration_minutes: number; note: string }> {
  return request('/progress/practice', {
    method: 'POST',
    body: JSON.stringify({ skill_id, duration_minutes, notes }),
  });
}
