"""Skill-gap analysis: a student's skills VS the skills one job asks for.

Pure functions only (no database, no randomness). Everything is a simple rule that can be explained:

Match percentage - the same weighted share the recommender uses for its skill score:
    each required skill counts 1, each preferred ("nice to have") skill counts 0.5
    match % = weight of the skills the student has / weight of all the job's skills

Priority of a MISSING skill - high, medium or low:
    high    a required skill that is essential (the job gives it weight >= 3 of 5)
            OR a required skill that appears in at least 30% of all open jobs
    medium  any other required skill, or a preferred skill that appears in >= 30% of open jobs
    low     any other preferred skill
  Inside a level, skills are ordered by the job's own weight, then by how many open jobs ask for
  them, then by name. Each skill carries the reasons behind its level.

The analysis only describes what this job asks for. It makes no claim about how long a skill takes
to learn or whether learning it will lead to being hired.
"""
from dataclasses import dataclass, field

from app.ai.recommender import PREFERRED_SKILL_FACTOR

ESSENTIAL_WEIGHT = 3  # the job's own weight (1-5) from which a required skill counts as essential
HIGH_DEMAND_SHARE = 0.30  # share of open jobs asking for a skill that makes it "frequently requested"
TOP_PRIORITIES = 5

HIGH, MEDIUM, LOW = "high", "medium", "low"
_LEVEL_RANK = {HIGH: 3, MEDIUM: 2, LOW: 1}


# ---------- inputs ----------
@dataclass
class JobSkillInfo:
    skill_id: int
    name: str
    category: str | None
    required: bool
    weight: int  # 1-5, set by the coordinator on the job


# ---------- outputs ----------
@dataclass
class MatchedSkill:
    skill_id: int
    name: str
    category: str | None
    required: bool
    essential: bool
    weight: int
    student_level: str | None  # the student's own proficiency for this skill


@dataclass
class MissingSkill:
    skill_id: int
    name: str
    category: str | None
    required: bool
    essential: bool
    weight: int
    priority: str  # high | medium | low
    reasons: list[str]
    jobs_requiring: int  # how many open jobs list this skill
    demand_share: float  # jobs_requiring / open jobs (0 when there are no open jobs)


@dataclass
class PriorityItem:
    rank: int
    skill_id: int
    name: str
    level: str
    reasons: list[str]


@dataclass
class SkillGapResult:
    has_requirements: bool  # False when the job lists no skills at all
    match_percentage: int | None  # None when there is nothing to compare
    required_match_percentage: int | None  # None when the job has no required skills
    matched_count: int
    missing_count: int
    total_count: int
    required_total: int
    required_matched: int
    matched_skills: list[MatchedSkill]
    missing_skills: list[MissingSkill]  # most important first
    priority: list[PriorityItem]  # the top skills to work on, most important first
    student_has_skills: bool
    summary: str
    notes: list[str] = field(default_factory=list)


# ---------- rules ----------
def is_essential(skill: JobSkillInfo) -> bool:
    return skill.required and skill.weight >= ESSENTIAL_WEIGHT


def priority_level(skill: JobSkillInfo, demand_share: float) -> str:
    frequent = demand_share >= HIGH_DEMAND_SHARE
    if skill.required:
        return HIGH if (is_essential(skill) or frequent) else MEDIUM
    return MEDIUM if frequent else LOW


def explain_priority(skill: JobSkillInfo, demand: int, total_open: int) -> list[str]:
    reasons = ["Required for this job" if skill.required else "Preferred for this job (nice to have)"]
    if is_essential(skill):
        reasons.append(f"Essential: this job gives it a weight of {skill.weight} out of 5")
    elif skill.weight >= ESSENTIAL_WEIGHT:
        reasons.append(f"This job gives it a weight of {skill.weight} out of 5")
    if demand > 0 and total_open > 0:
        share = demand / total_open
        text = f"Asked for in {demand} of {total_open} open jobs ({round(share * 100)}%)"
        reasons.append(text + (": frequently requested" if share >= HIGH_DEMAND_SHARE else ""))
    return reasons


def _weighted_share(skills: list[JobSkillInfo], have: set[int]) -> float | None:
    total = got = 0.0
    for s in skills:
        w = 1.0 if s.required else PREFERRED_SKILL_FACTOR
        total += w
        if s.skill_id in have:
            got += w
    return got / total if total else None


def _summary(matched: int, total: int, req_matched: int, req_total: int, pct: int | None) -> str:
    if total == 0:
        return "This job lists no specific skills, so there is nothing to compare."
    if matched == total:
        return f"You have all {total} skills this job asks for."
    text = f"You have {matched} of {total} skills ({pct}%)."
    if req_total:
        text += f" Required skills: {req_matched} of {req_total}."
    return text


def analyze_skill_gap(
    job_skills: list[JobSkillInfo],
    student_levels: dict[int, str],
    demand: dict[int, int] | None = None,
    total_open_jobs: int = 0,
) -> SkillGapResult:
    """`student_levels` maps skill_id -> proficiency for every skill the student has.
    `demand` maps skill_id -> number of open jobs that list the skill."""
    demand = demand or {}
    have = set(student_levels)

    matched = [
        MatchedSkill(s.skill_id, s.name, s.category, s.required, is_essential(s), s.weight, student_levels[s.skill_id])
        for s in job_skills if s.skill_id in have
    ]
    missing = []
    for s in job_skills:
        if s.skill_id in have:
            continue
        count = demand.get(s.skill_id, 0)
        share = count / total_open_jobs if total_open_jobs else 0.0
        missing.append(MissingSkill(
            s.skill_id, s.name, s.category, s.required, is_essential(s), s.weight,
            priority_level(s, share), explain_priority(s, count, total_open_jobs), count, round(share, 4),
        ))
    missing.sort(key=lambda m: (-_LEVEL_RANK[m.priority], -m.weight, -m.jobs_requiring, m.name.lower()))
    matched.sort(key=lambda m: (not m.required, -m.weight, m.name.lower()))

    required = [s for s in job_skills if s.required]
    required_matched = sum(1 for s in required if s.skill_id in have)
    share = _weighted_share(job_skills, have)
    req_share = (required_matched / len(required)) if required else None
    pct = None if share is None else round(share * 100)

    notes = []
    if not have:
        notes.append("Your profile has no skills yet. Add the skills you have so the comparison is meaningful.")
    if job_skills and not required:
        notes.append("This job lists only preferred skills; none are strictly required.")

    return SkillGapResult(
        has_requirements=bool(job_skills),
        match_percentage=pct,
        required_match_percentage=None if req_share is None else round(req_share * 100),
        matched_count=len(matched),
        missing_count=len(missing),
        total_count=len(job_skills),
        required_total=len(required),
        required_matched=required_matched,
        matched_skills=matched,
        missing_skills=missing,
        priority=[PriorityItem(i + 1, m.skill_id, m.name, m.priority, m.reasons) for i, m in enumerate(missing[:TOP_PRIORITIES])],
        student_has_skills=bool(have),
        summary=_summary(len(matched), len(job_skills), required_matched, len(required), pct),
        notes=notes,
    )
