"""Unit tests of the pure scoring logic (no database, no HTTP)."""
from datetime import date, timedelta

import pytest

from app.ai.eligibility import ELIGIBLE, NOT_ELIGIBLE, JobSkillReq, JobSnapshot, StudentSnapshot
from app.ai.recommender import (
    WEIGHTS,
    JobProfile,
    Recommender,
    RuleBasedRecommender,
    StudentProfile,
    score_academic,
    score_role,
    score_skills,
    student_hints,
)
from app.ai.text_similarity import tfidf_similarities

TODAY = date(2026, 6, 15)
CSE = 1


def snap(**over) -> StudentSnapshot:
    base = dict(cgpa=8.0, branch_id=CSE, branch_name="CSE", backlogs=0, skill_ids=set(), certifications=[], experiences=[])
    return StudentSnapshot(**{**base, **over})


def student(skills=(), cgpa=8.0, roles=(), categories=(), interests="", resume="", **snap_over) -> StudentProfile:
    return StudentProfile(
        eligibility=snap(skill_ids=set(skills), cgpa=cgpa, **snap_over),
        interest_text=interests, preferred_role_ids=set(roles),
        preferred_role_categories=set(categories), resume_text=resume,
    )


def job(job_id=1, skills=(), min_cgpa=7.0, role=(None, None, None), text="", allowed=None, max_backlogs=2, **over) -> JobProfile:
    snapshot = JobSnapshot(
        is_open=True, deadline=TODAY + timedelta(days=10), min_cgpa=min_cgpa, max_backlogs=max_backlogs,
        min_experience_months=0, allowed_branches=allowed if allowed is not None else {CSE: "CSE"},
        skills=[JobSkillReq(sid, name, req) for sid, name, req in skills], required_certifications=[],
    )
    return JobProfile(job_id=job_id, eligibility=snapshot, role_id=role[0], role_name=role[1], role_category=role[2], text=text)


PY, SQL, DOCKER = (1, "Python", True), (2, "SQL", True), (3, "Docker", False)
rec = RuleBasedRecommender()


def score_one(s, j):
    return rec.recommend(s, [j], TODAY)[0]


def comp(r, key):
    return next(c for c in r.breakdown if c.key == key)


# ---------- text similarity ----------
def test_related_texts_score_higher_than_unrelated():
    docs = ["python machine learning statistics models", "site engineer civil construction drawings"]
    sims = tfidf_similarities(["machine learning with python"], docs)[0]
    assert sims[0] > sims[1] and sims[1] == 0.0
    assert all(0.0 <= s <= 1.0 for s in sims)


def test_blank_or_stopword_only_text_scores_zero():
    assert tfidf_similarities([""], ["python developer"]) == [[0.0]]
    assert tfidf_similarities(["the and of"], ["the and of"]) == [[0.0]]
    assert tfidf_similarities([], ["x"]) == [] and tfidf_similarities(["x"], []) == [[]]


# ---------- skills ----------
def test_skill_score_weights_required_more_than_preferred():
    j = job(skills=[PY, SQL, DOCKER])  # total weight 1 + 1 + 0.5 = 2.5
    only_py, _, miss_req, miss_pref = score_skills(student(skills={1}), j)
    assert only_py.score == pytest.approx(1 / 2.5) and miss_req == ["SQL"] and miss_pref == ["Docker"]
    all_req, *_ = score_skills(student(skills={1, 2}), j)
    assert all_req.score == pytest.approx(2 / 2.5)  # skipping a preferred skill costs only 0.5
    everything, matched, *_ = score_skills(student(skills={1, 2, 3}), j)
    assert everything.score == 1.0 and matched == ["Docker", "Python", "SQL"]


def test_skill_component_unavailable_without_student_or_job_skills():
    assert not score_skills(student(skills=()), job(skills=[PY]))[0].available
    assert not score_skills(student(skills={1}), job(skills=[]))[0].available


# ---------- academic ----------
def test_academic_score():
    j = job(min_cgpa=7.0)
    assert score_academic(student(cgpa=6.9), j).score == 0.0
    assert score_academic(student(cgpa=7.0), j).score == pytest.approx(0.7)
    assert score_academic(student(cgpa=10), j).score == pytest.approx(1.0)
    mid = score_academic(student(cgpa=8.5), j).score
    assert 0.7 < mid < 1.0 and mid == pytest.approx(0.7 + 0.3 * (1.5 / 3))
    assert not score_academic(student(cgpa=None), j).available
    assert score_academic(student(cgpa=3.0), job(min_cgpa=0)).score > 0.7  # no minimum


# ---------- role ----------
def test_role_score():
    j = job(role=(5, "Data Analyst", "Data"))
    assert score_role(student(roles={5}), j).score == 1.0
    assert score_role(student(roles={9}, categories={"Data"}), j).score == 0.5
    assert score_role(student(roles={9}, categories={"Software"}), j).score == 0.0
    assert not score_role(student(roles=()), j).available
    assert score_role(student(roles={5}), job()).score == 0.0  # job without a role


# ---------- combining ----------
def test_weights_are_renormalised_over_available_components_only():
    r = score_one(student(skills={1, 2}, cgpa=None), job(skills=[PY, SQL], min_cgpa=0))
    assert [c.key for c in r.breakdown if c.available] == ["skills"]
    assert comp(r, "skills").weight == pytest.approx(1.0) and r.score == 100
    assert all(c.weight == 0 and c.points == 0 for c in r.breakdown if not c.available)


def test_available_weights_always_sum_to_one_and_points_to_the_fit():
    s = student(skills={1}, cgpa=8.0, roles={5}, interests="python data analysis")
    r = score_one(s, job(skills=[PY, SQL], role=(5, "Data Analyst", "Data"), text="python data analysis role"))
    avail = [c for c in r.breakdown if c.available]
    assert {c.key for c in avail} == {"skills", "academic", "role", "interest"}
    assert sum(c.weight for c in avail) == pytest.approx(1.0)
    assert sum(c.points for c in avail) * r.eligibility_multiplier == pytest.approx(r.score, abs=0.5)
    base = {k: WEIGHTS[k] for k in ("skills", "academic", "role", "interest")}
    assert comp(r, "skills").weight == pytest.approx(base["skills"] / sum(base.values()))


def test_perfect_match_scores_100():
    r = score_one(student(skills={1, 2}, cgpa=10), job(skills=[PY, SQL], min_cgpa=6))
    assert r.score == 100 and r.eligibility.result == ELIGIBLE


def test_eligibility_halves_the_score_of_an_otherwise_identical_job():
    s = student(skills={1, 2}, cgpa=8.0)
    ok = score_one(s, job(skills=[PY, SQL], min_cgpa=7.0))
    s_bad = student(skills={1, 2}, cgpa=8.0, backlogs=3)
    low = score_one(s_bad, job(skills=[PY, SQL], min_cgpa=7.0, max_backlogs=0))
    assert low.eligibility.result == NOT_ELIGIBLE and low.eligibility_multiplier == 0.5
    assert low.score == round(ok.score * 0.5)
    assert any("Not eligible" in c for c in low.concerns)


def test_scores_stay_within_0_and_100():
    for cgpa in (0.0, 5.0, 10.0):
        for skills in (set(), {1}, {1, 2, 3}):
            r = score_one(student(skills=skills, cgpa=cgpa, roles={5}, interests="python"), job(skills=[PY, SQL, DOCKER], role=(5, "A", "B"), text="python"))
            assert 0 <= r.score <= 100


# ---------- empty profile ----------
def test_empty_profile_scores_zero_with_explanations_and_hints():
    empty = student(skills=(), cgpa=None, branch_id=None, branch_name=None)
    r = score_one(empty, job(skills=[PY]))
    assert r.score == 0 and not any(c.available for c in r.breakdown)
    assert any("Not enough profile information" in c for c in r.concerns)
    assert len(student_hints(empty)) == 5
    assert student_hints(student(skills={1}, cgpa=8, roles={5}, interests="x")) == []


# ---------- explanations ----------
def test_reasons_and_concerns_explain_the_score():
    s = student(skills={1}, cgpa=9.0, roles={5}, interests="python data")
    r = score_one(s, job(skills=[PY, SQL, DOCKER], role=(5, "Data Analyst", "Data"), text="python data analyst"))
    text = " ".join(r.reasons)
    assert "Skill match: 1/3 skills matched (1/2 required): Python." in text
    assert "preferred roles" in text and "CGPA" in text and "interests" in text
    assert r.matched_skills == ["Python"] and r.missing_skills == ["SQL"] and r.missing_preferred_skills == ["Docker"]
    assert any("Missing required skills: SQL" in c for c in r.concerns)
    assert any("Not eligible" in c for c in r.concerns)  # SQL is required, so the student is not eligible yet
    # once the student has every required skill the explanation says so
    ok = score_one(student(skills={1, 2}, cgpa=9.0), job(skills=[PY, SQL]))
    assert any("You are eligible" in x for x in ok.reasons)


# ---------- different students rank differently ----------
def test_ranking_follows_the_student_profile():
    data_job = job(1, skills=[(1, "Python", True), (4, "Statistics", True)], role=(5, "Data Scientist", "Data"), text="python statistics machine learning models")
    civil_job = job(2, skills=[(7, "AutoCAD", True)], role=(6, "Site Engineer", "Core"), text="site drawings construction", allowed={9: "Civil"})
    data_student = student(skills={1, 4}, roles={5}, interests="machine learning statistics")
    civil_student = student(skills={7}, roles={6}, interests="construction drawings", branch_id=9, branch_name="Civil")
    for s, first in ((data_student, 1), (civil_student, 2)):
        ranked = sorted(rec.recommend(s, [data_job, civil_job], TODAY), key=lambda r: -r.score)
        assert ranked[0].job_id == first and ranked[0].score > ranked[1].score


# ---------- modularity ----------
def test_any_object_with_recommend_satisfies_the_protocol():
    class Constant:
        def recommend(self, student, jobs, today=None):
            return []

    engine: Recommender = Constant()
    assert engine.recommend(student(), [job()]) == []
