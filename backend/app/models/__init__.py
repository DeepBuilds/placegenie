"""Import every model so Base.metadata knows all tables."""
from app.models.application import (
    Application,
    ApplicationStatus,
    InterviewStage,
    InterviewStageType,
    StageOutcome,
)
from app.models.chat import ChatMessage, ChatRole
from app.models.company import (
    Company,
    Job,
    JobAllowedBranch,
    JobRequiredCertification,
    JobSkill,
    JobStatus,
    JobType,
    SkillImportance,
)
from app.models.reference import Branch, JobRole, Skill
from app.models.resume import Resume, ResumeAnalysis, ResumeDetectedSkill
from app.models.student import (
    Certification,
    Experience,
    Project,
    Proficiency,
    SkillSource,
    Student,
    StudentSkill,
)
from app.models.user import Coordinator, Role, User

__all__ = [
    "Application", "ApplicationStatus", "Branch", "Certification", "ChatMessage", "ChatRole",
    "Company", "Coordinator", "Experience", "InterviewStage", "InterviewStageType", "Job",
    "JobAllowedBranch", "JobRequiredCertification", "JobRole", "JobSkill", "JobStatus", "JobType",
    "Proficiency", "Project", "Resume", "ResumeAnalysis", "ResumeDetectedSkill", "Role", "Skill",
    "SkillImportance", "SkillSource", "StageOutcome", "Student", "StudentSkill", "User",
]
