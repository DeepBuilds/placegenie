"""Unit tests of the pure rule engine (no database, no HTTP)."""
from datetime import date, timedelta

import pytest

from app.ai.eligibility import (
    ELIGIBLE,
    INCOMPLETE_PROFILE,
    NOT_ELIGIBLE,
    ExperiencePeriod,
    JobSkillReq,
    JobSnapshot,
    StudentSnapshot,
    check_eligibility,
    total_experience_months,
)

TODAY = date(2026, 6, 15)
CSE, ME = 1, 2


def student(**over) -> StudentSnapshot:
    base = dict(cgpa=8.1, branch_id=CSE, branch_name="CSE", backlogs=0,
                skill_ids={1, 2, 3}, certifications=["AWS CP"], experiences=[])
    return StudentSnapshot(**{**base, **over})


def job(**over) -> JobSnapshot:
    base = dict(
        is_open=True, deadline=TODAY + timedelta(days=10), min_cgpa=7.5, max_backlogs=2,
        min_experience_months=0, allowed_branches={CSE: "CSE"},
        skills=[JobSkillReq(1, "Python", True), JobSkillReq(2, "SQL", True), JobSkillReq(9, "Docker", False)],
        required_certifications=[],
    )
    return JobSnapshot(**{**base, **over})


def run(s=None, j=None):
    return check_eligibility(s or student(), j or job(), TODAY)


def crit(result, key):
    return next(c for c in result.criteria if c.key == key)


# ---------- the happy path ----------
def test_eligible_student_passes_everything():
    r = run()
    assert r.result == ELIGIBLE and r.eligible is True
    assert [c.status for c in r.criteria] == ["passed"] * 7
    assert r.failed_requirements == [] and r.reasons == [] and r.missing_skills == []
    assert [c.key for c in r.criteria] == ["cgpa", "branch", "backlogs", "skills", "certifications", "experience", "deadline"]


def test_pass_messages_show_required_vs_actual():
    r = run()
    assert (crit(r, "cgpa").required, crit(r, "cgpa").actual) == ("7.50 or above", "8.10")
    assert (crit(r, "branch").required, crit(r, "branch").actual) == ("CSE", "CSE")
    assert (crit(r, "backlogs").required, crit(r, "backlogs").actual) == ("At most 2", "0")
    assert crit(r, "skills").actual == "2/2 matched"


# ---------- CGPA ----------
def test_cgpa_exactly_at_minimum_passes():
    assert crit(run(student(cgpa=7.5)), "cgpa").status == "passed"


def test_low_cgpa_fails_with_clear_reason():
    r = run(student(cgpa=6.9))
    assert r.result == NOT_ELIGIBLE and r.eligible is False
    c = crit(r, "cgpa")
    assert c.status == "failed" and (c.required, c.actual) == ("7.50 or above", "6.90")
    assert "6.90" in c.message and "7.50" in c.message
    assert r.failed_requirements == ["CGPA"] and c.message in r.reasons


def test_no_cgpa_requirement_always_passes():
    assert crit(run(student(cgpa=2.0), job(min_cgpa=0)), "cgpa").status == "passed"
    assert crit(run(student(cgpa=None), job(min_cgpa=0)), "cgpa").status == "passed"


# ---------- branch ----------
def test_wrong_branch_fails_and_lists_allowed_branches():
    r = run(student(branch_id=ME, branch_name="Mechanical"))
    c = crit(r, "branch")
    assert c.status == "failed" and c.required == "CSE" and "Mechanical" in c.message
    assert r.failed_requirements == ["Branch"]


def test_job_with_no_branch_list_accepts_every_branch():
    r = run(student(branch_id=ME, branch_name="Mechanical"), job(allowed_branches={}))
    assert crit(r, "branch").status == "passed" and r.eligible


def test_multiple_allowed_branches_are_sorted_in_requirement():
    c = crit(run(j=job(allowed_branches={CSE: "CSE", 7: "Civil"})), "branch")
    assert c.required == "Civil, CSE"


# ---------- backlogs ----------
@pytest.mark.parametrize("backlogs,expected", [(0, "passed"), (2, "passed"), (3, "failed")])
def test_backlog_limit(backlogs, expected):
    assert crit(run(student(backlogs=backlogs)), "backlogs").status == expected


def test_zero_backlog_policy_wording():
    r = run(student(backlogs=1), job(max_backlogs=0))
    c = crit(r, "backlogs")
    assert c.status == "failed" and c.required == "No backlogs allowed" and "1 backlog" in c.message


def test_unlimited_backlogs_when_job_has_no_limit():
    assert crit(run(student(backlogs=9), job(max_backlogs=None)), "backlogs").status == "passed"


# ---------- skills ----------
def test_missing_required_skill_fails_and_is_listed():
    r = run(student(skill_ids={1}))
    c = crit(r, "skills")
    assert c.status == "failed" and c.actual == "1/2 matched" and "SQL" in c.message
    assert r.missing_skills == ["SQL"] and r.failed_requirements == ["Required skills"]


def test_preferred_skills_never_block_but_are_reported():
    r = run(student(skill_ids={1, 2}))
    assert r.eligible and r.missing_preferred_skills == ["Docker"] and r.missing_skills == []
    assert "0/1" in crit(r, "skills").message


def test_student_with_no_skills_fails_required_skills():
    r = run(student(skill_ids=set()))
    assert r.missing_skills == ["Python", "SQL"] and not r.eligible


def test_job_without_required_skills_passes_skill_check():
    r = run(student(skill_ids=set()), job(skills=[JobSkillReq(9, "Docker", False)]))
    assert crit(r, "skills").status == "passed" and r.missing_preferred_skills == ["Docker"]
    assert crit(run(student(), job(skills=[])), "skills").status == "passed"


# ---------- certifications ----------
def test_missing_certification_fails():
    r = run(j=job(required_certifications=["CompTIA Security+"]))
    c = crit(r, "certifications")
    assert c.status == "failed" and r.missing_certifications == ["CompTIA Security+"]
    assert c.actual == "0/1 held" and r.failed_requirements == ["Certifications"]


def test_certification_match_ignores_case_and_spacing():
    r = run(student(certifications=["  comptia   SECURITY+ "]), job(required_certifications=["CompTIA Security+"]))
    assert crit(r, "certifications").status == "passed" and r.missing_certifications == []


def test_partial_certifications_listed():
    r = run(student(certifications=["AWS CP"]), job(required_certifications=["AWS CP", "Azure Fundamentals"]))
    assert r.missing_certifications == ["Azure Fundamentals"] and crit(r, "certifications").actual == "1/2 held"


# ---------- experience ----------
def test_experience_requirement():
    six = job(min_experience_months=6)
    short = student(experiences=[ExperiencePeriod(date(2026, 4, 1), date(2026, 6, 1))])
    long = student(experiences=[ExperiencePeriod(date(2025, 6, 1), date(2026, 1, 1))])
    assert crit(run(short, six), "experience").status == "failed"
    assert crit(run(long, six), "experience").status == "passed"
    assert crit(run(student(), six), "experience").actual == "0 months"


def test_fresher_job_passes_experience_regardless():
    assert crit(run(student(experiences=[])), "experience").status == "passed"


def test_experience_months_merge_overlaps_and_handle_ongoing():
    a = ExperiencePeriod(date(2025, 1, 1), date(2025, 7, 1))
    b = ExperiencePeriod(date(2025, 4, 1), date(2025, 10, 1))  # overlaps a: union is Jan-Oct
    assert total_experience_months([a, b], TODAY) == 9
    assert total_experience_months([ExperiencePeriod(date(2026, 1, 15), None)], TODAY) == 5  # ongoing: Jan 15 -> Jun 15
    assert total_experience_months([ExperiencePeriod(None, date(2025, 1, 1))], TODAY) == 0  # no start
    assert total_experience_months([ExperiencePeriod(date(2027, 1, 1), None)], TODAY) == 0  # future start
    assert total_experience_months([], TODAY) == 0


# ---------- deadline / status ----------
def test_passed_deadline_fails():
    r = run(j=job(deadline=TODAY - timedelta(days=1)))
    assert crit(r, "deadline").status == "failed" and not r.eligible and "deadline" in crit(r, "deadline").message


def test_deadline_today_is_still_open_and_none_is_open():
    assert crit(run(j=job(deadline=TODAY)), "deadline").status == "passed"
    assert crit(run(j=job(deadline=None)), "deadline").status == "passed"


def test_closed_job_fails():
    assert crit(run(j=job(is_open=False)), "deadline").status == "failed"


# ---------- incomplete profile ----------
def test_missing_profile_data_is_not_treated_as_a_pass():
    r = run(student(cgpa=None, branch_id=None, branch_name=None))
    assert r.result == INCOMPLETE_PROFILE and r.eligible is False
    assert crit(r, "cgpa").status == "not_evaluated" and crit(r, "branch").status == "not_evaluated"
    assert r.incomplete_fields == ["CGPA", "Branch"] and r.failed_requirements == []


def test_a_real_failure_outranks_incomplete_profile():
    r = run(student(cgpa=None, backlogs=5))
    assert r.result == NOT_ELIGIBLE and "Backlogs" in r.failed_requirements
    assert r.incomplete_fields == ["CGPA"]


# ---------- multiple failures ----------
def test_multiple_failures_are_all_reported():
    r = run(student(cgpa=6.0, branch_id=ME, branch_name="Mechanical", backlogs=4, skill_ids=set(), certifications=[]),
            job(required_certifications=["X Cert"], min_experience_months=12))
    assert r.result == NOT_ELIGIBLE
    assert r.failed_requirements == ["CGPA", "Branch", "Backlogs", "Required skills", "Certifications", "Experience"]
    assert len(r.reasons) == 6 and "6 requirements" in r.summary
