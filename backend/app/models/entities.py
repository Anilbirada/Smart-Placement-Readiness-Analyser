from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    display_name = Column(String(120), nullable=False)
    login_identifier = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    profile = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    attempts = relationship("AssessmentAttempt", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("StudentRecommendation", back_populates="user", cascade="all, delete-orphan")
    progress_events = relationship("ProgressEvent", back_populates="user", cascade="all, delete-orphan")


class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    version = Column(String(32), default="1.0.0", nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    skill_requirements = relationship("RoleSkillRequirement", back_populates="role", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    category = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    role_requirements = relationship("RoleSkillRequirement", back_populates="skill")
    learning_activities = relationship("LearningActivity", back_populates="skill")


class RoleSkillRequirement(Base):
    __tablename__ = "role_skill_requirements"
    __table_args__ = (UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(64), ForeignKey("job_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    weight = Column(Float, nullable=False)
    expected_level = Column(Float, nullable=False, default=70.0)
    rationale = Column(Text, nullable=False)
    version = Column(String(32), default="1.0.0", nullable=False)

    role = relationship("JobRole", back_populates="skill_requirements")
    skill = relationship("Skill", back_populates="role_requirements")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    education_level = Column(String(120), nullable=False)
    target_role_id = Column(String(64), ForeignKey("job_roles.id"), nullable=False, index=True)
    current_skills_json = Column(Text, default="[]", nullable=False)
    preferred_languages_json = Column(Text, default="[]", nullable=False)
    preparation_goal = Column(Text, nullable=False)
    available_preparation_time = Column(Integer, nullable=False, default=10)  # hours per week
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="profile")
    target_role = relationship("JobRole")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    assessment_type = Column(String(64), nullable=False, index=True)
    skill_area = Column(String(64), nullable=False)
    time_limit_minutes = Column(Integer, default=15, nullable=False)
    version = Column(String(32), default="1.0.0", nullable=False)
    status = Column(String(32), default="active", nullable=False, index=True)

    questions = relationship("Question", back_populates="assessment", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String(64), primary_key=True, index=True)
    assessment_id = Column(String(64), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(64), ForeignKey("skills.id"), nullable=False, index=True)
    topic = Column(String(120), nullable=False)
    skill_area = Column(String(64), nullable=False)
    question_type = Column(String(32), nullable=False)  # mcq | multi_select | short_text
    question_text = Column(Text, nullable=False)
    difficulty = Column(String(32), nullable=False)  # Easy | Medium | Hard
    correct_answer_json = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    score_value = Column(Float, nullable=False, default=10.0)
    version = Column(String(32), default="1.0.0", nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    assessment = relationship("Assessment", back_populates="questions")
    skill = relationship("Skill")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String(64), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_identifier = Column(String(16), nullable=False)
    option_text = Column(Text, nullable=False)

    question = relationship("Question", back_populates="options")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(String(64), ForeignKey("assessments.id"), nullable=False, index=True)
    assessment_version = Column(String(32), nullable=False)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="in_progress", nullable=False, index=True)

    user = relationship("User", back_populates="attempts")
    assessment = relationship("Assessment")
    answers = relationship("AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")
    result = relationship("AssessmentResult", back_populates="attempt", uselist=False, cascade="all, delete-orphan")


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempt_id = Column(String(64), ForeignKey("assessment_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(64), ForeignKey("questions.id"), nullable=False, index=True)
    answer_value_json = Column(Text, nullable=False)
    awarded_score = Column(Float, nullable=False)
    maximum_score = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    feedback = Column(Text, nullable=True)

    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("Question")


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id = Column(String(64), primary_key=True, index=True)
    attempt_id = Column(String(64), ForeignKey("assessment_attempts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    overall_score = Column(Float, nullable=True)
    earned_points = Column(Float, nullable=False, default=0.0)
    maximum_points = Column(Float, nullable=False, default=0.0)
    assessment_status = Column(String(64), nullable=False)
    readiness_category = Column(String(64), nullable=False)
    result_summary = Column(Text, nullable=False)
    limitations_note = Column(Text, nullable=False)
    scoring_version = Column(String(32), nullable=False, default="1.0.0")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    attempt = relationship("AssessmentAttempt", back_populates="result")
    skill_results = relationship("SkillAssessmentResult", back_populates="assessment_result", cascade="all, delete-orphan")


class SkillAssessmentResult(Base):
    __tablename__ = "skill_assessment_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_result_id = Column(String(64), ForeignKey("assessment_results.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(64), ForeignKey("skills.id"), nullable=False, index=True)
    score = Column(Float, nullable=True)
    earned_points = Column(Float, nullable=False, default=0.0)
    maximum_points = Column(Float, nullable=False, default=0.0)
    evidence_summary = Column(Text, nullable=False)
    assessment_status = Column(String(64), nullable=False)

    assessment_result = relationship("AssessmentResult", back_populates="skill_results")
    skill = relationship("Skill")


class LearningActivity(Base):
    __tablename__ = "learning_activities"

    id = Column(String(64), primary_key=True, index=True)
    skill_id = Column(String(64), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    activity_type = Column(String(64), nullable=False, default="practice")
    resource_url = Column(String(512), nullable=True)
    estimated_effort = Column(String(64), nullable=False)
    effort_hours = Column(Float, nullable=False, default=3.0)
    status = Column(String(32), default="active", nullable=False)

    skill = relationship("Skill", back_populates="learning_activities")


class StudentRecommendation(Base):
    __tablename__ = "student_recommendations"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(String(64), ForeignKey("skills.id"), nullable=False, index=True)
    learning_activity_id = Column(String(64), ForeignKey("learning_activities.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    evidence_summary = Column(Text, nullable=False)
    priority = Column(String(32), nullable=False)  # High | Medium | Low
    status = Column(String(32), default="pending", nullable=False, index=True)  # pending | in_progress | completed | dismissed
    is_ai_enhanced = Column(Boolean, default=False, nullable=False)
    ai_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="recommendations")
    skill = relationship("Skill")
    learning_activity = relationship("LearningActivity")


class ProgressEvent(Base):
    __tablename__ = "progress_events"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    reference_id = Column(String(64), nullable=True)
    event_timestamp = Column(DateTime, default=utc_now, nullable=False)
    safe_metadata_json = Column(Text, default="{}", nullable=False)

    user = relationship("User", back_populates="progress_events")


# Legacy model preserved for backwards compatibility with existing files
class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(64), unique=True, index=True, nullable=False)
    submitted_url = Column(Text, nullable=False)
    risk_category = Column(String(64), nullable=False)
    analysis_method = Column(String(64), nullable=False)
    model_version = Column(String(64), nullable=True)
    score = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    status = Column(String(32), default="completed")
