"""Reference (lookup) data: branches, skills and job roles.

Idempotent: only names that are missing are inserted, so it is safe to run on
every startup. Demo companies/jobs/students are added in later phases.

Run manually (from backend/):  python -m app.database.seed
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branch, JobRole, Skill

BRANCHES = [
    "Computer Science and Engineering",
    "Information Technology",
    "Artificial Intelligence and Data Science",
    "Electronics and Telecommunication Engineering",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Chemical Engineering",
]

# (name, category)
SKILLS = [
    # Programming languages
    ("Python", "Programming"), ("Java", "Programming"), ("C", "Programming"),
    ("C++", "Programming"), ("JavaScript", "Programming"), ("TypeScript", "Programming"),
    ("Go", "Programming"), ("Kotlin", "Programming"), ("R", "Programming"),
    # Web
    ("HTML", "Web"), ("CSS", "Web"), ("React", "Web"), ("Angular", "Web"),
    ("Node.js", "Web"), ("Express.js", "Web"), ("Django", "Web"), ("Flask", "Web"),
    ("FastAPI", "Web"), ("Spring Boot", "Web"), ("REST APIs", "Web"),
    # Databases
    ("SQL", "Database"), ("MySQL", "Database"), ("PostgreSQL", "Database"),
    ("MongoDB", "Database"), ("Redis", "Database"),
    # Data / AI
    ("Pandas", "Data"), ("NumPy", "Data"), ("Excel", "Data"), ("Power BI", "Data"),
    ("Tableau", "Data"), ("Statistics", "Data"), ("Machine Learning", "Data"),
    ("Deep Learning", "Data"), ("Scikit-learn", "Data"), ("TensorFlow", "Data"),
    ("Natural Language Processing", "Data"), ("Data Visualization", "Data"),
    # Cloud / DevOps
    ("Git", "Tools"), ("Linux", "Tools"), ("Docker", "DevOps"), ("Kubernetes", "DevOps"),
    ("AWS", "Cloud"), ("Microsoft Azure", "Cloud"), ("Google Cloud", "Cloud"), ("CI/CD", "DevOps"),
    # CS fundamentals
    ("Data Structures and Algorithms", "Fundamentals"), ("Object-Oriented Programming", "Fundamentals"),
    ("Operating Systems", "Fundamentals"), ("Computer Networks", "Fundamentals"),
    ("DBMS", "Fundamentals"), ("System Design", "Fundamentals"),
    # Testing / mobile / other
    ("Software Testing", "Testing"), ("Selenium", "Testing"), ("Android Development", "Mobile"),
    ("Flutter", "Mobile"), ("Cyber Security", "Security"),
    # Core engineering
    ("AutoCAD", "Core Engineering"), ("MATLAB", "Core Engineering"), ("Embedded C", "Core Engineering"),
    ("IoT", "Core Engineering"),
    # Soft skills
    ("Communication", "Soft Skills"), ("Teamwork", "Soft Skills"), ("Problem Solving", "Soft Skills"),
]

# (name, category)
JOB_ROLES = [
    ("Software Engineer", "Software"),
    ("Frontend Developer", "Software"),
    ("Backend Developer", "Software"),
    ("Full Stack Developer", "Software"),
    ("Mobile App Developer", "Software"),
    ("QA / Test Engineer", "Software"),
    ("DevOps Engineer", "Infrastructure"),
    ("Cloud Engineer", "Infrastructure"),
    ("Data Analyst", "Data"),
    ("Data Scientist", "Data"),
    ("Machine Learning Engineer", "Data"),
    ("Business Analyst", "Business"),
    ("Cyber Security Analyst", "Security"),
    ("Embedded Systems Engineer", "Core Engineering"),
    ("Graduate Engineer Trainee", "Core Engineering"),
]


def _insert_missing(db: Session, model, rows: list[tuple]) -> int:
    existing = set(db.scalars(select(model.name)))
    new = [row for row in rows if row[0] not in existing]
    for row in new:
        if len(row) == 1:
            db.add(model(name=row[0]))
        else:
            db.add(model(name=row[0], category=row[1]))
    return len(new)


def seed_reference_data(db: Session) -> dict[str, int]:
    added = {
        "branches": _insert_missing(db, Branch, [(b,) for b in BRANCHES]),
        "skills": _insert_missing(db, Skill, SKILLS),
        "job_roles": _insert_missing(db, JobRole, JOB_ROLES),
    }
    db.commit()
    return added


if __name__ == "__main__":
    import app.models  # noqa: F401
    from app.database.base import Base
    from app.database.session import SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        print("Inserted:", seed_reference_data(session))
