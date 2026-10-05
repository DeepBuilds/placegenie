"""CSV reports for the placement cell. The numbers come from coordinator_service, so reports and screens agree."""
import csv
import io
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, Job, JobStatus
from app.services import coordinator_service as cs

REPORTS = {
    "students": "All students with their profile, resume and placement status",
    "applications": "Every application with student, company, job and status",
    "placements": "Students who have been selected, with company and job",
    "companies": "Per company: jobs, applications, shortlisted, selected, rejected",
    "skills": "Skills asked for by open jobs and how many students have them",
}
_DANGEROUS_START = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value):
    """Stop spreadsheet programs from running a cell as a formula (CSV injection): text a student typed,
    such as a name beginning with '=', is prefixed with an apostrophe."""
    if isinstance(value, str) and value.startswith(_DANGEROUS_START):
        return "'" + value
    return "" if value is None else value


def to_csv(header: list[str], rows: list[list]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(v) for v in row])
    return "﻿" + out.getvalue()  # the byte-order mark makes Excel read the file as UTF-8


def build_report(db: Session, kind: str) -> tuple[str, str]:
    """Returns (file name, CSV text)."""
    if kind not in REPORTS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown report. Choose one of: {', '.join(REPORTS)}.")
    c = cs.load_cohort(db)
    by_id = {s.id: s for s in c.students}
    stamp = date.today().isoformat()

    if kind == "students":
        header = ["Student ID", "Name", "Email", "College", "Branch", "Year", "Semester", "CGPA", "Backlogs", "Profile complete %", "Resume uploaded", "Applications", "Placement stage"]
        rows = [
            [r.id, r.full_name, r.email, r.college, r.branch.name if r.branch else "", r.year, r.semester, r.cgpa, r.backlogs,
             r.profile_percent, "Yes" if r.has_resume else "No", r.applications, cs.STAGE_LABELS[r.stage]]
            for r in (cs._row(c, s) for s in c.students)
        ]
    elif kind == "applications":
        header = ["Application ID", "Student", "Student email", "Branch", "Company", "Job", "Status", "Applied on", "Last updated"]
        rows = [
            [a.id, by_id[a.student_id].full_name, by_id[a.student_id].user.email, by_id[a.student_id].branch.name if by_id[a.student_id].branch else "",
             a.job.company.name, a.job.title, a.status.value.replace("_", " "), a.applied_at.date().isoformat(), a.updated_at.date().isoformat()]
            for a in c.applications
        ]
    elif kind == "placements":
        header = ["Student ID", "Student", "Email", "Branch", "CGPA", "Company", "Job", "Selected (last updated)"]
        rows = [
            [a.student_id, by_id[a.student_id].full_name, by_id[a.student_id].user.email, by_id[a.student_id].branch.name if by_id[a.student_id].branch else "",
             float(by_id[a.student_id].cgpa) if by_id[a.student_id].cgpa is not None else "", a.job.company.name, a.job.title, a.updated_at.date().isoformat()]
            for a in c.applications if a.status.value == "selected"
        ]
    elif kind == "companies":
        open_jobs = dict(db.execute(select(Company.name, func.count(Job.id)).join(Job, Job.company_id == Company.id).where(Job.status == JobStatus.OPEN).group_by(Company.name)).all())
        header = ["Company", "Jobs", "Open jobs", "Applications", "Shortlisted / in process", "Selected", "Rejected"]
        rows = [[r.company, r.jobs, open_jobs.get(r.company, 0), r.applications, r.shortlisted, r.selected, r.rejected] for r in cs.company_stats(db, c)]
    else:  # skills
        header = ["Skill", "Open jobs requiring it", "Students who have it", "% of students"]
        rows = [[r.skill, r.jobs_requiring, r.students_with, r.students_percent] for r in cs.skill_supply(db, c, limit=None)]

    return f"placegenie-{kind}-{stamp}.csv", to_csv(header, rows)

