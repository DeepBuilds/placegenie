from datetime import date

import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.database.base import Base
from app.models import (
    Application,
    Branch,
    Certification,
    ChatConversation,
    ChatMessage,
    ChatRole,
    Company,
    InterviewStage,
    InterviewStageType,
    Job,
    JobAllowedBranch,
    JobRequiredCertification,
    JobRole,
    JobSkill,
    Project,
    Resume,
    ResumeAnalysis,
    ResumeDetectedSkill,
    Role,
    Skill,
    SkillImportance,
    Student,
    StudentSkill,
    User,
)

EXPECTED_TABLES = {
    "users", "students", "coordinators", "branches", "skills", "job_roles", "student_skills",
    "certifications", "projects", "experiences", "student_preferred_roles",
    "student_preferred_companies", "companies", "jobs", "job_skills", "job_allowed_branches",
    "job_required_certifications", "resumes", "resume_analyses", "resume_detected_skills",
    "applications", "interview_stages", "chat_conversations", "chat_messages",
}


def make_student(db, email="s@example.com", **kw) -> Student:
    user = User(email=email, password_hash="x", role=Role.STUDENT)
    user.student = Student(full_name="Test Student", **kw)
    db.add(user)
    db.commit()
    return user.student


def make_job(db, company_name="Acme", **kw) -> Job:
    company = Company(name=company_name)
    job = Job(company=company, title="Developer", **kw)
    db.add(job)
    db.commit()
    return job


def test_all_expected_tables_exist(db_session):
    assert set(inspect(db_session.get_bind()).get_table_names()) == EXPECTED_TABLES
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_table_has_timestamps_or_is_a_link_table(db_session):
    link_tables = {
        "student_preferred_roles", "student_preferred_companies", "job_skills",
        "job_allowed_branches", "job_required_certifications", "resume_detected_skills",
        "chat_messages",
    }
    for name, table in Base.metadata.tables.items():
        if name not in link_tables:
            assert {"created_at", "updated_at"} <= set(table.columns.keys()), name


def test_student_profile_relationships_roundtrip(db_session):
    db = db_session
    branch, python, sql = Branch(name="CSE"), Skill(name="Python"), Skill(name="SQL")
    role, company = JobRole(name="Data Analyst"), Company(name="Acme")
    student = make_student(db, cgpa=8.25, backlogs=0, year=2, semester=3, branch=branch)
    student.skills = [StudentSkill(skill=python), StudentSkill(skill=sql)]
    student.certifications.append(Certification(name="AWS Cloud Practitioner"))
    student.projects.append(Project(title="Placement app", tech_stack="React, FastAPI"))
    student.preferred_roles.append(role)
    student.preferred_companies.append(company)
    db.commit()
    db.expire_all()

    s = db.scalar(select(Student))
    assert s.branch.name == "CSE"
    assert {ss.skill.name for ss in s.skills} == {"Python", "SQL"}
    assert float(s.cgpa) == 8.25
    assert s.preferred_roles[0].name == "Data Analyst"
    assert s.preferred_companies[0].name == "Acme"
    assert s.user.student is s


def test_job_with_requirements(db_session):
    db = db_session
    cse, sql = Branch(name="CSE"), Skill(name="SQL")
    job = make_job(db, min_cgpa=7.5, max_backlogs=0)
    job.skills.append(JobSkill(skill=sql, importance=SkillImportance.REQUIRED, weight=2))
    job.allowed_branches.append(JobAllowedBranch(branch=cse))
    job.required_certifications.append(JobRequiredCertification(certification_name="Oracle SQL"))
    db.commit()
    db.expire_all()

    j = db.scalar(select(Job))
    assert float(j.min_cgpa) == 7.5
    assert j.skills[0].skill.name == "SQL" and j.skills[0].weight == 2
    assert j.allowed_branches[0].branch.name == "CSE"
    assert j.required_certifications[0].certification_name == "Oracle SQL"


# ---------- constraints ----------
def test_unique_email(db_session):
    make_student(db_session, "dup@example.com")
    db_session.add(User(email="dup@example.com", password_hash="x", role=Role.COORDINATOR))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_skill_and_company_names(db_session):
    db_session.add_all([Skill(name="Python"), Skill(name="Python")])
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    db_session.add_all([Company(name="Acme"), Company(name="Acme")])
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_student_cannot_have_same_skill_twice(db_session):
    student, skill = make_student(db_session), Skill(name="Python")
    db_session.add_all([StudentSkill(student=student, skill=skill)])
    db_session.commit()
    db_session.add(StudentSkill(student_id=student.id, skill_id=skill.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cannot_apply_twice_to_same_job(db_session):
    student, job = make_student(db_session), make_job(db_session)
    db_session.add(Application(student=student, job=job))
    db_session.commit()
    db_session.add(Application(student_id=student.id, job_id=job.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("bad", [{"cgpa": 10.5}, {"cgpa": -1}, {"backlogs": -2}, {"year": 9}])
def test_student_check_constraints(db_session, bad):
    with pytest.raises(IntegrityError):
        make_student(db_session, **bad)


def test_job_check_constraints(db_session):
    with pytest.raises(IntegrityError):
        make_job(db_session, min_cgpa=11)


def test_foreign_key_enforced(db_session):
    db_session.add(Certification(student_id=999, name="Orphan"))
    with pytest.raises(IntegrityError):
        db_session.commit()


# ---------- cascades ----------
def test_deleting_user_removes_student_and_all_children(db_session):
    db = db_session
    student, job = make_student(db), make_job(db)
    skill = Skill(name="Python")
    student.skills.append(StudentSkill(skill=skill))
    student.certifications.append(Certification(name="X"))
    student.conversations.append(ChatConversation(title="hi", messages=[ChatMessage(role=ChatRole.USER, content="hi")]))
    resume = Resume(
        student=student, file_path="a.pdf", original_name="cv.pdf", mime_type="application/pdf",
        size_bytes=10, extracted_text="text",
    )
    resume.analysis = ResumeAnalysis(
        completeness_score=70, suggestions=["Add projects"],
        detected_skills=[ResumeDetectedSkill(skill=skill)],
    )
    application = Application(student=student, job=job)
    application.interview_stages.append(
        InterviewStage(stage=InterviewStageType.HR_INTERVIEW, notes="n")
    )
    db.add_all([resume, application])
    db.commit()

    db.delete(student.user)
    db.commit()

    for model in (Student, StudentSkill, Certification, ChatConversation, ChatMessage, Resume, ResumeAnalysis,
                  ResumeDetectedSkill, Application, InterviewStage):
        assert db.scalar(select(func.count()).select_from(model)) == 0, model.__name__
    # shared reference data must survive
    assert db.scalar(select(func.count()).select_from(Skill)) == 1
    assert db.scalar(select(func.count()).select_from(Job)) == 1


def test_deleting_company_removes_jobs(db_session):
    job = make_job(db_session)
    db_session.delete(job.company)
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(Job)) == 0


def test_json_columns_store_lists(db_session):
    student = make_student(db_session)
    resume = Resume(student=student, file_path="a", original_name="a.pdf", mime_type="application/pdf", size_bytes=1)
    resume.analysis = ResumeAnalysis(education=[{"degree": "B.Tech", "year": 2027}])
    db_session.add(resume)
    db_session.commit()
    db_session.expire_all()
    assert db_session.scalar(select(ResumeAnalysis)).education[0]["degree"] == "B.Tech"


def test_dates_stored(db_session):
    student = make_student(db_session)
    student.certifications.append(Certification(name="C", issued_on=date(2025, 5, 1)))
    db_session.commit()
    assert db_session.scalar(select(Certification)).issued_on == date(2025, 5, 1)
