"""Fictional demo companies and jobs (no real companies, no scraping).

Run explicitly (from backend/):  python -m app.database.seed_demo
It is idempotent: a company or job that already exists (same name / same company + title)
is left untouched, so re-running never duplicates or overwrites coordinator edits.
It is NOT run automatically at startup, so companies deleted by a coordinator stay deleted.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.seed import BRANCHES, seed_reference_data
from app.models import (
    Branch,
    Company,
    Job,
    JobAllowedBranch,
    JobRequiredCertification,
    JobRole,
    JobSkill,
    JobStatus,
    JobType,
    Skill,
    SkillImportance,
)

CSE, IT, AIDS, ENTC, EE, ME, CIVIL, CHEM = BRANCHES
SOFTWARE_BRANCHES = [CSE, IT, AIDS]

R, P = SkillImportance.REQUIRED, SkillImportance.PREFERRED
FT, INT = JobType.FULL_TIME, JobType.INTERNSHIP

COMPANIES = [
    ("Nimbus Cloudworks", "Cloud Computing", "Pune", "https://nimbus-cloudworks.example.com",
     "Fictional cloud infrastructure company building hosting and DevOps tooling for startups."),
    ("Aurora Analytics", "Data & Analytics", "Bengaluru", "https://aurora-analytics.example.com",
     "Fictional analytics firm turning business data into dashboards and predictive models."),
    ("BrightPath Infotech", "IT Services", "Mumbai", "https://brightpath-infotech.example.com",
     "Fictional IT services company with a large campus hiring programme for engineers."),
    ("Zenith Software Labs", "Product Engineering", "Hyderabad", "https://zenith-labs.example.com",
     "Fictional product company building web platforms for the logistics industry."),
    ("Kestrel Systems", "Embedded & IoT", "Pune", "https://kestrel-systems.example.com",
     "Fictional embedded-systems company making sensors and controllers for smart devices."),
    ("Orbit Mobile Apps", "Mobile Software", "Remote", "https://orbit-mobile.example.com",
     "Fictional studio building consumer Android and cross-platform mobile apps."),
    ("Helix Secure", "Cyber Security", "Noida", "https://helix-secure.example.com",
     "Fictional security firm offering monitoring and penetration-testing services."),
    ("Meridian Core Industries", "Manufacturing", "Nashik", "https://meridian-core.example.com",
     "Fictional manufacturing group hiring graduate engineer trainees for plants and design teams."),
    ("Terra Infra Constructions", "Civil & Infrastructure", "Nagpur", "https://terra-infra.example.com",
     "Fictional infrastructure company working on roads, bridges and urban projects."),
    ("QuantaRetail Tech", "E-commerce", "Bengaluru", "https://quantaretail.example.com",
     "Fictional e-commerce technology company running a marketplace and supply-chain platform."),
]

# company, title, role, location, type, min_cgpa, max_backlogs, min_exp_months,
# deadline_in_days, status, skills[(name, importance, weight)], branches, certifications, description
JOBS = [
    ("Nimbus Cloudworks", "Cloud Support Engineer", "Cloud Engineer", "Pune", FT, 7.0, 0, 0, 30, JobStatus.OPEN,
     [("Linux", R, 3), ("AWS", R, 3), ("Computer Networks", R, 2), ("Python", P, 1), ("Docker", P, 2)],
     SOFTWARE_BRANCHES + [ENTC], [],
     "Monitor and troubleshoot customer cloud workloads, write small automation scripts and support deployments."),
    ("Nimbus Cloudworks", "DevOps Engineer Intern", "DevOps Engineer", "Pune", INT, 7.5, 0, 0, 21, JobStatus.OPEN,
     [("Git", R, 2), ("Docker", R, 3), ("Linux", R, 2), ("CI/CD", P, 2), ("Kubernetes", P, 2)],
     SOFTWARE_BRANCHES, [],
     "Six-month internship helping the platform team build CI/CD pipelines and container images."),
    ("Aurora Analytics", "Data Analyst", "Data Analyst", "Bengaluru", FT, 7.0, 1, 0, 28, JobStatus.OPEN,
     [("SQL", R, 3), ("Excel", R, 2), ("Python", R, 2), ("Power BI", P, 2), ("Statistics", P, 2)],
     SOFTWARE_BRANCHES + [ENTC, EE, ME], [],
     "Build dashboards, clean datasets and present insights to business teams."),
    ("Aurora Analytics", "Machine Learning Engineer", "Machine Learning Engineer", "Bengaluru", FT, 8.0, 0, 0, 35, JobStatus.OPEN,
     [("Python", R, 3), ("Machine Learning", R, 3), ("Scikit-learn", R, 2), ("Pandas", R, 2), ("Deep Learning", P, 2), ("Statistics", P, 1)],
     [CSE, AIDS], [],
     "Develop and evaluate predictive models for demand forecasting and customer churn."),
    ("Aurora Analytics", "Business Analyst Trainee", "Business Analyst", "Bengaluru", FT, 6.5, 2, 0, 45, JobStatus.OPEN,
     [("Excel", R, 3), ("SQL", R, 2), ("Communication", R, 2), ("Tableau", P, 1)],
     [], [],
     "Gather requirements from clients and translate them into reports and process improvements. Open to all branches."),
    ("BrightPath Infotech", "Associate Software Engineer", "Software Engineer", "Mumbai", FT, 6.0, 2, 0, 25, JobStatus.OPEN,
     [("Java", R, 3), ("Object-Oriented Programming", R, 3), ("SQL", R, 2), ("Data Structures and Algorithms", P, 2)],
     SOFTWARE_BRANCHES + [ENTC, EE], [],
     "Campus hiring programme: train on enterprise Java projects and join a delivery team."),
    ("BrightPath Infotech", "Quality Assurance Engineer", "QA / Test Engineer", "Mumbai", FT, 6.0, 3, 0, 40, JobStatus.OPEN,
     [("Software Testing", R, 3), ("SQL", R, 1), ("Selenium", P, 2), ("Communication", P, 1)],
     [], [],
     "Write test cases, execute manual and automated tests, and report defects. All branches welcome."),
    ("Zenith Software Labs", "Full Stack Developer", "Full Stack Developer", "Hyderabad", FT, 7.5, 0, 0, 27, JobStatus.OPEN,
     [("JavaScript", R, 3), ("React", R, 3), ("Node.js", R, 3), ("MongoDB", R, 2), ("REST APIs", P, 2), ("TypeScript", P, 1)],
     SOFTWARE_BRANCHES, [],
     "Build features across the React frontend and Node.js services of the logistics platform."),
    ("Zenith Software Labs", "Backend Developer (Python)", "Backend Developer", "Hyderabad", FT, 8.0, 0, 6, 33, JobStatus.OPEN,
     [("Python", R, 3), ("FastAPI", R, 2), ("PostgreSQL", R, 2), ("Docker", P, 2), ("System Design", P, 2), ("REST APIs", R, 2)],
     [CSE, IT], [],
     "Design and maintain REST APIs for tracking shipments. Prior internship or project experience of 6 months expected."),
    ("Kestrel Systems", "Embedded Software Engineer", "Embedded Systems Engineer", "Pune", FT, 7.0, 0, 0, 32, JobStatus.OPEN,
     [("Embedded C", R, 3), ("C", R, 3), ("IoT", P, 2), ("MATLAB", P, 1)],
     [ENTC, EE, CSE], [],
     "Write firmware for sensor boards and test it on hardware."),
    ("Orbit Mobile Apps", "Android Developer", "Mobile App Developer", "Remote", FT, 6.5, 1, 0, 24, JobStatus.OPEN,
     [("Kotlin", R, 3), ("Android Development", R, 3), ("REST APIs", R, 2), ("Git", P, 1)],
     SOFTWARE_BRANCHES + [ENTC], [],
     "Build and ship features in our consumer Android app."),
    ("Orbit Mobile Apps", "Flutter Developer Intern", "Mobile App Developer", "Remote", INT, 6.0, 2, 0, 18, JobStatus.OPEN,
     [("Flutter", R, 3), ("Git", R, 1), ("Problem Solving", P, 1)],
     [], [],
     "Three-month remote internship building screens for a cross-platform app."),
    ("Helix Secure", "Security Analyst", "Cyber Security Analyst", "Noida", FT, 7.5, 0, 0, 38, JobStatus.OPEN,
     [("Cyber Security", R, 3), ("Computer Networks", R, 3), ("Linux", R, 2), ("Python", P, 1)],
     [CSE, IT, ENTC], ["CompTIA Security+"],
     "Monitor security events, triage alerts and support penetration tests. Security+ certification required."),
    ("Meridian Core Industries", "Graduate Engineer Trainee (Mechanical)", "Graduate Engineer Trainee", "Nashik", FT, 6.0, 1, 0, 50, JobStatus.OPEN,
     [("AutoCAD", R, 3), ("MATLAB", P, 1), ("Teamwork", P, 1)],
     [ME], [],
     "Two-year trainee programme rotating through design, production and quality teams."),
    ("Meridian Core Industries", "Graduate Engineer Trainee (Electrical)", "Graduate Engineer Trainee", "Nashik", FT, 6.5, 0, 0, 50, JobStatus.OPEN,
     [("MATLAB", R, 2), ("IoT", P, 1), ("Teamwork", P, 1)],
     [EE, ENTC], [],
     "Trainee role supporting power systems and plant automation projects."),
    ("Terra Infra Constructions", "Site Engineer Trainee", "Graduate Engineer Trainee", "Nagpur", FT, 6.0, 2, 0, 42, JobStatus.OPEN,
     [("AutoCAD", R, 3), ("Communication", R, 2), ("Teamwork", P, 1)],
     [CIVIL], [],
     "Assist project engineers on site with measurements, drawings and progress reports."),
    ("QuantaRetail Tech", "Software Development Engineer", "Software Engineer", "Bengaluru", FT, 8.5, 0, 0, 29, JobStatus.OPEN,
     [("Data Structures and Algorithms", R, 3), ("Java", R, 2), ("System Design", R, 2), ("SQL", R, 2), ("AWS", P, 2), ("Spring Boot", P, 2)],
     [CSE, IT, AIDS], [],
     "High-bar engineering role on the marketplace backend; strong problem-solving expected."),
    ("QuantaRetail Tech", "Data Scientist", "Data Scientist", "Bengaluru", FT, 8.0, 0, 0, 36, JobStatus.OPEN,
     [("Python", R, 3), ("Statistics", R, 3), ("Machine Learning", R, 3), ("SQL", R, 2), ("Natural Language Processing", P, 2), ("Pandas", P, 1)],
     [CSE, AIDS, IT], [],
     "Use customer and catalogue data to build ranking and search-relevance models."),
    ("Zenith Software Labs", "Frontend Developer (Closed Drive)", "Frontend Developer", "Hyderabad", FT, 7.0, 0, 0, 5, JobStatus.CLOSED,
     [("HTML", R, 2), ("CSS", R, 2), ("JavaScript", R, 3), ("React", P, 2)],
     SOFTWARE_BRANCHES, [],
     "Example of a closed drive: hidden from students, visible to coordinators."),
]


def _by_name(db: Session, model) -> dict[str, int]:
    return {name: id_ for id_, name in db.execute(select(model.id, model.name))}


def seed_demo_data(db: Session) -> dict[str, int]:
    seed_reference_data(db)  # make sure skills / branches / roles exist first
    skills, roles, branches = _by_name(db, Skill), _by_name(db, JobRole), _by_name(db, Branch)
    companies = {c.name: c for c in db.scalars(select(Company))}

    new_companies = new_jobs = 0
    for name, industry, location, website, description in COMPANIES:
        if name not in companies:
            companies[name] = Company(
                name=name, industry=industry, location=location, website=website, description=description
            )
            db.add(companies[name])
            new_companies += 1
    db.flush()

    existing = {(j.company_id, j.title) for j in db.scalars(select(Job))}
    for (company, title, role, location, jtype, cgpa, backlogs, exp, days, status,
         job_skills, job_branches, certs, description) in JOBS:
        c = companies[company]
        if (c.id, title) in existing:
            continue
        job = Job(
            company_id=c.id, role_id=roles[role], title=title, description=description,
            location=location, job_type=jtype, min_cgpa=cgpa, max_backlogs=backlogs,
            min_experience_months=exp, deadline=date.today() + timedelta(days=days), status=status,
        )
        job.skills = [JobSkill(skill_id=skills[n], importance=imp, weight=w) for n, imp, w in job_skills]
        job.allowed_branches = [JobAllowedBranch(branch_id=branches[b]) for b in job_branches]
        job.required_certifications = [JobRequiredCertification(certification_name=n) for n in certs]
        db.add(job)
        new_jobs += 1
    db.commit()
    return {"companies_added": new_companies, "jobs_added": new_jobs}


if __name__ == "__main__":
    import app.models  # noqa: F401
    from app.database.base import Base
    from app.database.session import SessionLocal, engine

    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        print(seed_demo_data(session))
