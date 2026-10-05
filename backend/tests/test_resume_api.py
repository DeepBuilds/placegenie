"""API tests: /resumes upload, analysis, ownership and security."""
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.database.seed_demo import seed_demo_data
from app.models import Resume, ResumeAnalysis, ResumeDetectedSkill
from tests.conftest import auth_header
from tests.pdf_utils import FULL_RESUME, MISSING_SECTIONS_RESUME, make_pdf

API = "/api/v1"
ME = f"{API}/students/me"
RES = f"{API}/resumes"
PDF_HEADERS = ("application/pdf",)


@pytest.fixture
def demo(db_session):
    seed_demo_data(db_session)
    return db_session


@pytest.fixture
def h(client, demo, student_token):
    return auth_header(student_token)


@pytest.fixture
def other_h(client, demo):
    token = client.post(f"{API}/auth/register", json={"full_name": "Ravi Kumar", "email": "ravi@example.com", "password": "Passw0rd123"}).json()["access_token"]
    return auth_header(token)


def upload(client, h, data=None, name="resume.pdf", ctype="application/pdf"):
    data = make_pdf(FULL_RESUME) if data is None else data
    return client.post(RES, headers=h, files={"file": (name, data, ctype)})


def stored_files():
    root = get_settings().upload_path / "resumes"
    return sorted(p.name for p in root.glob("*")) if root.exists() else []


def skill_id(client, h, name):
    return next(s["id"] for s in client.get(f"{API}/skills", headers=h).json() if s["name"] == name)


# ---------- valid upload ----------
def test_valid_pdf_upload_returns_full_analysis(client, h):
    res = upload(client, h)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["resume"]["original_name"] == "resume.pdf" and body["resume"]["size_bytes"] > 500
    assert body["detected_name"] == "Asha Patil" and body["page_count"] == 1
    assert body["completeness_score"] >= 90
    assert body["contact"] == {"email": True, "phone": True, "linkedin": True, "github": True}
    assert [s["key"] for s in body["sections_found"]] == ["summary", "education", "skills", "projects", "experience", "certifications"]
    assert body["sections_missing"] == []
    assert body["education"][0]["cgpa"] == 8.4
    assert [p["title"] for p in body["projects"]][0] == "Placement Predictor"
    assert body["experience"][0]["dates"] == "Jun 2025 - Aug 2025"
    assert "Google Data Analytics Certificate" in body["certifications"]
    assert sum(p["earned"] for p in body["score_breakdown"]) == body["completeness_score"]
    assert "automated" in body["disclaimer"]
    assert len(stored_files()) == 1 and stored_files()[0].endswith(".pdf")


def test_analysis_is_persisted_and_can_be_fetched(client, h, db_session):
    rid = upload(client, h).json()["resume"]["id"]
    mine = client.get(f"{RES}/me", headers=h).json()
    assert mine["id"] == rid and mine["page_count"] == 1
    again = client.get(f"{RES}/{rid}/analysis", headers=h)
    assert again.status_code == 200 and again.json()["detected_name"] == "Asha Patil"
    db_session.expire_all()
    row = db_session.scalar(select(Resume))
    assert row.extracted_text and "Placement Predictor" in row.extracted_text and row.is_active
    assert row.analysis.completeness_score == again.json()["completeness_score"] and row.analysis.sections
    assert db_session.scalar(select(func.count()).select_from(ResumeDetectedSkill)) == len(again.json()["skills"]) > 5
    assert row.uploaded_at is not None


def test_no_resume_yet(client, h):
    assert client.get(f"{RES}/me", headers=h).json() is None


def test_skills_detected_with_evidence_and_profile_flag(client, h):
    skills = {s["name"]: s for s in upload(client, h).json()["skills"]}
    assert {"Python", "SQL", "Pandas", "Scikit-learn", "Flask", "MySQL", "REST APIs", "Git"} <= set(skills)
    assert "skills" in skills["Python"]["evidence"] and "projects" in skills["Python"]["evidence"]
    assert skills["Flask"]["evidence"] == ["projects"]
    assert all(s["in_profile"] is False for s in skills.values())  # profile is still empty


# ---------- resume with missing sections ----------
def test_resume_with_missing_sections_and_suggestions(client, h):
    body = upload(client, h, make_pdf(MISSING_SECTIONS_RESUME)).json()
    missing = {s["key"]: s["required"] for s in body["sections_missing"]}
    assert missing["skills"] is True and missing["projects"] is True and missing["certifications"] is False
    assert body["skills"] == [] and body["projects"] == [] and body["completeness_score"] < 40
    sugg = " ".join(s["text"] for s in body["suggestions"])
    assert "Skills section" in sugg and "phone number" in sugg
    assert body["suggestions"][0]["severity"] == "high"
    sev = [s["severity"] for s in body["suggestions"]]
    assert sev == sorted(sev, key={"high": 0, "medium": 1, "low": 2}.get)


# ---------- invalid / oversized / empty ----------
def test_text_file_is_rejected(client, h):
    res = upload(client, h, b"just some text, not a pdf", name="resume.txt", ctype="text/plain")
    assert res.status_code == 415 and "PDF" in res.json()["detail"]
    assert stored_files() == []


def test_word_document_is_rejected(client, h):
    res = upload(client, h, b"PK\x03\x04docx-bytes", name="resume.docx", ctype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert res.status_code == 415


def test_wrong_content_type_with_pdf_name_is_rejected(client, h):
    assert upload(client, h, ctype="text/html").status_code == 415


def test_fake_pdf_without_pdf_signature_is_rejected(client, h):
    res = upload(client, h, b"<html><script>alert(1)</script></html>", name="resume.pdf")
    assert res.status_code == 415 and "not a valid PDF" in res.json()["detail"]
    assert stored_files() == []


def test_extension_is_case_insensitive(client, h):
    assert upload(client, h, name="MY RESUME.PDF").status_code == 201


def test_corrupt_pdf_is_rejected_without_crashing(client, h):
    res = upload(client, h, b"%PDF-1.4\ngarbage that cannot be parsed\n%%EOF")
    assert res.status_code == 422 and "could not be read" in res.json()["detail"]
    assert stored_files() == []


def test_zero_byte_file_is_rejected(client, h):
    res = upload(client, h, b"")
    assert res.status_code == 422 and "empty" in res.json()["detail"]


@pytest.mark.parametrize("lines", [[], [""], ["Hi"]])
def test_empty_resume_without_text_is_rejected(client, h, lines):
    res = upload(client, h, make_pdf(lines))
    assert res.status_code == 422 and "No readable text" in res.json()["detail"]
    assert client.get(f"{RES}/me", headers=h).json() is None and stored_files() == []


def test_oversized_file_is_rejected(client, h, monkeypatch):
    monkeypatch.setattr(get_settings(), "resume_max_mb", 1)
    big = make_pdf(FULL_RESUME) + b"0" * (1024 * 1024 + 10)  # valid start, over the 1 MB limit
    res = upload(client, h, big)
    assert res.status_code == 413 and "1 MB" in res.json()["detail"]
    assert stored_files() == []


def test_file_just_under_the_limit_is_accepted(client, h, monkeypatch):
    monkeypatch.setattr(get_settings(), "resume_max_mb", 1)
    ok = make_pdf(FULL_RESUME) + b"0" * (1024 * 1024 - len(make_pdf(FULL_RESUME)) - 10)
    assert upload(client, h, ok).status_code == 201


def test_declared_huge_upload_is_refused_before_reading(client, h, monkeypatch):
    monkeypatch.setattr(get_settings(), "resume_max_mb", 1)
    res = client.post(RES, headers={**h, "Content-Length": str(50 * 1024 * 1024)}, files={"file": ("a.pdf", b"%PDF-", "application/pdf")})
    assert res.status_code == 413


def test_too_many_pages_is_rejected(client, h, monkeypatch):
    monkeypatch.setattr(get_settings(), "resume_max_pages", 2)
    res = upload(client, h, make_pdf([f"Line {i} with several words to read" for i in range(200)]))
    assert res.status_code == 422 and "at most 2" in res.json()["detail"]


def test_missing_file_field_is_a_validation_error(client, h):
    assert client.post(RES, headers=h).status_code == 422


# ---------- security: unauthorised access and ownership ----------
def test_all_endpoints_require_login(client, demo):
    assert client.post(RES, files={"file": ("a.pdf", make_pdf(FULL_RESUME), "application/pdf")}).status_code == 401
    for method, path in (("get", "/me"), ("get", "/1/analysis"), ("post", "/1/analyze"), ("post", "/1/sync-skills"), ("get", "/1/file"), ("delete", "/1")):
        assert getattr(client, method)(RES + path).status_code == 401, path


def test_coordinators_cannot_use_student_resume_endpoints(client, demo, coordinator_token):
    ch = auth_header(coordinator_token)
    assert client.get(f"{RES}/me", headers=ch).status_code == 403
    assert upload(client, ch).status_code == 403


def test_students_cannot_see_or_change_each_others_resumes(client, h, other_h):
    rid = upload(client, h).json()["resume"]["id"]
    for method, path in (("get", f"/{rid}/analysis"), ("post", f"/{rid}/analyze"), ("post", f"/{rid}/sync-skills"),
                         ("get", f"/{rid}/file"), ("delete", f"/{rid}")):
        res = getattr(client, method)(RES + path, headers=other_h)
        assert res.status_code == 404, (path, res.status_code)
        assert res.json()["detail"] == "Resume not found."
    assert client.get(f"{RES}/me", headers=other_h).json() is None
    assert client.get(f"{RES}/{rid}/analysis", headers=h).status_code == 200  # the owner is unaffected
    assert len(stored_files()) == 1


def test_unknown_resume_id_is_404_not_500(client, h):
    assert client.get(f"{RES}/99999/analysis", headers=h).status_code == 404
    assert client.get(f"{RES}/not-a-number/analysis", headers=h).status_code == 422


def test_client_filename_cannot_choose_the_stored_path(client, h, db_session):
    res = upload(client, h, name="../../../evil.pdf")
    assert res.status_code == 201 and res.json()["resume"]["original_name"] == "evil.pdf"
    db_session.expire_all()
    row = db_session.scalar(select(Resume))
    assert row.file_path.startswith("resumes/") and ".." not in row.file_path and "evil" not in row.file_path
    root = get_settings().upload_path.resolve()
    assert all(root in p.resolve().parents for p in root.rglob("*.pdf"))
    assert not list(Path(root.parent).glob("evil*"))


# ---------- replace / delete / download ----------
def test_new_upload_replaces_the_old_resume_and_deletes_its_file(client, h, db_session):
    first = upload(client, h).json()["resume"]["id"]
    old_files = stored_files()
    second = upload(client, h, make_pdf(MISSING_SECTIONS_RESUME)).json()["resume"]["id"]
    assert second != first and client.get(f"{RES}/me", headers=h).json()["id"] == second
    assert client.get(f"{RES}/{first}/analysis", headers=h).status_code == 404
    assert len(stored_files()) == 1 and stored_files() != old_files
    assert db_session.scalar(select(func.count()).select_from(Resume)) == 1
    assert db_session.scalar(select(func.count()).select_from(ResumeAnalysis)) == 1


def test_delete_removes_row_analysis_and_file(client, h, db_session):
    rid = upload(client, h).json()["resume"]["id"]
    assert client.delete(f"{RES}/{rid}", headers=h).status_code == 204
    assert client.get(f"{RES}/me", headers=h).json() is None and stored_files() == []
    for table in ("resumes", "resume_analyses", "resume_detected_skills"):
        assert db_session.execute(text(f"select count(*) from {table}")).scalar() == 0
    assert client.delete(f"{RES}/{rid}", headers=h).status_code == 404


def test_owner_can_download_the_original_file(client, h):
    pdf = make_pdf(FULL_RESUME)
    rid = upload(client, h, pdf).json()["resume"]["id"]
    res = client.get(f"{RES}/{rid}/file", headers=h)
    assert res.status_code == 200 and res.content == pdf
    assert res.headers["content-type"] == "application/pdf" and res.headers["x-content-type-options"] == "nosniff"


# ---------- comparisons with the profile and jobs ----------
def test_profile_comparison_and_sync_skills(client, h):
    client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": skill_id(client, h, "Python")}, {"skill_id": skill_id(client, h, "Docker")}]})
    body = upload(client, h).json()
    cmp = body["profile_comparison"]
    assert "Docker" in cmp["skills_not_on_resume"] and "Python" not in cmp["skills_not_on_resume"]
    assert "SQL" in [s["name"] for s in cmp["skills_not_in_profile"]]
    assert next(s for s in body["skills"] if s["name"] == "Python")["in_profile"] is True
    texts = " ".join(s["text"] for s in body["suggestions"])
    assert "missing from your profile" in texts and "does not mention" in texts

    rid = body["resume"]["id"]
    synced = client.post(f"{RES}/{rid}/sync-skills", headers=h).json()
    assert synced["profile_comparison"]["skills_not_in_profile"] == [] and all(s["in_profile"] for s in synced["skills"])
    profile = client.get(ME, headers=h).json()["skills"]
    assert {"Python", "SQL", "Pandas", "Docker"} <= {s["name"] for s in profile}
    assert next(s for s in profile if s["name"] == "SQL")["source"] == "resume"
    assert next(s for s in profile if s["name"] == "Python")["source"] == "manual"  # existing skills untouched


def test_cgpa_mismatch_is_reported(client, h):
    client.put(ME, headers=h, json={"full_name": "Asha Patil", "cgpa": 7.1, "backlogs": 0})
    cmp = upload(client, h).json()["profile_comparison"]
    assert cmp["resume_cgpa"] == 8.4 and cmp["profile_cgpa"] == 7.1 and cmp["cgpa_mismatch"] is True
    assert "CGPA" in " ".join(s["text"] for s in upload(client, h).json()["suggestions"] if s["severity"] == "high")


def test_job_relevance_favours_data_jobs_for_a_data_resume(client, h):
    body = upload(client, h).json()
    rel = body["job_relevance"]
    assert 1 <= len(rel) <= 5 and [r["relevance"] for r in rel] == sorted((r["relevance"] for r in rel), reverse=True)
    top = {r["title"] for r in rel[:3]}
    assert top & {"Data Analyst", "Data Scientist", "Machine Learning Engineer"}
    assert all(0 <= r["relevance"] <= 100 for r in rel)
    assert "Site Engineer Trainee" not in {r["title"] for r in rel}
    best = rel[0]
    assert best["matched_skills"] and isinstance(best["missing_skills"], list)


def test_potentially_missing_skills_exclude_what_the_student_has(client, h):
    client.put(f"{ME}/skills", headers=h, json={"skills": [{"skill_id": skill_id(client, h, "Statistics")}]})
    potential = upload(client, h).json()["potentially_missing_skills"]
    names = {p["name"] for p in potential}
    assert names and "Python" not in names and "Statistics" not in names
    assert all(p["jobs_requiring"] >= 1 and p["example_jobs"] for p in potential)


def test_missing_profile_information_is_listed(client, h):
    info = upload(client, h).json()["profile_comparison"]["missing_profile_information"]
    assert "CGPA" in info and "Branch" in info


def test_reanalyze_rebuilds_the_analysis_from_stored_text(client, h, db_session):
    rid = upload(client, h).json()["resume"]["id"]
    before = client.get(f"{RES}/{rid}/analysis", headers=h).json()
    again = client.post(f"{RES}/{rid}/analyze", headers=h)
    assert again.status_code == 200
    assert again.json()["completeness_score"] == before["completeness_score"]
    assert [s["name"] for s in again.json()["skills"]] == [s["name"] for s in before["skills"]]
    assert db_session.scalar(select(func.count()).select_from(ResumeAnalysis)) == 1


def test_resume_text_now_feeds_job_recommendations(client, h):
    def resume_component():
        top = client.get(f"{API}/recommendations", headers=h, params={"limit": 50}).json()["items"]
        ds = next(i for i in top if i["job"]["title"] == "Data Scientist")
        return next(c for c in ds["breakdown"] if c["key"] == "resume")

    assert resume_component()["available"] is False
    upload(client, h)
    comp = resume_component()
    assert comp["available"] is True and comp["score"] > 0


def test_analysis_is_deterministic(client, h):
    rid = upload(client, h).json()["resume"]["id"]
    one = client.get(f"{RES}/{rid}/analysis", headers=h).json()
    two = client.get(f"{RES}/{rid}/analysis", headers=h).json()
    assert one == two
