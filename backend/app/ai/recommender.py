"""Transparent, rule-based job recommender.

How a job is scored (all numbers are visible to the student):

    fit   = weighted average of the components the student has data for   (0..1)
    score = fit * eligibility multiplier * 100                            (0..100)

Components (each 0..1) and their base weights:
    skills     0.45  weighted share of the job's skills the student has
    academic   0.20  CGPA headroom over the job's minimum (0 if the CGPA rule is failed)
    role       0.15  1 = a preferred role, 0.5 = same role family, 0 = otherwise
    interest   0.10  TF-IDF similarity: student interests/projects/experience VS job text
    resume     0.10  TF-IDF similarity: resume text VS job text (only when a resume exists)

A component with no data (e.g. the student chose no preferred roles) is *left out* and
the remaining weights are rescaled to sum to 1: missing data is never counted as a
zero or filled with a guess. If nothing at all can be scored the score is 0.

Eligibility (Phase 6 engine) multiplies the result:
    ELIGIBLE x1.0   INCOMPLETE_PROFILE x0.9   NOT_ELIGIBLE x0.5
so ineligible jobs stay visible ("stretch" jobs) but rank below jobs the student can apply to.

Everything lives behind the `Recommender` protocol so a machine-learning ranker can later
replace or augment `RuleBasedRecommender` without touching the API or the UI.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.ai.eligibility import (
    ELIGIBLE,
    INCOMPLETE_PROFILE,
    NOT_ELIGIBLE,
    EligibilityResult,
    JobSnapshot,
    StudentSnapshot,
    check_eligibility,
)
from app.ai.text_similarity import tfidf_similarities

WEIGHTS = {"skills": 0.45, "academic": 0.20, "role": 0.15, "interest": 0.10, "resume": 0.10}
LABELS = {
    "skills": "Skill match",
    "academic": "Academic fit",
    "role": "Preferred role",
    "interest": "Interest match",
    "resume": "Resume relevance",
}
ELIGIBILITY_MULTIPLIER = {ELIGIBLE: 1.0, INCOMPLETE_PROFILE: 0.9, NOT_ELIGIBLE: 0.5}

# Raw TF-IDF cosine between short texts is small even for good matches, so a similarity at
# or above this value counts as a full match (linear below it).
TEXT_SIMILARITY_SATURATION = 0.25
PREFERRED_SKILL_FACTOR = 0.5  # a preferred skill counts half as much as a required one


# ---------- inputs ----------
@dataclass
class StudentProfile:
    eligibility: StudentSnapshot
    interest_text: str = ""  # interests + projects + experience + certifications
    preferred_role_ids: set[int] = field(default_factory=set)
    preferred_role_categories: set[str] = field(default_factory=set)
    resume_text: str = ""


@dataclass
class JobProfile:
    job_id: int
    eligibility: JobSnapshot
    role_id: int | None
    role_name: str | None
    role_category: str | None
    text: str  # title + role + description + company industry + skill names


# ---------- outputs ----------
@dataclass
class Component:
    key: str
    label: str
    base_weight: float
    available: bool
    score: float  # 0..1
    note: str
    weight: float = 0.0  # effective weight after rescaling (0 if unavailable)
    points: float = 0.0  # contribution to the 0..100 fit before the eligibility multiplier


@dataclass
class Recommendation:
    job_id: int
    score: int  # 0..100
    eligibility: EligibilityResult
    eligibility_multiplier: float
    matched_skills: list[str]
    missing_skills: list[str]  # required skills the student lacks
    missing_preferred_skills: list[str]
    reasons: list[str]  # why this job was recommended
    concerns: list[str]  # what holds it back
    breakdown: list[Component]


class Recommender(Protocol):
    """Anything that can rank jobs for a student. An ML model would implement this too."""

    def recommend(
        self, student: StudentProfile, jobs: list[JobProfile], today: date | None = None
    ) -> list[Recommendation]: ...


# ---------- components ----------
def _unavailable(key: str, note: str) -> Component:
    return Component(key, LABELS[key], WEIGHTS[key], False, 0.0, note)


def score_skills(student: StudentProfile, job: JobProfile) -> tuple[Component, list[str], list[str], list[str]]:
    """Weighted share of the job's skills the student holds. Returns (component, matched, missing_required, missing_preferred)."""
    have = student.eligibility.skill_ids
    matched, missing_req, missing_pref = [], [], []
    got = total = 0.0
    for s in job.eligibility.skills:
        w = 1.0 if s.required else PREFERRED_SKILL_FACTOR
        total += w
        if s.skill_id in have:
            got += w
            matched.append(s.name)
        else:
            (missing_req if s.required else missing_pref).append(s.name)
    key = str.lower
    matched, missing_req, missing_pref = sorted(matched, key=key), sorted(missing_req, key=key), sorted(missing_pref, key=key)

    if not have:
        return _unavailable("skills", "Add skills to your profile."), matched, missing_req, missing_pref
    if total == 0:
        return _unavailable("skills", "This job lists no skills."), matched, missing_req, missing_pref
    n_req = sum(1 for s in job.eligibility.skills if s.required)
    note = f"{len(matched)}/{len(job.eligibility.skills)} skills matched"
    if n_req:
        note += f" ({n_req - len(missing_req)}/{n_req} required)"
    comp = Component("skills", LABELS["skills"], WEIGHTS["skills"], True, got / total, note)
    return comp, matched, missing_req, missing_pref


def score_academic(student: StudentProfile, job: JobProfile) -> Component:
    cgpa, minimum = student.eligibility.cgpa, job.eligibility.min_cgpa
    if cgpa is None:
        return _unavailable("academic", "Add your CGPA to your profile.")
    if cgpa < minimum:
        return Component("academic", LABELS["academic"], WEIGHTS["academic"], True, 0.0,
                         f"CGPA {cgpa:.2f} is below the required {minimum:.2f}")
    # Meeting the bar is worth 0.7; the remaining 0.3 grows with headroom up to a perfect 10.
    headroom = 0.0 if minimum >= 10 else (cgpa - minimum) / (10 - minimum)
    note = f"CGPA {cgpa:.2f} vs minimum {minimum:.2f}" if minimum > 0 else f"CGPA {cgpa:.2f} (no minimum)"
    return Component("academic", LABELS["academic"], WEIGHTS["academic"], True, 0.7 + 0.3 * headroom, note)


def score_role(student: StudentProfile, job: JobProfile) -> Component:
    if not student.preferred_role_ids:
        return _unavailable("role", "Choose preferred job roles in your profile.")
    if job.role_id is None:
        return Component("role", LABELS["role"], WEIGHTS["role"], True, 0.0, "This job has no role category")
    if job.role_id in student.preferred_role_ids:
        return Component("role", LABELS["role"], WEIGHTS["role"], True, 1.0, f"{job.role_name} is one of your preferred roles")
    if job.role_category and job.role_category in student.preferred_role_categories:
        return Component("role", LABELS["role"], WEIGHTS["role"], True, 0.5, f"{job.role_name} is in the same field as a preferred role")
    return Component("role", LABELS["role"], WEIGHTS["role"], True, 0.0, f"{job.role_name} is not one of your preferred roles")


def _text_component(key: str, text: str, similarity: float, missing_note: str, label_for_note: str) -> Component:
    if not text.strip():
        return _unavailable(key, missing_note)
    score = min(1.0, similarity / TEXT_SIMILARITY_SATURATION)
    return Component(key, LABELS[key], WEIGHTS[key], True, score,
                     f"{label_for_note} text similarity {similarity:.2f} (counts fully at {TEXT_SIMILARITY_SATURATION:.2f})")


# ---------- the rule-based recommender ----------
class RuleBasedRecommender:
    def recommend(self, student: StudentProfile, jobs: list[JobProfile], today: date | None = None) -> list[Recommendation]:
        today = today or date.today()
        # One TF-IDF fit for the whole batch: [interests, resume] against every job text.
        sims = tfidf_similarities([student.interest_text, student.resume_text], [j.text for j in jobs])
        return [
            self._score_one(student, job, interest_sim=sims[0][i], resume_sim=sims[1][i], today=today)
            for i, job in enumerate(jobs)
        ]

    def _score_one(self, student: StudentProfile, job: JobProfile, interest_sim: float, resume_sim: float, today: date) -> Recommendation:
        eligibility = check_eligibility(student.eligibility, job.eligibility, today)
        skills, matched, missing_req, missing_pref = score_skills(student, job)
        components = [
            skills,
            score_academic(student, job),
            score_role(student, job),
            _text_component("interest", student.interest_text, interest_sim, "Add interests or projects to your profile.", "Interest"),
            _text_component("resume", student.resume_text, resume_sim, "No resume uploaded yet.", "Resume"),
        ]

        available_weight = sum(c.base_weight for c in components if c.available)
        fit = 0.0
        if available_weight > 0:
            for c in components:
                if c.available:
                    c.weight = c.base_weight / available_weight
                    c.points = c.weight * c.score * 100
                    fit += c.weight * c.score
        multiplier = ELIGIBILITY_MULTIPLIER[eligibility.result]
        score = round(fit * multiplier * 100)

        reasons, concerns = _explain(student, job, components, eligibility, matched, missing_req, missing_pref, multiplier, available_weight > 0)
        return Recommendation(
            job_id=job.job_id, score=score, eligibility=eligibility, eligibility_multiplier=multiplier,
            matched_skills=matched, missing_skills=missing_req, missing_preferred_skills=missing_pref,
            reasons=reasons, concerns=concerns, breakdown=components,
        )


def _explain(student, job, components, eligibility, matched, missing_req, missing_pref, multiplier, scored) -> tuple[list[str], list[str]]:
    by = {c.key: c for c in components}
    reasons: list[str] = []
    concerns: list[str] = []

    if eligibility.eligible:
        reasons.append("You are eligible: you meet every listed requirement.")
    elif eligibility.result == INCOMPLETE_PROFILE:
        concerns.append("Eligibility could not be fully checked: complete your profile (" + ", ".join(eligibility.incomplete_fields) + ").")
    else:
        concerns.append(f"Not eligible yet: {len(eligibility.failed_requirements)} requirement(s) not met "
                        f"({', '.join(eligibility.failed_requirements)}). Score reduced by {round((1 - multiplier) * 100)}%.")
        concerns.extend(c.message for c in eligibility.criteria if c.status == "failed")

    sk = by["skills"]
    if sk.available:
        if matched:
            reasons.append(f"Skill match: {sk.note}: {', '.join(matched)}.")
        else:
            concerns.append("None of this job's skills are in your profile yet.")
        if missing_req:
            concerns.append("Missing required skills: " + ", ".join(missing_req) + ".")
        if missing_pref:
            concerns.append("Nice-to-have skills you lack: " + ", ".join(missing_pref) + ".")

    role = by["role"]
    if role.available and role.score >= 0.5:
        reasons.append(role.note[0].upper() + role.note[1:] + ".")
    ac = by["academic"]
    if ac.available and ac.score >= 0.7:
        reasons.append("Your academic profile satisfies the CGPA requirement (" + ac.note + ").")
    for key, text in (("interest", "Your interests and projects overlap with this job's description."),
                      ("resume", "Your resume's content is relevant to this job.")):
        if by[key].available and by[key].score >= 0.5:
            reasons.append(text)

    if not scored:
        concerns.append("Not enough profile information to score this job: " + " ".join(c.note for c in components if not c.available))
    if not reasons and scored:
        reasons.append("Limited overlap with your profile; shown for completeness.")
    return reasons, concerns


def build_job_text(title: str, role_name: str | None, description: str | None, industry: str | None, skill_names: list[str]) -> str:
    return " ".join(p for p in (title, role_name, description, industry, " ".join(skill_names)) if p)


def default_recommender() -> Recommender:
    """The single place that decides which engine ranks jobs: swap in an ML model here."""
    return RuleBasedRecommender()


def student_hints(student: StudentProfile) -> list[str]:
    """What the student could add to their profile to make recommendations more accurate."""
    hints = []
    if not student.eligibility.skill_ids:
        hints.append("Add your skills: skill match is the biggest part of the score.")
    if student.eligibility.cgpa is None:
        hints.append("Add your CGPA so academic fit and eligibility can be checked.")
    if student.eligibility.branch_id is None:
        hints.append("Select your branch so branch-restricted jobs can be checked.")
    if not student.preferred_role_ids:
        hints.append("Choose preferred job roles to rank jobs by the work you want.")
    if not student.interest_text.strip():
        hints.append("Add interests or projects so jobs can be matched to your topics.")
    return hints
