"""API tests: GET /recommendations on the seeded demo jobs."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text

from app.database.seed_demo import seed_demo_data
from app.models import Job, Resume, Student
from tests.conftest import auth_header

API = "/api/v1"
ME = f"{API}/students/me"
REC = f"{API}/recommendations"
CSE = "Computer Science and Engineering"
CIVIL = "Civil Engineering"


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def h(client, demo, student_token):
    return auth_header(student_token)


def lookup(client, h, path, name):
    return next(x["id"] for x in client.get(f"{API}/{path}", headers=h).json() if x["name"] == name)


def build_profile(client, h, *, branch=CSE, cgpa=8.2, backlogs=0, skills=(), roles=(), interests=None):
    assert client.put(ME, headers=h, json={
        "full_name": "Asha Patil", "branch_id": lookup(client, h, "branches", branch), "cgpa": cgpa,
        "backlogs": backlogs, "interests": interests}).status_code == 200
    assert client.put(f"{ME}/skills", headers=h, json={
        "skills": [{"skill_id": lookup(client, h, "skills", s)} for s in skills]}).status_code == 200
    ids = [lookup(client, h, "job-roles", r) for r in roles]
    assert client.put(f"{ME}/preferences", headers=h, json={"preferred_role_ids": ids}).status_code == 200


def recs(client, h, **params):
    res = client.get(REC, headers=h, params={"limit": 50, **params})
    assert res.status_code == 200, res.text
    return res.json()


def by_title(page):
    return {i["job"]["title"]: i for i in page["items"]}


DATA_SKILLS = ("Python", "Machine Learning", "Scikit-learn", "Pandas", "Statistics", "SQL")


# ---------- different profiles get different recommendations ----------
def test_data_student_gets_data_jobs_first(client, h):
    build_profile(client, h, skills=DATA_SKILLS, roles=("Data Scientist", "Machine Learning Engineer"),
                  interests="machine learning and statistics")
    page = recs(client, h)
    top = [i["job"]["title"] for i in page["items"][:3]]
    assert "Machine Learning Engineer" in top and "Data Scientist" in top
    assert page["items"][0]["match_score"] >= page["items"][-1]["match_score"]


def test_civil_student_gets_different_top_job(client, h):
    build_profile(client, h, branch=CIVIL, cgpa=7.0, skills=("AutoCAD", "Communication", "Teamwork"),
                  roles=("Graduate Engineer Trainee",), interests="construction site drawings")
    top = recs(client, h)["items"][0]
    assert top["job"]["title"] == "Site Engineer Trainee"
    assert top["eligibility"]["eligible"] is True and top["match_score"] >= 80


def test_two_students_with_different_profiles_see_different_rankings(client, h):
    build_profile(client, h, skills=DATA_SKILLS, roles=("Data Scientist",))
    first = [i["job"]["id"] for i in recs(client, h)["items"]]
    other = client.post(f"{API}/auth/register", json={"full_name": "Ravi", "email": "r@example.com", "password": "Passw0rd123"}).json()
    oh = auth_header(other["access_token"])
    build_profile(client, oh, branch="Mechanical Engineering", cgpa=6.5, skills=("AutoCAD", "MATLAB"), roles=("Graduate Engineer Trainee",))
    second = [i["job"]["id"] for i in recs(client, oh)["items"]]
    assert first != second and first[0] != second[0]


# ---------- different skill sets ----------
def test_more_matching_skills_give_a_higher_score(client, h):
    build_profile(client, h, skills=("Python",))
    few = by_title(recs(client, h))["Data Scientist"]["match_score"]
    build_profile(client, h, skills=DATA_SKILLS)
    many = by_title(recs(client, h))["Data Scientist"]["match_score"]
    assert many > few


def test_matched_and_missing_skills_are_reported_and_consistent_with_eligibility(client, h):
    build_profile(client, h, skills=("Python", "Statistics"))
    item = by_title(recs(client, h))["Data Scientist"]  # needs Python, Statistics, ML, SQL (+ NLP, Pandas preferred)
    assert item["matched_skills"] == ["Python", "Statistics"]
    assert item["missing_skills"] == ["Machine Learning", "SQL"]
    assert item["missing_preferred_skills"] == ["Natural Language Processing", "Pandas"]
    elig = client.post(f"{API}/jobs/{item['job']['id']}/eligibility", headers=h).json()
    assert elig["missing_skills"] == item["missing_skills"]  # the two engines agree
    assert elig["missing_preferred_skills"] == item["missing_preferred_skills"]


# ---------- eligible vs ineligible ----------
def test_ineligible_jobs_are_penalised_and_flagged(client, h):
    build_profile(client, h, cgpa=7.2, skills=DATA_SKILLS, roles=("Data Scientist",))
    page = recs(client, h)
    ds = by_title(page)["Data Scientist"]  # needs CGPA 8.0
    assert ds["eligibility"]["result"] == "NOT_ELIGIBLE" and ds["eligibility"]["multiplier"] == 0.5
    assert "CGPA" in ds["eligibility"]["failed_requirements"]
    assert any("Not eligible" in c for c in ds["concerns"])
    fit = sum(c["points"] for c in ds["breakdown"])
    assert ds["match_score"] == round(fit * 0.5)  # exactly half of the un-penalised fit


def test_becoming_eligible_raises_the_score_of_the_same_job(client, h):
    skills = ("Python", "Machine Learning", "Scikit-learn", "Pandas", "Statistics")
    build_profile(client, h, cgpa=7.5, skills=skills)  # Machine Learning Engineer needs CGPA 8.0
    blocked = by_title(recs(client, h))["Machine Learning Engineer"]
    assert blocked["eligibility"]["result"] == "NOT_ELIGIBLE"
    build_profile(client, h, cgpa=8.0, skills=skills)  # now exactly meets the CGPA bar
    ok = by_title(recs(client, h))["Machine Learning Engineer"]
    assert ok["eligibility"]["result"] == "ELIGIBLE"
    assert ok["match_score"] > blocked["match_score"]


def test_counts_and_eligible_only_filter(client, h):
    build_profile(client, h, cgpa=8.1, skills=DATA_SKILLS, roles=("Data Analyst",))
    page = recs(client, h)
    c = page["counts"]
    assert c["eligible"] + c["incomplete_profile"] + c["not_eligible"] == page["total"] > 0
    assert c["eligible"] == sum(i["eligibility"]["eligible"] for i in page["items"])
    only = recs(client, h, eligible_only="true")
    assert only["total"] == c["eligible"] and all(i["eligibility"]["eligible"] for i in only["items"])
    assert only["counts"] == c  # counts always describe all candidates


def test_incomplete_profile_is_marked_not_guessed(client, h):
    client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": lookup(client, h, "skills", "Excel")}]})
    page = recs(client, h)  # no CGPA / branch entered
    assert page["counts"]["incomplete_profile"] + page["counts"]["not_eligible"] == page["total"]
    ba = by_title(page)["Business Analyst Trainee"]
    assert ba["eligibility"]["result"] in ("INCOMPLETE_PROFILE", "NOT_ELIGIBLE")
    academic = next(c for c in ba["breakdown"] if c["key"] == "academic")
    assert academic["available"] is False and academic["weight"] == 0


# ---------- empty profile / no matches ----------
def test_empty_profile_gets_zero_scores_and_hints(client, h, demo):
    page = recs(client, h)
    open_future = demo.scalar(select(text("count(*)")).select_from(Job).where(Job.status == "open"))
    assert page["total"] == open_future
    assert all(i["match_score"] == 0 for i in page["items"])
    assert len(page["profile_hints"]) == 5
    assert all(not c["available"] for c in page["items"][0]["breakdown"])
    assert any("Not enough profile information" in c for c in page["items"][0]["concerns"])


def test_no_matching_jobs_returns_an_empty_page(client, h):
    build_profile(client, h, skills=DATA_SKILLS)
    page = recs(client, h, location="Antarctica")
    assert page["items"] == [] and page["total"] == 0
    assert page["counts"] == {"eligible": 0, "incomplete_profile": 0, "not_eligible": 0}
    nothing = recs(client, h, role_id=99999)
    assert nothing["items"] == [] and nothing["total"] == 0


def test_no_open_jobs_at_all(client, student_token):
    page = client.get(REC, headers=auth_header(student_token)).json()  # nothing seeded
    assert page["items"] == [] and page["total"] == 0


# ---------- filters, sorting, pagination ----------
def test_filter_by_role_and_location(client, h, demo):
    build_profile(client, h, skills=DATA_SKILLS)
    role = lookup(client, h, "job-roles", "Data Analyst")
    assert [i["job"]["title"] for i in recs(client, h, role_id=role)["items"]] == ["Data Analyst"]
    remote = recs(client, h, location="remote")
    assert {i["job"]["title"] for i in remote["items"]} == {"Android Developer", "Flutter Developer Intern"}
    assert recs(client, h, location="REMOTE")["total"] == 2  # case-insensitive
    both = recs(client, h, role_id=lookup(client, h, "job-roles", "Mobile App Developer"), location="remote")
    assert both["total"] == 2


def test_sorting(client, h):
    build_profile(client, h, skills=DATA_SKILLS, roles=("Data Scientist",), interests="statistics")
    desc = [i["match_score"] for i in recs(client, h, sort="score_desc")["items"]]
    asc = [i["match_score"] for i in recs(client, h, sort="score_asc")["items"]]
    assert desc == sorted(desc, reverse=True) and asc == sorted(asc)
    titles = [i["job"]["title"].lower() for i in recs(client, h, sort="title")["items"]]
    assert titles == sorted(titles)
    deadlines = [i["job"]["deadline"] for i in recs(client, h, sort="deadline")["items"]]
    assert deadlines == sorted(deadlines)
    assert client.get(REC, headers=h, params={"sort": "random"}).status_code == 422


def test_pagination(client, h):
    build_profile(client, h, skills=DATA_SKILLS)
    full = [i["job"]["id"] for i in recs(client, h)["items"]]
    p1 = client.get(REC, headers=h, params={"limit": 5, "offset": 0}).json()
    p2 = client.get(REC, headers=h, params={"limit": 5, "offset": 5}).json()
    assert p1["total"] == p2["total"] == len(full) and len(p1["items"]) == 5
    assert [i["job"]["id"] for i in p1["items"] + p2["items"]] == full[:10]  # stable, no overlap
    last = client.get(REC, headers=h, params={"limit": 5, "offset": len(full) - 2}).json()
    assert len(last["items"]) == 2
    assert client.get(REC, headers=h, params={"limit": 0}).status_code == 422
    assert client.get(REC, headers=h, params={"limit": 500}).status_code == 422
    assert client.get(REC, headers=h, params={"offset": -1}).status_code == 422


# ---------- inputs that change the score ----------
def test_interests_raise_the_interest_component(client, h):
    build_profile(client, h, skills=("Python",))
    before = next(c for c in by_title(recs(client, h))["Data Scientist"]["breakdown"] if c["key"] == "interest")
    assert before["available"] is False
    build_profile(client, h, skills=("Python",), interests="machine learning statistics models customer data")
    ds = by_title(recs(client, h))
    interest = lambda t: next(c for c in ds[t]["breakdown"] if c["key"] == "interest")
    assert interest("Data Scientist")["available"] and interest("Data Scientist")["score"] > interest("Site Engineer Trainee")["score"]


def test_preferred_role_boosts_that_role(client, h):
    build_profile(client, h, skills=("Python", "SQL"))
    base = by_title(recs(client, h))["Data Analyst"]["match_score"]
    build_profile(client, h, skills=("Python", "SQL"), roles=("Data Analyst",))
    boosted = by_title(recs(client, h))["Data Analyst"]
    role = next(c for c in boosted["breakdown"] if c["key"] == "role")
    assert role["score"] == 1.0
    assert boosted["match_score"] > base  # same eligibility, plus a perfect role component
    assert any("preferred roles" in r for r in boosted["reasons"])


def test_resume_text_is_used_when_present(client, h, demo):
    build_profile(client, h, skills=("Python",))
    assert next(c for c in by_title(recs(client, h))["Data Scientist"]["breakdown"] if c["key"] == "resume")["available"] is False
    student = demo.scalar(select(Student))
    demo.add(Resume(student_id=student.id, file_path="x.pdf", original_name="cv.pdf", mime_type="application/pdf",
                    size_bytes=10, extracted_text="Built machine learning models in Python with statistics and pandas"))
    demo.commit()
    ds = by_title(recs(client, h))
    resume = lambda t: next(c for c in ds[t]["breakdown"] if c["key"] == "resume")
    assert resume("Data Scientist")["available"] and resume("Data Scientist")["score"] > resume("Site Engineer Trainee")["score"]


def test_breakdown_is_complete_and_weights_sum_to_one(client, h):
    build_profile(client, h, skills=DATA_SKILLS, roles=("Data Scientist",), interests="statistics")
    for item in recs(client, h)["items"]:
        assert [c["key"] for c in item["breakdown"]] == ["skills", "academic", "role", "interest", "resume"]
        assert abs(sum(c["weight"] for c in item["breakdown"]) - 1.0) < 0.01
        assert 0 <= item["match_score"] <= 100 and item["reasons"] is not None


# ---------- which jobs are candidates ----------
def test_closed_and_expired_jobs_are_not_recommended(client, h, demo):
    build_profile(client, h, skills=DATA_SKILLS)
    titles = lambda: {i["job"]["title"] for i in recs(client, h)["items"]}
    assert "Frontend Developer (Closed Drive)" not in titles()  # closed
    demo.get(Job, demo.scalar(select(Job.id).where(Job.title == "Data Analyst"))).deadline = date.today() - timedelta(days=1)
    demo.commit()
    assert "Data Analyst" not in titles()  # past its deadline


def test_recommendations_are_deterministic_and_store_nothing(client, h, demo):
    build_profile(client, h, skills=DATA_SKILLS, roles=("Data Scientist",), interests="statistics")
    before = {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in ("students", "applications", "student_skills", "jobs")}
    one, two = recs(client, h), recs(client, h)
    assert one == two
    assert before == {t: demo.execute(text(f"select count(*) from {t}")).scalar() for t in before}


# ---------- authorization ----------
def test_requires_login(client, demo):
    assert client.get(REC).status_code == 401


def test_coordinators_cannot_use_student_recommendations(client, demo, coordinator_token):
    assert client.get(REC, headers=auth_header(coordinator_token)).status_code == 403


def test_each_student_only_gets_their_own_scores(client, h):
    build_profile(client, h, skills=DATA_SKILLS)
    mine = by_title(recs(client, h))["Data Scientist"]["match_score"]
    other = client.post(f"{API}/auth/register", json={"full_name": "Ravi", "email": "r2@example.com", "password": "Passw0rd123"}).json()
    theirs = by_title(recs(client, auth_header(other["access_token"])))["Data Scientist"]["match_score"]
    assert theirs == 0 and mine > 0


# ---------- the engine is swappable ----------
def test_service_uses_whatever_engine_default_recommender_returns(client, h, monkeypatch):
    from app.services import recommendation_service as svc

    class AlwaysFifty:
        def recommend(self, student, jobs, today=None):
            real = svc.RuleBasedRecommender().recommend(student, jobs, today)
            for r in real:
                r.score = 50
            return real

    monkeypatch.setattr(svc, "default_recommender", lambda: AlwaysFifty())
    assert {i["match_score"] for i in recs(client, h)["items"]} == {50}
