from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Certification,
    Company,
    Experience,
    JobRole,
    Project,
    Skill,
    SkillSource,
    Student,
    StudentSkill,
    User,
)
from app.repositories import student_repository as repo
from app.schemas.profile import (
    Completeness,
    PreferencesUpdate,
    ProfileOut,
    ProfileUpdate,
    SkillsUpdate,
    StudentSkillOut,
)

MIN_SKILLS_FOR_COMPLETE = 3


def _invalid(detail: str) -> HTTPException:
    return HTTPException(422, detail)


def get_student(db: Session, user: User) -> Student:
    student = repo.get_profile_by_user_id(db, user.id)
    if student is None:  # every student user gets a profile at registration; guard anyway
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student profile not found.")
    return student


# ---------- completeness ----------
def compute_completeness(student: Student) -> Completeness:
    """Which profile items needed by eligibility/recommendations are still missing.

    Certifications and experience are optional for most students, so they are
    not counted against the score.
    """
    checks = [
        ("Phone number", bool(student.phone)),
        ("College", bool(student.college)),
        ("Branch", student.branch_id is not None),
        ("Year and semester", bool(student.year and student.semester)),
        ("CGPA", student.cgpa is not None),
        (f"At least {MIN_SKILLS_FOR_COMPLETE} skills", len(student.skills) >= MIN_SKILLS_FOR_COMPLETE),
        ("At least one project", len(student.projects) >= 1),
        ("Interests", bool(student.interests)),
        ("Preferred job roles", len(student.preferred_roles) >= 1),
    ]
    missing = [label for label, ok in checks if not ok]
    score = round(100 * (len(checks) - len(missing)) / len(checks))
    return Completeness(score=score, missing=missing)


def to_profile_out(student: Student) -> ProfileOut:
    return ProfileOut(
        id=student.id,
        email=student.user.email,
        full_name=student.full_name,
        phone=student.phone,
        college=student.college,
        branch=student.branch,
        year=student.year,
        semester=student.semester,
        cgpa=float(student.cgpa) if student.cgpa is not None else None,
        backlogs=student.backlogs,
        interests=student.interests,
        preferred_location=student.preferred_location,
        preferred_job_type=student.preferred_job_type,
        skills=[
            StudentSkillOut(
                skill_id=s.skill_id,
                name=s.skill.name,
                category=s.skill.category,
                proficiency=s.proficiency,
                source=s.source,
            )
            for s in sorted(student.skills, key=lambda s: s.skill.name.lower())
        ],
        certifications=sorted(student.certifications, key=lambda c: c.id),
        projects=sorted(student.projects, key=lambda p: p.id),
        experiences=sorted(student.experiences, key=lambda e: e.id),
        preferred_roles=student.preferred_roles,
        preferred_companies=student.preferred_companies,
        completeness=compute_completeness(student),
    )


def _reload(db: Session, student: Student) -> ProfileOut:
    db.commit()
    db.expire_all()
    return to_profile_out(repo.get_profile_by_user_id(db, student.user_id))


# ---------- updates ----------
def update_basic(db: Session, student: Student, data: ProfileUpdate) -> ProfileOut:
    if data.branch_id is not None and repo.get_branch(db, data.branch_id) is None:
        raise _invalid("Selected branch does not exist.")
    for field, value in data.model_dump().items():
        setattr(student, field, value)
    return _reload(db, student)


def replace_skills(db: Session, student: Student, data: SkillsUpdate) -> ProfileOut:
    """Replace the whole skill list. Skills previously found by resume analysis keep that source."""
    wanted = {entry.skill_id: entry for entry in data.skills}
    found = {s.id for s in repo.get_by_ids(db, Skill, list(wanted))}
    unknown = set(wanted) - found
    if unknown:
        raise _invalid(f"Unknown skill id(s): {sorted(unknown)}.")

    current = {s.skill_id: s for s in student.skills}
    for skill_id, row in current.items():
        if skill_id not in wanted:
            student.skills.remove(row)
    for skill_id, entry in wanted.items():
        if skill_id in current:
            current[skill_id].proficiency = entry.proficiency
        else:
            student.skills.append(
                StudentSkill(skill_id=skill_id, proficiency=entry.proficiency, source=SkillSource.MANUAL)
            )
    return _reload(db, student)


def update_preferences(db: Session, student: Student, data: PreferencesUpdate) -> ProfileOut:
    role_ids, company_ids = set(data.preferred_role_ids), set(data.preferred_company_ids)
    roles = repo.get_by_ids(db, JobRole, list(role_ids))
    companies = repo.get_by_ids(db, Company, list(company_ids))
    if len(roles) != len(role_ids):
        raise _invalid("One or more selected job roles do not exist.")
    if len(companies) != len(company_ids):
        raise _invalid("One or more selected companies do not exist.")
    student.preferred_roles = roles
    student.preferred_companies = companies
    return _reload(db, student)


# ---------- certifications / projects / experiences (same pattern) ----------
CHILD_MODELS = {"certifications": Certification, "projects": Project, "experiences": Experience}


def add_item(db: Session, student: Student, kind: str, data) -> ProfileOut:
    getattr(student, kind).append(CHILD_MODELS[kind](**data.model_dump()))
    return _reload(db, student)


def update_item(db: Session, student: Student, kind: str, item_id: int, data) -> ProfileOut:
    item = _owned_or_404(db, student, kind, item_id)
    for field, value in data.model_dump().items():
        setattr(item, field, value)
    return _reload(db, student)


def delete_item(db: Session, student: Student, kind: str, item_id: int) -> ProfileOut:
    item = _owned_or_404(db, student, kind, item_id)
    getattr(student, kind).remove(item)
    return _reload(db, student)


def _owned_or_404(db: Session, student: Student, kind: str, item_id: int):
    # 404 (not 403) for other students' items, so ids of other people's data are not revealed.
    item = repo.get_owned(db, CHILD_MODELS[kind], item_id, student.id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found.")
    return item
