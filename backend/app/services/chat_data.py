"""Answers about the logged-in student's own PlaceGenie data, built straight from the existing services.

These replies never go through a language model, so every number, status and requirement in them is exact.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.chatbot import knowledge
from app.ai.chatbot.intents import JobMatch, JobRef, find_jobs
from app.ai.chatbot.prompt import StudentSummary
from app.ai.chatbot.types import SOURCE_DATA, SOURCE_LIMIT, Draft
from app.models import Student, User
from app.services import (
    application_service,
    eligibility_service,
    profile_service,
    recommendation_service,
    resume_service,
    skill_gap_service,
)

GUIDANCE_NOTE = "This is guidance based on your PlaceGenie profile; the company and placement cell make the final decision."
STATUS_MARK = {"passed": "✓ Passed", "failed": "✗ Failed", "not_evaluated": "? Not checked"}


def _when(dt: datetime | None) -> str:
    return dt.strftime("%a %d %b %Y, %I:%M %p") if dt else "date not set"


def _label(status: str) -> str:
    return status.replace("_", " ").capitalize()


def _ask_which_job(match: JobMatch, verb: str) -> Draft:
    lines = [f"- {j.title} at {j.company}" for j in match.jobs[:6]]
    return Draft(
        "I found more than one job that fits. Which one do you mean?\n" + "\n".join(lines),
        SOURCE_DATA,
        [f"{verb} {j.title} at {j.company}" for j in match.jobs[:4]],
    )


def _suggest_jobs(db: Session, user: User, verb: str, text: str) -> Draft:
    page = recommendation_service.recommend_for(db, user, limit=3)
    chips = [f"{verb} {i.job.title} at {i.job.company.name}" for i in page.items]
    return Draft(text, SOURCE_DATA, chips)


# ---------------------------------------------------------------- eligibility
def eligibility(db: Session, user: User, message: str, jobs: list[JobRef]) -> Draft:
    match = find_jobs(message, jobs)
    if match.kind == "many":
        return _ask_which_job(match, "Am I eligible for")
    if match.kind == "one":
        r = eligibility_service.check_for_student(db, user, match.job.id)
        verdict = {"ELIGIBLE": "ELIGIBLE ✓", "NOT_ELIGIBLE": "NOT ELIGIBLE ✗", "INCOMPLETE_PROFILE": "CANNOT BE FULLY CHECKED ?"}[r.result]
        lines = [f"Eligibility for {r.job.title} at {r.job.company}: {verdict}", r.summary, ""]
        lines += [f"- {c.label}: {STATUS_MARK[c.status]}. Required: {c.required}; you: {c.actual}." for c in r.criteria]
        if r.missing_skills:
            lines.append(f"\nRequired skills you are missing: {', '.join(r.missing_skills)}.")
        if r.missing_certifications:
            lines.append(f"Required certifications you are missing: {', '.join(r.missing_certifications)}.")
        if r.incomplete_fields:
            lines.append(f"Complete these in your profile for a full check: {', '.join(r.incomplete_fields)}.")
        lines += ["", GUIDANCE_NOTE]
        chips = [f"Skill gap for {r.job.title} at {r.job.company}"] if not r.eligible else []
        return Draft("\n".join(lines), SOURCE_DATA, chips)

    page = recommendation_service.recommend_for(db, user, eligible_only=True, limit=5)
    c = page.counts
    total = c.eligible + c.incomplete_profile + c.not_eligible
    if total == 0:
        return Draft("There are no open jobs right now, so there is nothing to check.", SOURCE_DATA)
    lines = [f"You currently meet the requirements for {c.eligible} of {total} open jobs."]
    if page.items:
        lines.append("Your best eligible matches:")
        lines += [f"- {i.job.title} at {i.job.company.name} ({i.match_score}% match)" for i in page.items]
    else:
        lines.append("None of the open jobs are fully matched yet.")
    if c.incomplete_profile:
        lines.append(f"{c.incomplete_profile} more could not be fully checked because your profile is incomplete.")
    lines += [*[f"- {h}" for h in page.profile_hints[:3]], "", GUIDANCE_NOTE]
    chips = [f"Am I eligible for {i.job.title} at {i.job.company.name}?" for i in page.items[:3]]
    return Draft("\n".join(lines), SOURCE_DATA, chips)


# ---------------------------------------------------------------- skill gap
def skill_gap(db: Session, user: User, message: str, jobs: list[JobRef]) -> Draft:
    match = find_jobs(message, jobs)
    if match.kind == "many":
        return _ask_which_job(match, "Skill gap for")
    if match.kind == "none":
        return _suggest_jobs(db, user, "Skill gap for", "Which job should I compare your skills with? For example: \"skill gap for Data Analyst\". Some jobs that suit you:")
    g = skill_gap_service.analyze_for_student(db, user, match.job.id)
    if not g.has_requirements:
        return Draft(f"{g.job.title} at {g.job.company} lists no specific skills, so there is nothing to compare.", SOURCE_DATA)
    lines = [f"Skill gap for {g.job.title} at {g.job.company}", g.summary]
    if g.matched_skills:
        lines.append("\nYou have: " + ", ".join(m.name for m in g.matched_skills) + ".")
    if g.missing_skills:
        lines.append("\nMissing, most important first:")
        lines += [f"- {m.name} ({m.priority} priority, {'required' if m.required else 'preferred'}): {m.reasons[1] if len(m.reasons) > 1 else m.reasons[0]}" for m in g.missing_skills[:6]]
    else:
        lines.append("\nYou have every skill this job lists.")
    lines += [*[f"\n{n}" for n in g.notes], "", g.disclaimer]
    return Draft("\n".join(lines), SOURCE_DATA, [f"Am I eligible for {g.job.title} at {g.job.company}?"])


# ---------------------------------------------------------------- recommendations
def recommend(db: Session, user: User) -> Draft:
    page = recommendation_service.recommend_for(db, user, limit=5)
    if not page.items:
        return Draft("There are no open jobs to recommend right now.", SOURCE_DATA)
    lines = ["Your top matches right now:"]
    for i in page.items:
        flag = "eligible" if i.eligibility.eligible else "not eligible yet" if i.eligibility.result == "NOT_ELIGIBLE" else "profile incomplete"
        lines.append(f"- {i.job.title} at {i.job.company.name}: {i.match_score}% match ({flag})")
    if page.profile_hints:
        lines += ["", "To improve these recommendations:", *[f"- {h}" for h in page.profile_hints[:3]]]
    lines += ["", "Open the Recommended page to see why each job scored the way it did."]
    chips = [f"Skill gap for {i.job.title} at {i.job.company.name}" for i in page.items[:2]]
    return Draft("\n".join(lines), SOURCE_DATA, chips)


# ---------------------------------------------------------------- applications & interviews
def applications(db: Session, user: User, message: str) -> Draft:
    result = application_service.list_mine(db, user, None, None)
    if not result.items:
        return Draft("You have not applied to any job yet. Open a job in PlaceGenie and choose Apply.", SOURCE_DATA, ["Recommend jobs for me"])
    refs = [JobRef(a.job.id, a.job.title, a.job.company) for a in result.items]
    match = find_jobs(message, refs)
    shown = [a for a in result.items if a.job.id in {j.id for j in match.jobs}] if match.kind != "none" else result.items
    lines = [f"You have {len(result.items)} application{'s' if len(result.items) != 1 else ''}:" if match.kind == "none" else "Matching applications:"]
    for a in shown[:8]:
        extra = f" - next interview {_when(a.next_interview)}" if a.next_interview else ""
        lines.append(f"- {a.job.title} at {a.job.company}: {_label(a.status.value)}{extra}")
    lines += ["", "These statuses are what the placement cell has recorded in PlaceGenie; I do not have live information from the companies."]
    return Draft("\n".join(lines), SOURCE_DATA, ["Show my upcoming interviews"])


def interviews(db: Session, user: User) -> Draft:
    result = application_service.list_interviews(db, user, "upcoming")
    c = result.counts
    if not result.items:
        text = "You have no upcoming interviews recorded in PlaceGenie."
        if c["needs_result"]:
            text += f" {c['needs_result']} past interview{'s have' if c['needs_result'] != 1 else ' has'} no result yet: open the Interview tracker to update."
        return Draft(text, SOURCE_DATA, ["How do I prepare for a technical interview?"])
    lines = [f"Your upcoming interviews ({len(result.items)}):"]
    for i in result.items[:6]:
        lines.append(f"- {_when(i.scheduled_at)}: {i.stage.value.replace('_', ' ')} for {i.application.job.title} at {i.application.job.company}")
    if c["needs_result"]:
        lines.append(f"\nAlso, {c['needs_result']} past interview{'s have' if c['needs_result'] != 1 else ' has'} no result recorded yet.")
    return Draft("\n".join(lines), SOURCE_DATA, ["How do I prepare for a technical interview?", "Tips for the HR interview"])


# ---------------------------------------------------------------- resume & profile
def resume(db: Session, user: User) -> Draft:
    current = resume_service.current_resume(db, user)
    if current is None:
        guide = knowledge.TOPICS_BY_ID["resume_writing"]
        return Draft(
            "You have not uploaded a resume yet. Upload a PDF on the Resume page to get a section-by-section review.\n\nMeanwhile, " + guide.answer[0].lower() + guide.answer[1:],
            SOURCE_DATA,
        )
    a = resume_service.get_analysis(db, user, current.id)
    lines = [f"Your resume ({a.resume.original_name}) scores {a.completeness_score}/100 for completeness, with {len(a.skills)} recognised skills."]
    if a.sections_missing:
        lines.append("Sections not found: " + ", ".join(s.label for s in a.sections_missing) + ".")
    top = [s for s in a.suggestions][:4]
    if top:
        lines += ["", "Most useful improvements:", *[f"- {s.text}" for s in top]]
    else:
        lines.append("No improvements to suggest: it covers the basics.")
    lines += ["", "The review is automated and keyword-based, so treat it as a checklist. Details are on the Resume analysis page."]
    return Draft("\n".join(lines), SOURCE_DATA, ["Show my skill gap"])


def profile(db: Session, user: User) -> Draft:
    p = profile_service.to_profile_out(profile_service.get_student(db, user))
    lines = [f"Your profile is {p.completeness.score}% complete."]
    lines.append(f"Branch: {p.branch.name if p.branch else 'not set'}; CGPA: {p.cgpa if p.cgpa is not None else 'not set'}; backlogs: {p.backlogs}.")
    lines.append("Skills: " + (", ".join(s.name for s in p.skills) if p.skills else "none added yet") + ".")
    if p.completeness.missing:
        lines += ["", "Still missing:", *[f"- {m}" for m in p.completeness.missing]]
    return Draft("\n".join(lines), SOURCE_DATA, ["Recommend jobs for me"])


# ---------------------------------------------------------------- what the assistant cannot know
def realtime_limit() -> Draft:
    topic = knowledge.TOPICS_BY_ID["realtime_limits"]
    return Draft(topic.answer, SOURCE_LIMIT, list(topic.follow_ups))


# ---------------------------------------------------------------- summary for an LLM
def build_summary(db: Session, student: Student, user: User) -> StudentSummary:
    """Academic facts only; no name, email, phone, resume text or interview notes."""
    profile_out = profile_service.to_profile_out(student)
    apps = application_service.list_mine(db, user, None, None)
    upcoming = application_service.list_interviews(db, user, "upcoming")
    return StudentSummary(
        branch=profile_out.branch.name if profile_out.branch else None,
        year=profile_out.year,
        semester=profile_out.semester,
        cgpa=profile_out.cgpa,
        backlogs=profile_out.backlogs,
        skills=[s.name for s in profile_out.skills],
        preferred_roles=[r.name for r in profile_out.preferred_roles],
        projects=len(profile_out.projects),
        certifications=len(profile_out.certifications),
        application_counts=apps.counts,
        upcoming_interviews=upcoming.total,
        resume_uploaded=resume_service.current_resume(db, user) is not None,
        profile_complete_percent=profile_out.completeness.score,
    )

