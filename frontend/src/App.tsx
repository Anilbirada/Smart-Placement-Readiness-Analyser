import React, { useEffect, useState } from 'react';
import {
  deleteProfileData,
  fetchAssessmentDetail,
  fetchAssessments,
  fetchAttemptResult,
  fetchDashboard,
  fetchHealth,
  fetchProgress,
  fetchRecommendations,
  fetchRoleDetail,
  fetchRoles,
  fetchSkills,
  getStoredToken,
  getStudentSessionId,
  loginStudent,
  logPracticeSession,
  registerStudent,
  saveProfile,
  setStoredToken,
  setStudentSessionId,
  startAssessmentAttempt,
  submitAssessmentAttempt,
  updateRecommendationStatus,
} from './services/api';
import type {
  AssessmentDetail,
  AssessmentSummary,
  AttemptResult,
  DashboardData,
  HealthStatus,
  JobRoleDetail,
  JobRoleSummary,
  ProgressData,
  RecommendationItem,
  SkillItem,
} from './types';

type TabKey =
  | 'landing'
  | 'dashboard'
  | 'profile'
  | 'roles'
  | 'assessments'
  | 'results'
  | 'learning-plan'
  | 'progress';

function getCategoryBadgeClass(category: string): string {
  if (category === 'Strong Performance on Assessed Areas') return 'badge badge-success';
  if (category === 'Progressing Well') return 'badge badge-info';
  if (category === 'Developing') return 'badge badge-warning';
  if (category === 'Needs More Preparation') return 'badge badge-danger';
  return 'badge badge-neutral';
}

export function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('landing');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [roles, setRoles] = useState<JobRoleSummary[]>([]);
  const [selectedRoleDetail, setSelectedRoleDetail] = useState<JobRoleDetail | null>(null);
  const [skills, setSkills] = useState<SkillItem[]>([]);
  const [assessments, setAssessments] = useState<AssessmentSummary[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [progress, setProgress] = useState<ProgressData | null>(null);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Auth / Session state
  const [sessionId, setSessionIdState] = useState<string>(getStudentSessionId());
  const [hasToken, setHasToken] = useState<boolean>(Boolean(getStoredToken()));
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');
  const [authName, setAuthName] = useState<string>('');
  const [authLoginId, setAuthLoginId] = useState<string>('');
  const [authPassword, setAuthPassword] = useState<string>('');

  // Profile form state
  const [displayName, setDisplayName] = useState<string>('');
  const [educationLevel, setEducationLevel] = useState<string>('B.E. / B.Tech Final Year');
  const [targetRoleId, setTargetRoleId] = useState<string>('role-swe');
  const [currentSkillsInput, setCurrentSkillsInput] = useState<string>('Python, SQL');
  const [preferredLanguagesInput, setPreferredLanguagesInput] = useState<string>('Python, TypeScript');
  const [preparationGoal, setPreparationGoal] = useState<string>(
    'Identify core technical gaps and structure weekly placement preparation.',
  );
  const [availablePrepTime, setAvailablePrepTime] = useState<number>(10);

  // Active Assessment Attempt state
  const [activeAssessment, setActiveAssessment] = useState<AssessmentDetail | null>(null);
  const [activeAttemptId, setActiveAttemptId] = useState<string | null>(null);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState<number>(0);
  const [answersMap, setAnswersMap] = useState<Record<string, string | string[]>>({});
  const [confirmSubmit, setConfirmSubmit] = useState<boolean>(false);
  const [latestResult, setLatestResult] = useState<AttemptResult | null>(null);

  // Practice Logger form state
  const [practiceSkillId, setPracticeSkillId] = useState<string>('skill-aptitude');
  const [practiceDuration, setPracticeDuration] = useState<number>(45);
  const [practiceNotes, setPracticeNotes] = useState<string>('');

  useEffect(() => {
    void loadInitialData();
  }, [sessionId, hasToken]);

  async function loadInitialData() {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [healthData, rolesData, skillsData, assessmentsData, dashData] = await Promise.all([
        fetchHealth(),
        fetchRoles(),
        fetchSkills(),
        fetchAssessments(),
        fetchDashboard(),
      ]);
      setHealth(healthData);
      setRoles(rolesData);
      setSkills(skillsData);
      setAssessments(assessmentsData);
      setDashboard(dashData);

      if (skillsData.length > 0 && !practiceSkillId) {
        setPracticeSkillId(skillsData[0].id);
      }

      if (dashData.profile) {
        setDisplayName(dashData.profile.display_name);
        setEducationLevel(dashData.profile.education_level);
        setTargetRoleId(dashData.profile.target_role_id);
        setCurrentSkillsInput(dashData.profile.current_skills.join(', '));
        setPreferredLanguagesInput(dashData.profile.preferred_languages.join(', '));
        setPreparationGoal(dashData.profile.preparation_goal);
        setAvailablePrepTime(dashData.profile.available_preparation_time);
      }

      const initialRoleId = dashData.profile?.target_role_id || rolesData[0]?.id || 'role-swe';
      if (initialRoleId) {
        const roleDetail = await fetchRoleDetail(initialRoleId);
        setSelectedRoleDetail(roleDetail);
      }

      const [recsData, progData] = await Promise.all([fetchRecommendations(), fetchProgress()]);
      setRecommendations(recsData);
      setProgress(progData);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Unable to connect to backend service.');
    } finally {
      setLoading(false);
    }
  }

  async function handleInspectRole(roleId: string) {
    setErrorMessage(null);
    try {
      const detail = await fetchRoleDetail(roleId);
      setSelectedRoleDetail(detail);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Unable to load role details.');
    }
  }

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    setStatusMessage(null);

    if (displayName.trim().length < 2) {
      setErrorMessage('Please enter a display name of at least 2 characters.');
      return;
    }
    if (preparationGoal.trim().length < 5) {
      setErrorMessage('Please enter a preparation goal of at least 5 characters.');
      return;
    }
    if (availablePrepTime < 1 || availablePrepTime > 80) {
      setErrorMessage('Available preparation time must be between 1 and 80 hours per week.');
      return;
    }

    setLoading(true);
    try {
      const current_skills = currentSkillsInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      const preferred_languages = preferredLanguagesInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      await saveProfile({
        display_name: displayName.trim(),
        education_level: educationLevel.trim(),
        target_role_id: targetRoleId,
        current_skills,
        preferred_languages,
        preparation_goal: preparationGoal.trim(),
        available_preparation_time: Number(availablePrepTime),
      });

      await loadInitialData();
      setStatusMessage('Student profile and target role saved. Recommendations have been updated.');
      setActiveTab('dashboard');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to save profile.');
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteProfile() {
    setErrorMessage(null);
    setStatusMessage(null);
    setLoading(true);
    try {
      await deleteProfileData();
      setStoredToken(null);
      setHasToken(false);
      setDisplayName('');
      await loadInitialData();
      setStatusMessage('Your profile, attempts, and recommendations have been permanently deleted.');
      setActiveTab('landing');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to delete profile.');
    } finally {
      setLoading(false);
    }
  }

  async function handleStartAssessment(assessmentId: string) {
    setErrorMessage(null);
    setStatusMessage(null);
    setLoading(true);
    try {
      const [detail, attempt] = await Promise.all([
        fetchAssessmentDetail(assessmentId),
        startAssessmentAttempt(assessmentId),
      ]);
      setActiveAssessment(detail);
      setActiveAttemptId(attempt.attempt_id);
      setCurrentQuestionIdx(0);
      setAnswersMap({});
      setConfirmSubmit(false);
      setActiveTab('assessments');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Could not start assessment.');
    } finally {
      setLoading(false);
    }
  }

  function handleSelectMcq(questionId: string, optionId: string) {
    setAnswersMap((prev) => ({ ...prev, [questionId]: optionId }));
  }

  function handleToggleMultiSelect(questionId: string, optionId: string) {
    setAnswersMap((prev) => {
      const current = Array.isArray(prev[questionId]) ? (prev[questionId] as string[]) : [];
      const next = current.includes(optionId)
        ? current.filter((item) => item !== optionId)
        : [...current, optionId];
      return { ...prev, [questionId]: next };
    });
  }

  function handleShortTextChange(questionId: string, text: string) {
    setAnswersMap((prev) => ({ ...prev, [questionId]: text }));
  }

  async function handleSubmitAssessment() {
    if (!activeAssessment || !activeAttemptId) return;
    setErrorMessage(null);
    setLoading(true);
    try {
      const formattedAnswers = Object.entries(answersMap).map(([question_id, answer_value]) => ({
        question_id,
        answer_value,
      }));
      const result = await submitAssessmentAttempt(activeAttemptId, formattedAnswers, false);
      setLatestResult(result);
      setActiveAssessment(null);
      setActiveAttemptId(null);
      setConfirmSubmit(false);
      await loadInitialData();
      setStatusMessage(`Submitted ${result.assessment_title}. Backend score calculated.`);
      setActiveTab('results');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to submit assessment.');
    } finally {
      setLoading(false);
    }
  }

  async function handleViewAttemptResult(attemptId: string) {
    setErrorMessage(null);
    setLoading(true);
    try {
      const result = await fetchAttemptResult(attemptId);
      setLatestResult(result);
      setActiveTab('results');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Unable to load attempt results.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRecommendationStatusChange(
    recId: string,
    nextStatus: 'pending' | 'in_progress' | 'completed' | 'dismissed',
  ) {
    setErrorMessage(null);
    try {
      await updateRecommendationStatus(recId, nextStatus);
      const [recsData, dashData, progData] = await Promise.all([
        fetchRecommendations(),
        fetchDashboard(),
        fetchProgress(),
      ]);
      setRecommendations(recsData);
      setDashboard(dashData);
      setProgress(progData);
      setStatusMessage(`Updated learning activity status to '${nextStatus}'.`);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to update recommendation.');
    }
  }

  async function handleLogPractice(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    setStatusMessage(null);
    if (practiceNotes.trim().length < 3) {
      setErrorMessage('Please enter a brief note describing what you practiced (at least 3 characters).');
      return;
    }
    try {
      const res = await logPracticeSession(practiceSkillId, Number(practiceDuration), practiceNotes.trim());
      setPracticeNotes('');
      const progData = await fetchProgress();
      setProgress(progData);
      setStatusMessage(res.note);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Could not log practice session.');
    }
  }

  async function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    try {
      const res =
        authMode === 'register'
          ? await registerStudent(authName, authLoginId, authPassword)
          : await loginStudent(authLoginId, authPassword);
      setStoredToken(res.access_token);
      setHasToken(true);
      setShowAuthModal(false);
      setAuthPassword('');
      setStatusMessage(`Signed in as ${res.display_name} (${res.login_identifier}).`);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Authentication failed.');
    }
  }

  function handleLogout() {
    setStoredToken(null);
    setHasToken(false);
    setStatusMessage('Signed out of token session; switched to local student workspace.');
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div>
          <p className="brand-eyebrow">Career Assessment & Skill-Gap Intelligence</p>
          <h1 className="brand-title">Smart Placement Readiness Analyser</h1>
          <p className="brand-subtitle">
            Evidence-based diagnostic assessments, role-skill mapping, and personalised study planning
          </p>
        </div>
        <div className="header-controls">
          <div className="session-badge" aria-label="System and session status">
            <span>
              Engine v{health?.scoring_model_version ?? '1.0.0'} |{' '}
              {dashboard?.has_profile ? dashboard.display_name : sessionId}
            </span>
          </div>
          {!hasToken ? (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowAuthModal(!showAuthModal)}
            >
              {showAuthModal ? 'Close Sign-In' : 'Account Sign-In / Register'}
            </button>
          ) : (
            <button type="button" className="btn btn-secondary btn-sm" onClick={handleLogout}>
              Sign Out
            </button>
          )}
        </div>
      </header>

      {/* Mandatory Transparency & Non-Guarantee Disclaimer Banner */}
      <div className="disclaimer-banner" role="note">
        <strong>Transparency & Fairness Notice:</strong> Readiness scores and categories are educational
        preparation guidance calculated strictly from completed assessment evidence. They do{' '}
        <strong>not</strong> predict hiring probabilities, guarantee employment, or replace company-specific
        interview evaluations. Unassessed skills are explicitly marked <em>Not Assessed</em>.
      </div>

      {/* Optional Account Modal */}
      {showAuthModal && (
        <section className="panel" aria-label="Student Account Authentication">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>{authMode === 'register' ? 'Create Student Account' : 'Student Sign-In'}</h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                className={`btn btn-sm ${authMode === 'register' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setAuthMode('register')}
              >
                Register
              </button>
              <button
                type="button"
                className={`btn btn-sm ${authMode === 'login' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setAuthMode('login')}
              >
                Login
              </button>
            </div>
          </div>
          <form onSubmit={handleAuthSubmit} className="grid-3">
            {authMode === 'register' && (
              <div className="form-group">
                <label htmlFor="auth-name" className="form-label">
                  Display Name
                </label>
                <input
                  id="auth-name"
                  className="form-input"
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  placeholder="e.g., Aarav Sharma"
                  required
                />
              </div>
            )}
            <div className="form-group">
              <label htmlFor="auth-login" className="form-label">
                Login Identifier (Email or Roll ID)
              </label>
              <input
                id="auth-login"
                className="form-input"
                value={authLoginId}
                onChange={(e) => setAuthLoginId(e.target.value)}
                placeholder="student@college.edu"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="auth-password" className="form-label">
                Password (min 6 chars)
              </label>
              <input
                id="auth-password"
                type="password"
                className="form-input"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                required
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', marginBottom: 18 }}>
              <button type="submit" className="btn btn-primary">
                {authMode === 'register' ? 'Register & Sign In' : 'Sign In'}
              </button>
            </div>
          </form>
          <div style={{ marginTop: 8, paddingTop: 12, borderTop: '1px solid #1e293b' }}>
            <label htmlFor="workspace-session-id" className="form-label">
              Or switch local isolated Student Workspace ID:
            </label>
            <div style={{ display: 'flex', gap: 10, maxWidth: 420 }}>
              <input
                id="workspace-session-id"
                className="form-input"
                value={sessionId}
                onChange={(e) => setSessionIdState(e.target.value)}
              />
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setStudentSessionId(sessionId);
                  void loadInitialData();
                }}
              >
                Switch ID
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Navigation Tabs */}
      <nav className="nav-tabs" aria-label="Main Application Sections">
        <button
          type="button"
          className={`nav-tab ${activeTab === 'landing' ? 'active' : ''}`}
          onClick={() => setActiveTab('landing')}
        >
          Overview
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          Readiness Dashboard
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          Student Profile
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'roles' ? 'active' : ''}`}
          onClick={() => setActiveTab('roles')}
        >
          Target Roles & Skills
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'assessments' ? 'active' : ''}`}
          onClick={() => setActiveTab('assessments')}
        >
          Assessment Centre
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          Results & Skill Gaps
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'learning-plan' ? 'active' : ''}`}
          onClick={() => setActiveTab('learning-plan')}
        >
          Learning Plan ({recommendations.filter((r) => r.status !== 'completed').length})
        </button>
        <button
          type="button"
          className={`nav-tab ${activeTab === 'progress' ? 'active' : ''}`}
          onClick={() => setActiveTab('progress')}
        >
          Progress Tracker
        </button>
      </nav>

      {errorMessage && (
        <div className="alert-error" role="alert">
          <strong>Action Required:</strong> {errorMessage}
        </div>
      )}

      {statusMessage && (
        <div className="alert-success" role="status">
          {statusMessage}
        </div>
      )}

      {/* ============================================================
          SCREEN A: LANDING PAGE
         ============================================================ */}
      {activeTab === 'landing' && (
        <main>
          <section className="panel">
            <span className="badge badge-info" style={{ marginBottom: 12 }}>
              Transparent Rule-Based Placement Preparation
            </span>
            <h2 style={{ fontSize: '1.85rem', marginBottom: 12 }}>
              Measure Your Placement Preparation with Auditable Evidence
            </h2>
            <p style={{ color: '#cbd5e1', maxWidth: 820, fontSize: '1.03rem' }}>
              Students preparing for campus and entry-level technical placements often struggle to know which
              skills matter for their target role, which topics need deeper practice, and how to organise their
              available study hours. <strong>Smart Placement Readiness Analyser</strong> maps your target job role
              to transparent skill weights, evaluates your knowledge through structured assessments, highlights
              verified strengths and skill gaps, and builds an actionable learning plan.
            </p>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 20 }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setActiveTab(dashboard?.has_profile ? 'dashboard' : 'profile')}
              >
                {dashboard?.has_profile ? 'Go to Readiness Dashboard' : 'Get Started: Create Student Profile'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setActiveTab('roles')}>
                Explore Supported Job Roles ({roles.length})
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setActiveTab('assessments')}>
                Browse Assessment Centre ({assessments.length})
              </button>
            </div>
          </section>

          <div className="grid-2">
            <section className="panel">
              <h3>Main Assessment Pillars</h3>
              <ul style={{ paddingLeft: 20, color: '#cbd5e1', display: 'grid', gap: 10 }}>
                <li>
                  <strong>Aptitude & Logical Reasoning:</strong> Quantitative rate problems, probability, and
                  deductive logic used in initial screening.
                </li>
                <li>
                  <strong>Programming & Core CS Fundamentals:</strong> Control flow, mutability, complexity
                  analysis, hash tables, and graph traversals.
                </li>
                <li>
                  <strong>Role-Specific Technical Concepts:</strong> Python idioms, REST API idempotency, SQL
                  aggregations, ML leakage prevention, Web accessibility, and QA boundary testing.
                </li>
                <li>
                  <strong>Communication & Portfolio Readiness:</strong> Structured STAR behavioral responses and
                  evidence-backed resume documentation.
                </li>
              </ul>
            </section>

            <section className="panel">
              <h3>How Readiness Scoring Works</h3>
              <p style={{ color: '#cbd5e1' }}>
                Every score is computed on the backend using documented rules:
              </p>
              <ul style={{ paddingLeft: 20, color: '#cbd5e1', display: 'grid', gap: 10 }}>
                <li>
                  <strong>Area Score:</strong> <code>(Points Earned / Maximum Available Points) × 100</code>.
                </li>
                <li>
                  <strong>Weighted Role Score:</strong> Sum of each assessed role skill score multiplied by its
                  documented importance weight.
                </li>
                <li>
                  <strong>Honest Missing-Evidence Policy:</strong> Unassessed skills are marked{' '}
                  <em>Not Assessed</em>—never silently converted to 0% or 100%.
                </li>
                <li>
                  <strong>Guidance Only:</strong> Readiness categories guide your study plan and never claim to
                  predict employer hiring decisions.
                </li>
              </ul>
            </section>
          </div>
        </main>
      )}

      {/* ============================================================
          SCREEN B: STUDENT DASHBOARD
         ============================================================ */}
      {activeTab === 'dashboard' && (
        <main>
          {!dashboard?.has_profile ? (
            <section className="panel">
              <h2>Welcome to Your Placement Readiness Dashboard</h2>
              <p style={{ color: '#cbd5e1' }}>
                {dashboard?.incomplete_evidence_explanation ||
                  'No student profile has been configured yet. Create your profile and select a target role to begin.'}
              </p>
              <button type="button" className="btn btn-primary" onClick={() => setActiveTab('profile')}>
                Configure Student Profile & Target Role
              </button>
            </section>
          ) : (
            <>
              <div className="grid-4" style={{ marginBottom: 24 }}>
                <div className="metric-card">
                  <span className="metric-label">Selected Target Role</span>
                  <p className="metric-value" style={{ fontSize: '1.3rem' }}>
                    {dashboard.profile?.target_role_name}
                  </p>
                  <p className="metric-sub">
                    Weekly Prep Budget: {dashboard.profile?.available_preparation_time} hrs/wk
                  </p>
                </div>

                <div className="metric-card">
                  <span className="metric-label">Overall Role Readiness</span>
                  <p className="metric-value">
                    {dashboard.overall_role_readiness_score !== null
                      ? `${dashboard.overall_role_readiness_score.toFixed(1)}%`
                      : 'Incomplete'}
                  </p>
                  <p className="metric-sub">
                    {dashboard.assessed_area_weighted_score !== null
                      ? `Assessed Areas Avg: ${dashboard.assessed_area_weighted_score.toFixed(1)}%`
                      : 'No assessments completed yet'}
                  </p>
                </div>

                <div className="metric-card">
                  <span className="metric-label">Role Skill Coverage</span>
                  <p className="metric-value">
                    {dashboard.assessed_skills_count} / {dashboard.total_role_skills_count}
                  </p>
                  <p className="metric-sub">
                    {dashboard.assessed_weight_coverage_percent.toFixed(0)}% of role weight assessed
                  </p>
                </div>

                <div className="metric-card">
                  <span className="metric-label">Readiness Guidance Status</span>
                  <div style={{ marginTop: 6 }}>
                    <span className={getCategoryBadgeClass(dashboard.readiness_category)}>
                      {dashboard.readiness_category}
                    </span>
                  </div>
                  <p className="metric-sub">
                    Completed Activities: {dashboard.completed_activities_count}
                  </p>
                </div>
              </div>

              {/* Next Suggested Action */}
              <section className="panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <span className="badge badge-info" style={{ marginBottom: 6 }}>
                    Next Suggested Action
                  </span>
                  <h3 style={{ margin: '4px 0' }}>{dashboard.next_suggested_action.title}</h3>
                  <p style={{ margin: 0, color: '#cbd5e1' }}>{dashboard.next_suggested_action.description}</p>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setActiveTab(dashboard.next_suggested_action.action_target as TabKey)}
                >
                  Proceed Now
                </button>
              </section>

              <div className="grid-2">
                {/* Role Skill Readiness Breakdown */}
                <section className="panel">
                  <h3>Target Role Skill Breakdown ({dashboard.profile?.target_role_name})</h3>
                  <p style={{ fontSize: '0.88rem', color: '#94a3b8', marginBottom: 16 }}>
                    {dashboard.incomplete_evidence_explanation}
                  </p>
                  {dashboard.role_skill_readiness.map((item) => (
                    <div key={item.skill_id} className="skill-row">
                      <div className="skill-row-header">
                        <div>
                          <strong>{item.skill_name}</strong>{' '}
                          <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                            (Weight: {(item.role_weight * 100).toFixed(0)}% | Target: {item.expected_level}%)
                          </span>
                        </div>
                        <span
                          className={
                            item.status_label === 'Meets Target'
                              ? 'badge badge-success'
                              : item.status_label === 'Needs Improvement'
                                ? 'badge badge-warning'
                                : 'badge badge-neutral'
                          }
                        >
                          {item.current_score !== null
                            ? `${item.current_score.toFixed(1)}% — ${item.status_label}`
                            : 'Not Assessed'}
                        </span>
                      </div>
                      <div className="progress-track" aria-label={`${item.skill_name} score bar`}>
                        <div
                          className={`progress-fill ${
                            item.current_score !== null && item.current_score >= item.expected_level
                              ? 'progress-fill-success'
                              : 'progress-fill-warning'
                          }`}
                          style={{ width: `${item.current_score !== null ? Math.min(100, item.current_score) : 0}%` }}
                        />
                      </div>
                      <p style={{ margin: '6px 0 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                        {item.evidence_summary}
                      </p>
                    </div>
                  ))}
                </section>

                {/* Recent Attempts & Top Recommendations */}
                <div>
                  <section className="panel">
                    <h3>Recent Assessment Attempts</h3>
                    {dashboard.recent_attempts.length === 0 ? (
                      <p style={{ color: '#94a3b8' }}>
                        No assessments completed yet. Visit the Assessment Centre to record your first attempt.
                      </p>
                    ) : (
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Assessment</th>
                            <th>Score</th>
                            <th>Guidance</th>
                            <th>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dashboard.recent_attempts.map((att) => (
                            <tr key={att.attempt_id}>
                              <td>
                                <strong>{att.assessment_title}</strong>
                                <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                                  v{att.assessment_version}
                                </div>
                              </td>
                              <td>{att.overall_score !== null ? `${att.overall_score.toFixed(1)}%` : 'N/A'}</td>
                              <td>
                                <span className={getCategoryBadgeClass(att.readiness_category)}>
                                  {att.readiness_category}
                                </span>
                              </td>
                              <td>
                                <button
                                  type="button"
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleViewAttemptResult(att.attempt_id)}
                                >
                                  Inspect
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </section>

                  <section className="panel">
                    <h3>Outstanding Learning Recommendations</h3>
                    {dashboard.outstanding_recommendations.length === 0 ? (
                      <p style={{ color: '#94a3b8' }}>No pending recommendations right now.</p>
                    ) : (
                      dashboard.outstanding_recommendations.slice(0, 3).map((rec) => (
                        <div key={rec.id} className="skill-row">
                          <div className="skill-row-header">
                            <strong>{rec.activity_title}</strong>
                            <span
                              className={
                                rec.priority === 'High'
                                  ? 'badge badge-danger'
                                  : rec.priority === 'Medium'
                                    ? 'badge badge-warning'
                                    : 'badge badge-info'
                              }
                            >
                              {rec.priority} Priority
                            </span>
                          </div>
                          <p style={{ margin: '4px 0', fontSize: '0.86rem', color: '#cbd5e1' }}>{rec.reason}</p>
                        </div>
                      ))
                    )}
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setActiveTab('learning-plan')}
                    >
                      Open Full Learning Plan
                    </button>
                  </section>
                </div>
              </div>
            </>
          )}
        </main>
      )}

      {/* ============================================================
          SCREEN C: STUDENT PROFILE
         ============================================================ */}
      {activeTab === 'profile' && (
        <main className="grid-2">
          <section className="panel">
            <h2>Student Profile & Preparation Preferences</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
              We collect only information required to map your target job role and calibrate weekly study
              recommendations. No sensitive demographic attributes are collected or used in scoring.
            </p>
            <form onSubmit={handleSaveProfile}>
              <div className="form-group">
                <label htmlFor="profile-display-name" className="form-label">
                  Name or Preferred Display Name *
                </label>
                <input
                  id="profile-display-name"
                  className="form-input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g., Ananya Rao"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="profile-education" className="form-label">
                  Education Level / Program *
                </label>
                <input
                  id="profile-education"
                  className="form-input"
                  value={educationLevel}
                  onChange={(e) => setEducationLevel(e.target.value)}
                  placeholder="e.g., B.E. Computer Science (Semester 7)"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="profile-target-role" className="form-label">
                  Target Job Role *
                </label>
                <select
                  id="profile-target-role"
                  className="form-select"
                  value={targetRoleId}
                  onChange={(e) => {
                    setTargetRoleId(e.target.value);
                    void handleInspectRole(e.target.value);
                  }}
                >
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="profile-current-skills" className="form-label">
                  Current Self-Reported Skills (comma-separated)
                </label>
                <input
                  id="profile-current-skills"
                  className="form-input"
                  value={currentSkillsInput}
                  onChange={(e) => setCurrentSkillsInput(e.target.value)}
                  placeholder="Python, SQL, REST APIs, Git"
                />
                <span className="form-hint">
                  Self-reported skills help contextualise your profile; readiness scores still require verified
                  assessment attempts.
                </span>
              </div>

              <div className="form-group">
                <label htmlFor="profile-languages" className="form-label">
                  Preferred Programming Languages (comma-separated)
                </label>
                <input
                  id="profile-languages"
                  className="form-input"
                  value={preferredLanguagesInput}
                  onChange={(e) => setPreferredLanguagesInput(e.target.value)}
                  placeholder="Python, TypeScript, Java, C++"
                />
              </div>

              <div className="form-group">
                <label htmlFor="profile-prep-time" className="form-label">
                  Available Preparation Time (Hours per Week) *
                </label>
                <input
                  id="profile-prep-time"
                  type="number"
                  min={1}
                  max={80}
                  className="form-input"
                  value={availablePrepTime}
                  onChange={(e) => setAvailablePrepTime(Number(e.target.value))}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="profile-goal" className="form-label">
                  Preparation Goal *
                </label>
                <textarea
                  id="profile-goal"
                  className="form-textarea"
                  value={preparationGoal}
                  onChange={(e) => setPreparationGoal(e.target.value)}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? 'Saving Profile…' : 'Save Student Profile'}
              </button>
            </form>
          </section>

          <div>
            <section className="panel">
              <h3>Selected Role Skill Profile Preview</h3>
              {selectedRoleDetail ? (
                <>
                  <p style={{ color: '#cbd5e1' }}>
                    <strong>{selectedRoleDetail.name}</strong> (v{selectedRoleDetail.version}):{' '}
                    {selectedRoleDetail.description}
                  </p>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Skill</th>
                        <th>Weight</th>
                        <th>Target</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedRoleDetail.skills.map((s) => (
                        <tr key={s.skill_id}>
                          <td>
                            <strong>{s.skill_name}</strong>
                            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{s.rationale}</div>
                          </td>
                          <td>{(s.weight * 100).toFixed(0)}%</td>
                          <td>{s.expected_level}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              ) : (
                <p style={{ color: '#94a3b8' }}>Select a role to view its required skills.</p>
              )}
            </section>

            <section className="panel">
              <h3>Privacy & Data Deletion Control</h3>
              <p style={{ color: '#94a3b8', fontSize: '0.88rem' }}>
                You may permanently delete your student profile, all submitted assessment attempts, and learning
                recommendations at any time.
              </p>
              <button type="button" className="btn btn-danger" onClick={handleDeleteProfile}>
                Delete My Profile & Assessment Data
              </button>
            </section>
          </div>
        </main>
      )}

      {/* ============================================================
          SCREEN D: TARGET ROLE SELECTION
         ============================================================ */}
      {activeTab === 'roles' && (
        <main className="grid-2">
          <section className="panel">
            <h2>Configurable Target Job Roles</h2>
            <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
              Select any role below to inspect its weighted skill requirements, expected proficiency targets, and
              rationale. Remember that different employers may emphasise different skill combinations.
            </p>
            <div style={{ display: 'grid', gap: 12 }}>
              {roles.map((r) => (
                <div
                  key={r.id}
                  className="skill-row"
                  style={{
                    borderColor: selectedRoleDetail?.id === r.id ? '#38bdf8' : '#1e293b',
                  }}
                >
                  <div className="skill-row-header">
                    <strong>{r.name}</strong>
                    <span className="badge badge-info">{r.skill_count} Core Skills</span>
                  </div>
                  <p style={{ fontSize: '0.88rem', color: '#cbd5e1', margin: '4px 0 10px' }}>{r.description}</p>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => void handleInspectRole(r.id)}
                    >
                      Inspect Skill Weights
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => {
                        setTargetRoleId(r.id);
                        void handleInspectRole(r.id);
                        setActiveTab('profile');
                      }}
                    >
                      Use as Target Role
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="panel">
            {selectedRoleDetail ? (
              <>
                <span className="badge badge-info">Role Configuration v{selectedRoleDetail.version}</span>
                <h2 style={{ marginTop: 8 }}>{selectedRoleDetail.name}</h2>
                <p style={{ color: '#cbd5e1' }}>{selectedRoleDetail.description}</p>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                  Total Validated Skill Weight: {(selectedRoleDetail.total_weight * 100).toFixed(0)}%
                </p>
                {selectedRoleDetail.skills.map((s) => (
                  <div key={s.skill_id} className="skill-row">
                    <div className="skill-row-header">
                      <strong>{s.skill_name}</strong>
                      <span className="badge badge-neutral">
                        Weight: {(s.weight * 100).toFixed(0)}% | Target: {s.expected_level}%
                      </span>
                    </div>
                    <p style={{ margin: '4px 0', fontSize: '0.85rem', color: '#cbd5e1' }}>
                      {s.skill_description}
                    </p>
                    <p style={{ margin: 0, fontSize: '0.82rem', color: '#7dd3fc' }}>
                      <strong>Role Relevance:</strong> {s.rationale}
                    </p>
                  </div>
                ))}
                <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: 12 }}>
                  {selectedRoleDetail.disclaimer}
                </p>
              </>
            ) : (
              <p>Select a role to view its detailed skill matrix.</p>
            )}
          </section>
        </main>
      )}

      {/* ============================================================
          SCREEN E: ASSESSMENT CENTRE
         ============================================================ */}
      {activeTab === 'assessments' && (
        <main>
          {!activeAssessment ? (
            <section className="panel">
              <h2>Assessment Centre</h2>
              <p style={{ color: '#cbd5e1', maxWidth: 800 }}>
                Complete structured assessments to build verifiable skill evidence. Objective scoring is performed
                exclusively on the backend; correct answers and explanations are unlocked only after submission.
              </p>
              <div className="grid-2" style={{ marginTop: 20 }}>
                {assessments.map((a) => (
                  <div key={a.id} className="metric-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                        <span className="badge badge-info">{a.skill_area}</span>
                        <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                          v{a.version} • {a.time_limit_minutes} mins
                        </span>
                      </div>
                      <h3 style={{ margin: '6px 0' }}>{a.title}</h3>
                      <p style={{ color: '#cbd5e1', fontSize: '0.9rem' }}>{a.description}</p>
                      <p style={{ fontSize: '0.83rem', color: '#94a3b8' }}>
                        <strong>Covered Skills:</strong> {a.covered_skills.join(', ')}
                      </p>
                      <p style={{ fontSize: '0.83rem', color: '#94a3b8' }}>
                        <strong>Format:</strong> {a.question_count} Questions • {a.total_points} Total Points
                      </p>
                    </div>
                    <div style={{ marginTop: 14 }}>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => void handleStartAssessment(a.id)}
                        disabled={loading}
                      >
                        Start Assessment Attempt
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : (
            <section className="panel" aria-label="Live Assessment Runner">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
                <div>
                  <span className="badge badge-info">
                    Attempt ID: {activeAttemptId} • Version {activeAssessment.version}
                  </span>
                  <h2 style={{ margin: '6px 0 0' }}>{activeAssessment.title}</h2>
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    setActiveAssessment(null);
                    setActiveAttemptId(null);
                  }}
                >
                  Exit Without Submitting
                </button>
              </div>

              <div className="disclaimer-banner" style={{ marginBottom: 16 }}>
                <strong>Instructions:</strong> {activeAssessment.instructions}
              </div>

              {/* Question Navigation Pills */}
              <div className="question-nav-pills" role="tablist" aria-label="Question navigation">
                {activeAssessment.questions.map((q, idx) => {
                  const ans = answersMap[q.id];
                  const isAnswered =
                    ans !== undefined && ans !== '' && (!Array.isArray(ans) || ans.length > 0);
                  return (
                    <button
                      key={q.id}
                      type="button"
                      className={`q-pill ${idx === currentQuestionIdx ? 'current' : ''} ${
                        isAnswered ? 'answered' : ''
                      }`}
                      onClick={() => setCurrentQuestionIdx(idx)}
                      aria-label={`Question ${idx + 1}`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>

              {/* Current Question Display */}
              {(() => {
                const q = activeAssessment.questions[currentQuestionIdx];
                if (!q) return null;
                const currentAns = answersMap[q.id];

                return (
                  <div className="metric-card" style={{ marginBottom: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                      <span className="badge badge-neutral">
                        Question {currentQuestionIdx + 1} of {activeAssessment.questions.length} • {q.skill_name}
                      </span>
                      <span className="badge badge-info">
                        {q.difficulty} • {q.score_value} pts •{' '}
                        {q.question_type === 'mcq'
                          ? 'Single Choice'
                          : q.question_type === 'multi_select'
                            ? 'Multiple Select (Partial Credit Supported)'
                            : 'Short Text Answer'}
                      </span>
                    </div>

                    <h3 style={{ fontSize: '1.12rem', marginBottom: 16 }}>{q.question_text}</h3>

                    {q.question_type === 'mcq' && (
                      <div role="radiogroup" aria-label={q.question_text}>
                        {q.options.map((opt) => {
                          const selected = currentAns === opt.option_identifier;
                          return (
                            <label
                              key={opt.option_identifier}
                              className={`option-item ${selected ? 'selected' : ''}`}
                            >
                              <input
                                type="radio"
                                name={`q-${q.id}`}
                                checked={selected}
                                onChange={() => handleSelectMcq(q.id, opt.option_identifier)}
                              />
                              <span>
                                <strong>{opt.option_identifier}.</strong> {opt.option_text}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}

                    {q.question_type === 'multi_select' && (
                      <div role="group" aria-label={q.question_text}>
                        {q.options.map((opt) => {
                          const selectedList = Array.isArray(currentAns) ? currentAns : [];
                          const checked = selectedList.includes(opt.option_identifier);
                          return (
                            <label
                              key={opt.option_identifier}
                              className={`option-item ${checked ? 'selected' : ''}`}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => handleToggleMultiSelect(q.id, opt.option_identifier)}
                              />
                              <span>
                                <strong>{opt.option_identifier}.</strong> {opt.option_text}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}

                    {q.question_type === 'short_text' && (
                      <div className="form-group">
                        <label htmlFor={`short-text-${q.id}`} className="form-label">
                          Your Answer:
                        </label>
                        <input
                          id={`short-text-${q.id}`}
                          className="form-input"
                          value={typeof currentAns === 'string' ? currentAns : ''}
                          onChange={(e) => handleShortTextChange(q.id, e.target.value)}
                          placeholder="Type your concise technical answer here..."
                        />
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Navigation & Submission Confirmation */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={currentQuestionIdx === 0}
                    onClick={() => setCurrentQuestionIdx((i) => Math.max(0, i - 1))}
                  >
                    Previous Question
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={currentQuestionIdx >= activeAssessment.questions.length - 1}
                    onClick={() =>
                      setCurrentQuestionIdx((i) => Math.min(activeAssessment.questions.length - 1, i + 1))
                    }
                  >
                    Next Question
                  </button>
                </div>

                {!confirmSubmit ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => setConfirmSubmit(true)}
                  >
                    Review & Submit Assessment
                  </button>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: '0.9rem', color: '#fcd34d' }}>
                      Confirm final submission for grading?
                    </span>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => void handleSubmitAssessment()}
                      disabled={loading}
                    >
                      {loading ? 'Grading on Backend…' : 'Confirm Submit'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setConfirmSubmit(false)}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            </section>
          )}
        </main>
      )}

      {/* ============================================================
          SCREEN F: RESULTS AND SKILL-GAP REPORT
         ============================================================ */}
      {activeTab === 'results' && (
        <main>
          {!latestResult ? (
            <section className="panel">
              <h2>Assessment Results & Skill-Gap Report</h2>
              <p style={{ color: '#cbd5e1' }}>
                Select a completed attempt from your Dashboard or complete an assessment in the Assessment Centre
                to inspect detailed question-by-question feedback and skill-area scores.
              </p>
              {dashboard && dashboard.recent_attempts.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h3>Available Completed Attempts</h3>
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                    {dashboard.recent_attempts.map((att) => (
                      <button
                        key={att.attempt_id}
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => void handleViewAttemptResult(att.attempt_id)}
                      >
                        {att.assessment_title} ({att.overall_score?.toFixed(1)}%)
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </section>
          ) : (
            <>
              <section className="panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                  <div>
                    <span className="badge badge-info">
                      Assessment v{latestResult.assessment_version} • Scoring Engine v{latestResult.scoring_version}
                    </span>
                    <h2 style={{ margin: '8px 0 4px' }}>{latestResult.assessment_title} — Diagnostic Report</h2>
                    <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.88rem' }}>
                      Submitted: {new Date(latestResult.submitted_at).toLocaleString()} • Answered{' '}
                      {latestResult.answered_questions} of {latestResult.total_questions} questions
                    </p>
                  </div>
                  <span className={getCategoryBadgeClass(latestResult.readiness_category)}>
                    {latestResult.readiness_category}
                  </span>
                </div>

                <div className="grid-3" style={{ marginTop: 20 }}>
                  <div className="metric-card">
                    <span className="metric-label">Assessment Score</span>
                    <p className="metric-value">
                      {latestResult.overall_score !== null ? `${latestResult.overall_score.toFixed(1)}%` : 'N/A'}
                    </p>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Points Earned</span>
                    <p className="metric-value">
                      {latestResult.earned_points.toFixed(1)} / {latestResult.maximum_points.toFixed(1)}
                    </p>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Calculation Method</span>
                    <p style={{ margin: 0, fontSize: '0.86rem', color: '#cbd5e1' }}>
                      {latestResult.scoring_formula_explanation}
                    </p>
                  </div>
                </div>

                <div className="grid-2" style={{ marginTop: 20 }}>
                  <div className="metric-card">
                    <h3 style={{ marginTop: 0, color: '#6ee7b7' }}>Evidence-Backed Strengths</h3>
                    {latestResult.strengths.length === 0 ? (
                      <p style={{ color: '#94a3b8', margin: 0 }}>
                        No skill in this attempt reached the 70% proficiency benchmark yet.
                      </p>
                    ) : (
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {latestResult.strengths.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div className="metric-card">
                    <h3 style={{ marginTop: 0, color: '#fcd34d' }}>Priority Improvement Areas</h3>
                    {latestResult.improvement_areas.length === 0 ? (
                      <p style={{ color: '#94a3b8', margin: 0 }}>
                        All assessed skills in this attempt met or exceeded the 70% benchmark.
                      </p>
                    ) : (
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {latestResult.improvement_areas.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </section>

              <section className="panel">
                <h3>Question-by-Question Grading & Explanations</h3>
                {latestResult.question_results.map((qr, idx) => (
                  <div key={qr.question_id} className="skill-row">
                    <div className="skill-row-header">
                      <strong>
                        Q{idx + 1}. [{qr.topic}] {qr.question_text}
                      </strong>
                      <span className={qr.is_correct ? 'badge badge-success' : qr.awarded_score > 0 ? 'badge badge-warning' : 'badge badge-danger'}>
                        {qr.awarded_score} / {qr.maximum_score} pts
                      </span>
                    </div>
                    <p style={{ margin: '4px 0', fontSize: '0.86rem', color: '#cbd5e1' }}>
                      <strong>Your Answer:</strong>{' '}
                      {Array.isArray(qr.submitted_answer)
                        ? qr.submitted_answer.join(', ') || 'Unanswered'
                        : qr.submitted_answer || 'Unanswered'}{' '}
                      — <em>{qr.feedback}</em>
                    </p>
                    <p style={{ margin: '4px 0 0', fontSize: '0.85rem', color: '#7dd3fc' }}>
                      <strong>Explanation:</strong> {qr.explanation}
                    </p>
                  </div>
                ))}
                <p style={{ fontSize: '0.84rem', color: '#94a3b8', marginTop: 12 }}>
                  <strong>Limitations:</strong> {latestResult.limitations_note}
                </p>
              </section>
            </>
          )}
        </main>
      )}

      {/* ============================================================
          SCREEN G: PERSONALISED LEARNING PLAN
         ============================================================ */}
      {activeTab === 'learning-plan' && (
        <main>
          <section className="panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
              <div>
                <h2 style={{ margin: 0 }}>Personalised Learning Plan</h2>
                <p style={{ margin: '4px 0 0', color: '#94a3b8', fontSize: '0.9rem' }}>
                  Rule-based recommendations prioritised by your assessed skill gaps, target role weights, and
                  weekly preparation hours.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={async () => {
                  const refreshed = await fetchRecommendations(true);
                  setRecommendations(refreshed);
                  setStatusMessage('Refreshed recommendations against latest skill evidence.');
                }}
              >
                Recalculate Plan
              </button>
            </div>

            {recommendations.length === 0 ? (
              <p style={{ color: '#94a3b8' }}>
                Create your student profile first to generate role-aligned learning recommendations.
              </p>
            ) : (
              recommendations.map((rec) => (
                <div key={rec.id} className="skill-row">
                  <div className="skill-row-header">
                    <div>
                      <span
                        className={
                          rec.priority === 'High'
                            ? 'badge badge-danger'
                            : rec.priority === 'Medium'
                              ? 'badge badge-warning'
                              : 'badge badge-info'
                        }
                        style={{ marginRight: 8 }}
                      >
                        {rec.priority} Priority
                      </span>
                      <strong>{rec.activity_title}</strong>{' '}
                      <span style={{ fontSize: '0.84rem', color: '#94a3b8' }}>
                        ({rec.skill_name} • Effort: {rec.estimated_effort})
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <label htmlFor={`rec-status-${rec.id}`} style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                        Status:
                      </label>
                      <select
                        id={`rec-status-${rec.id}`}
                        className="form-select"
                        style={{ width: 'auto', padding: '6px 10px', fontSize: '0.84rem' }}
                        value={rec.status}
                        onChange={(e) =>
                          void handleRecommendationStatusChange(
                            rec.id,
                            e.target.value as 'pending' | 'in_progress' | 'completed' | 'dismissed',
                          )
                        }
                      >
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                        <option value="dismissed">Dismissed</option>
                      </select>
                    </div>
                  </div>
                  <p style={{ margin: '6px 0', fontSize: '0.9rem', color: '#e2e8f0' }}>
                    {rec.activity_description}
                  </p>
                  <p style={{ margin: '4px 0', fontSize: '0.85rem', color: '#7dd3fc' }}>
                    <strong>Why Recommended:</strong> {rec.reason}
                  </p>
                  <p style={{ margin: '4px 0', fontSize: '0.82rem', color: '#94a3b8' }}>
                    <strong>Supporting Evidence:</strong> {rec.evidence_summary}
                  </p>
                  {rec.is_ai_enhanced && rec.ai_note && (
                    <p style={{ margin: '4px 0', fontSize: '0.82rem', color: '#c084fc' }}>{rec.ai_note}</p>
                  )}
                  {rec.resource_url && (
                    <a
                      href={rec.resource_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: '#38bdf8', fontSize: '0.84rem', fontWeight: 600 }}
                    >
                      Open Reference Documentation ↗
                    </a>
                  )}
                </div>
              ))
            )}
          </section>
        </main>
      )}

      {/* ============================================================
          SCREEN H: PROGRESS TRACKER
         ============================================================ */}
      {activeTab === 'progress' && progress && (
        <main>
          <div className="disclaimer-banner">
            <strong>Mastery Verification Policy:</strong> {progress.mastery_note}
          </div>

          <div className="grid-4" style={{ marginBottom: 24 }}>
            <div className="metric-card">
              <span className="metric-label">Submitted Assessments</span>
              <p className="metric-value">{progress.total_attempts_submitted}</p>
            </div>
            <div className="metric-card">
              <span className="metric-label">Completed Activities</span>
              <p className="metric-value">{progress.completed_recommendations_count}</p>
            </div>
            <div className="metric-card">
              <span className="metric-label">Active Recommendations</span>
              <p className="metric-value">{progress.pending_recommendations_count}</p>
            </div>
            <div className="metric-card">
              <span className="metric-label">Logged Practice Sessions</span>
              <p className="metric-value">{progress.practice_sessions_logged}</p>
            </div>
          </div>

          <div className="grid-2">
            {/* Skill Evolution & Retake Comparisons */}
            <div>
              <section className="panel">
                <h3>Skill Assessment Score Progression</h3>
                {progress.skill_progress_summary.length === 0 ? (
                  <p style={{ color: '#94a3b8' }}>No skill scores recorded yet.</p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Skill</th>
                        <th>Attempts</th>
                        <th>Initial</th>
                        <th>Latest</th>
                        <th>Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {progress.skill_progress_summary.map((sp) => (
                        <tr key={sp.skill_id}>
                          <td>
                            <strong>{sp.skill_name}</strong>
                          </td>
                          <td>{sp.attempts_count}</td>
                          <td>{sp.initial_score.toFixed(1)}%</td>
                          <td>{sp.latest_score.toFixed(1)}%</td>
                          <td>
                            <span
                              className={
                                sp.score_change > 0
                                  ? 'badge badge-success'
                                  : sp.score_change < 0
                                    ? 'badge badge-danger'
                                    : 'badge badge-neutral'
                              }
                            >
                              {sp.score_change > 0 ? `+${sp.score_change.toFixed(1)}%` : `${sp.score_change.toFixed(1)}%`}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>

              <section className="panel">
                <h3>Retake Comparisons (Version-Checked)</h3>
                {progress.attempt_comparisons.length === 0 ? (
                  <p style={{ color: '#94a3b8' }}>
                    Retake any assessment at least twice to see a version-validated comparison of your score
                    changes.
                  </p>
                ) : (
                  progress.attempt_comparisons.map((comp) => (
                    <div key={`${comp.earlier_attempt_id}-${comp.later_attempt_id}`} className="skill-row">
                      <div className="skill-row-header">
                        <strong>{comp.assessment_title}</strong>
                        <span className={comp.comparable ? 'badge badge-info' : 'badge badge-warning'}>
                          {comp.comparable ? `Delta: ${comp.score_delta! >= 0 ? '+' : ''}${comp.score_delta}%` : 'Version Mismatch'}
                        </span>
                      </div>
                      <p style={{ margin: '4px 0', fontSize: '0.86rem', color: '#cbd5e1' }}>
                        Earlier (v{comp.earlier_version}): {comp.earlier_score?.toFixed(1)}% → Latest (v
                        {comp.later_version}): {comp.later_score?.toFixed(1)}%
                      </p>
                      <p style={{ margin: 0, fontSize: '0.82rem', color: '#94a3b8' }}>{comp.comparison_note}</p>
                    </div>
                  ))
                )}
              </section>
            </div>

            {/* Practice Session Logger & Event Log */}
            <div>
              <section className="panel">
                <h3>Log a Self-Study / Practice Session</h3>
                <form onSubmit={handleLogPractice}>
                  <div className="form-group">
                    <label htmlFor="practice-skill" className="form-label">
                      Skill Practiced
                    </label>
                    <select
                      id="practice-skill"
                      className="form-select"
                      value={practiceSkillId}
                      onChange={(e) => setPracticeSkillId(e.target.value)}
                    >
                      {skills.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.category})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label htmlFor="practice-duration" className="form-label">
                      Duration (Minutes)
                    </label>
                    <input
                      id="practice-duration"
                      type="number"
                      min={5}
                      max={480}
                      className="form-input"
                      value={practiceDuration}
                      onChange={(e) => setPracticeDuration(Number(e.target.value))}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="practice-notes" className="form-label">
                      Session Summary / Topics Covered
                    </label>
                    <input
                      id="practice-notes"
                      className="form-input"
                      value={practiceNotes}
                      onChange={(e) => setPracticeNotes(e.target.value)}
                      placeholder="e.g., Solved 8 SQL GROUP BY and HAVING exercises"
                      required
                    />
                  </div>
                  <button type="submit" className="btn btn-primary">
                    Record Practice Session
                  </button>
                </form>
              </section>

              <section className="panel">
                <h3>Stored Activity & Assessment Event Log</h3>
                {progress.progress_events.length === 0 ? (
                  <p style={{ color: '#94a3b8' }}>No events recorded yet.</p>
                ) : (
                  <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                    {progress.progress_events.slice(0, 15).map((ev) => (
                      <div key={ev.id} className="skill-row" style={{ padding: '10px 12px' }}>
                        <div className="skill-row-header" style={{ marginBottom: 2 }}>
                          <strong style={{ fontSize: '0.86rem' }}>{ev.event_type.replace(/_/g, ' ').toUpperCase()}</strong>
                          <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                            {new Date(ev.event_timestamp).toLocaleString()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                          Ref: {ev.reference_id || 'N/A'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
