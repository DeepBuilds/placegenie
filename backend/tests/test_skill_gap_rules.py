"""Unit tests of the pure skill-gap rules (no database, no HTTP)."""
import pytest

from app.ai.skill_gap import (
    ESSENTIAL_WEIGHT,
    HIGH_DEMAND_SHARE,
    TOP_PRIORITIES,
    JobSkillInfo,
    analyze_skill_gap,
    explain_priority,
    priority_level,
)


def skill(sid, name, required=True, weight=1, category=None):
    return JobSkillInfo(sid, name, category, required, weight)


PY, SQL, DOCKER, AWS, EXCEL = (skill(1, "Python", weight=3), skill(2, "SQL", weight=2), skill(3, "Docker", weight=2),
                               skill(4, "AWS", weight=1), skill(5, "Excel", required=False, weight=1))
JOB = [PY, SQL, DOCKER, AWS, EXCEL]


def run(job=JOB, have=(), demand=None, total=0):
    return analyze_skill_gap(job, {sid: "beginner" for sid in have}, demand, total)


def names(items):
    return [i.name for i in items]


# ---------- the five required scenarios ----------
def test_complete_match():
    r = run(have={1, 2, 3, 4, 5})
    assert r.match_percentage == 100 and r.required_match_percentage == 100
    # required first, then heavier weights, then name
    assert names(r.matched_skills) == ["Python", "Docker", "SQL", "AWS", "Excel"]
    assert r.missing_skills == [] and r.priority == [] and r.missing_count == 0
    assert "all 5 skills" in r.summary


def test_partial_match():
    r = run(have={1, 2})  # Python + SQL of: Python, SQL, Docker, AWS (required) + Excel (preferred)
    assert names(r.matched_skills) == ["Python", "SQL"]
    assert set(names(r.missing_skills)) == {"Docker", "AWS", "Excel"}
    assert r.matched_count == 2 and r.missing_count == 3 and r.total_count == 5
    assert r.required_matched == 2 and r.required_total == 4 and r.required_match_percentage == 50
    assert r.match_percentage == round(100 * 2 / 4.5)  # weights: 4 required x1 + 1 preferred x0.5
    assert r.summary == "You have 2 of 5 skills (44%). Required skills: 2 of 4."


def test_zero_match():
    r = run(have={99})  # a skill that is not part of this job
    assert r.match_percentage == 0 and r.required_match_percentage == 0
    assert r.matched_skills == [] and r.missing_count == 5 and r.student_has_skills is True
    assert r.notes == []


def test_empty_student_skills():
    r = run(have=())
    assert r.match_percentage == 0 and r.matched_skills == [] and r.missing_count == 5
    assert r.student_has_skills is False
    assert any("no skills yet" in n for n in r.notes)
    assert r.priority  # there is still something to prioritise


def test_job_with_no_skills_at_all():
    r = run(job=[], have={1, 2})
    assert r.has_requirements is False and r.match_percentage is None and r.required_match_percentage is None
    assert r.matched_skills == [] and r.missing_skills == [] and r.priority == [] and r.total_count == 0
    assert "nothing to compare" in r.summary


def test_job_with_no_required_skills_only_preferred():
    job = [skill(1, "Python", required=False, weight=2), skill(2, "SQL", required=False, weight=1)]
    r = run(job=job, have={1})
    assert r.required_total == 0 and r.required_match_percentage is None
    assert r.match_percentage == 50 and names(r.missing_skills) == ["SQL"]
    assert r.missing_skills[0].priority == "low"
    assert any("only preferred" in n for n in r.notes)
    assert "Required skills" not in r.summary


# ---------- match percentage ----------
def test_percentage_matches_the_recommender_formula():
    # required counts 1, preferred 0.5 - identical to the recommender's skill component
    job = [skill(1, "A"), skill(2, "B"), skill(3, "C", required=False)]
    assert run(job=job, have={1}).match_percentage == round(100 * 1 / 2.5)
    assert run(job=job, have={3}).match_percentage == round(100 * 0.5 / 2.5)
    assert run(job=job, have={1, 2}).match_percentage == 80


def test_job_weight_does_not_change_the_percentage():
    light = [skill(1, "A", weight=1), skill(2, "B", weight=1)]
    heavy = [skill(1, "A", weight=5), skill(2, "B", weight=1)]
    assert run(job=light, have={1}).match_percentage == run(job=heavy, have={1}).match_percentage == 50


# ---------- priority rules ----------
def test_priority_levels():
    essential = skill(1, "Core", required=True, weight=ESSENTIAL_WEIGHT)
    plain = skill(2, "Plain", required=True, weight=1)
    nice = skill(3, "Nice", required=False, weight=5)
    assert priority_level(essential, 0.0) == "high"
    assert priority_level(plain, 0.0) == "medium"
    assert priority_level(nice, 0.0) == "low"  # a high job weight alone does not make a preferred skill urgent


def test_frequent_skills_are_promoted_one_level():
    plain, nice = skill(1, "Plain", required=True, weight=1), skill(2, "Nice", required=False, weight=1)
    assert priority_level(plain, HIGH_DEMAND_SHARE) == "high"
    assert priority_level(plain, HIGH_DEMAND_SHARE - 0.01) == "medium"
    assert priority_level(nice, HIGH_DEMAND_SHARE) == "medium"
    assert priority_level(nice, 0.05) == "low"


def test_missing_skills_are_ordered_by_level_then_weight_then_demand_then_name():
    job = [
        skill(1, "LowPref", required=False, weight=1),
        skill(2, "MedReq", required=True, weight=1),
        skill(3, "HighReq", required=True, weight=3),
        skill(4, "HighReqHeavier", required=True, weight=5),
        skill(5, "MedReqB", required=True, weight=1),
        skill(6, "MedReqC", required=True, weight=2),
    ]
    r = run(job=job, demand={5: 3, 2: 1, 6: 1}, total=20)
    assert names(r.missing_skills) == ["HighReqHeavier", "HighReq", "MedReqC", "MedReqB", "MedReq", "LowPref"]
    assert [m.priority for m in r.missing_skills] == ["high", "high", "medium", "medium", "medium", "low"]


def test_demand_breaks_ties_and_can_promote_required_skills():
    job = [skill(1, "Rare", weight=1), skill(2, "Common", weight=1)]
    r = run(job=job, demand={1: 1, 2: 8}, total=20)  # Common is asked for by 40% of open jobs
    assert names(r.missing_skills) == ["Common", "Rare"]
    assert r.missing_skills[0].priority == "high" and r.missing_skills[1].priority == "medium"
    assert r.missing_skills[0].jobs_requiring == 8 and r.missing_skills[0].demand_share == 0.4


def test_essential_flag():
    r = run(job=[skill(1, "A", weight=3), skill(2, "B", weight=2), skill(3, "C", required=False, weight=5)], have={1})
    assert r.matched_skills[0].essential is True
    assert {m.name: m.essential for m in r.missing_skills} == {"B": False, "C": False}


def test_reasons_are_plain_language_and_include_demand():
    reasons = explain_priority(skill(1, "Docker", weight=3), demand=7, total_open=18)
    assert reasons[0] == "Required for this job"
    assert "Essential: this job gives it a weight of 3 out of 5" in reasons
    assert "Asked for in 7 of 18 open jobs (39%): frequently requested" in reasons
    pref = explain_priority(skill(1, "X", required=False, weight=1), demand=1, total_open=18)
    assert pref[0].startswith("Preferred") and pref[-1] == "Asked for in 1 of 18 open jobs (6%)"
    assert len(explain_priority(skill(1, "X", weight=1), demand=0, total_open=18)) == 1  # no demand line when unknown


def test_priority_list_is_the_top_few_with_ranks():
    job = [skill(i, f"S{i}", weight=3) for i in range(1, 9)]
    r = run(job=job)
    assert len(r.missing_skills) == 8 and len(r.priority) == TOP_PRIORITIES
    assert [p.rank for p in r.priority] == [1, 2, 3, 4, 5]
    assert names(r.priority) == names(r.missing_skills)[:TOP_PRIORITIES]
    assert all(p.level == "high" and p.reasons for p in r.priority)


def test_no_demand_data_does_not_divide_by_zero():
    r = run(demand=None, total=0)
    assert all(m.demand_share == 0.0 and m.jobs_requiring == 0 for m in r.missing_skills)
    assert run(demand={1: 5}, total=0).missing_skills[0].demand_share == 0.0


def test_matched_skills_carry_the_students_level_and_required_first():
    r = analyze_skill_gap(JOB, {5: "advanced", 1: "intermediate"})
    assert [(m.name, m.student_level) for m in r.matched_skills] == [("Python", "intermediate"), ("Excel", "advanced")]


def test_output_never_contains_learning_claims():
    r = run(have={1})
    text = " ".join(r.summary.split() + [x for m in r.missing_skills for x in m.reasons] + r.notes).lower()
    for forbidden in ("weeks", "months", "hours", "guarantee", "will get", "course", "tutorial"):
        assert forbidden not in text
