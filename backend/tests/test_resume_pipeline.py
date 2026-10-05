"""Unit tests of each stage of the resume pipeline (no database, no HTTP)."""
import pytest

from app.ai.resume.analyze import analyze_text, compare_with_profile, job_relevance, potentially_missing_skills, JobDoc
from app.ai.resume.clean import clean_text, word_count
from app.ai.resume.extract import ResumeExtractionError, extract_pdf_text
from app.ai.resume.parse import (
    parse_certifications,
    parse_contact,
    parse_education,
    parse_entries,
    parse_name,
    starts_with_action_verb,
)
from app.ai.resume.sections import heading_key, split_sections
from app.ai.resume.skills import SkillMatcher
from app.database.seed import SKILLS
from tests.pdf_utils import FULL_RESUME, MISSING_SECTIONS_RESUME, make_pdf

CATALOG = [(i + 1, n, c) for i, (n, c) in enumerate(SKILLS)]
IDS = {n: i for i, n, _ in CATALOG}
MATCHER = SkillMatcher(CATALOG)
CORPUS = ["python data analyst sql dashboards statistics reporting trends", "java backend developer spring rest apis"]


def analyse(lines):
    ex = extract_pdf_text(make_pdf(lines))
    return analyze_text(ex.text, ex.page_count, MATCHER, CORPUS)


# ---------- stage 1: extraction ----------
def test_extract_text_and_pages():
    ex = extract_pdf_text(make_pdf(["Hello resume world", "Second line of text that is long enough to pass"]))
    assert "Hello resume world" in ex.text and ex.page_count == 1


def test_extract_multi_page():
    ex = extract_pdf_text(make_pdf([f"Line number {i} with some words" for i in range(100)]))
    assert ex.page_count == 3 and "Line number 99" in ex.text


@pytest.mark.parametrize("lines", [[], [""], ["Hi"], ["    "]])
def test_extract_rejects_pdf_without_readable_text(lines):
    with pytest.raises(ResumeExtractionError, match="No readable text"):
        extract_pdf_text(make_pdf(lines))


def test_extract_rejects_corrupt_pdf():
    with pytest.raises(ResumeExtractionError, match="could not be read"):
        extract_pdf_text(b"%PDF-1.4\nthis is not really a pdf at all\n%%EOF")


def test_extract_enforces_page_limit():
    pdf = make_pdf([f"Line {i} of a very long document" for i in range(120)], lines_per_page=10)
    with pytest.raises(ResumeExtractionError, match="at most 10"):
        extract_pdf_text(pdf, max_pages=10)


# ---------- stage 2: cleaning ----------
def test_clean_normalises_bullets_ligatures_and_spacing():
    raw = "Skills  \n\n\n•  Built ﬁle   parser\n▪ Used  Python\n E D U C A T I O N\n"
    cleaned = clean_text(raw)
    assert "- Built file parser" in cleaned and "- Used Python" in cleaned
    assert "EDUCATION" in cleaned and "\n\n\n" not in cleaned and "   " not in cleaned


def test_clean_removes_control_characters_and_handles_empty():
    assert "\x00" not in clean_text("a\x00b\x07c")
    assert clean_text("") == "" and clean_text("   \n \n") == ""


def test_word_count():
    assert word_count("Built a REST API using Python, MySQL and C++.") == 9


# ---------- stage 3: sections ----------
@pytest.mark.parametrize("line,key", [
    ("EDUCATION", "education"), ("Technical Skills", "skills"), ("Academic Projects:", "projects"),
    ("Work Experience", "experience"), ("Certifications & Courses", "certifications"),
    ("Career Objective", "summary"), ("Awards", "achievements"), ("Programming Languages", "skills"),
])
def test_heading_detection(line, key):
    assert heading_key(line) == key


@pytest.mark.parametrize("line", ["", "- Education", "I completed my education in 2024 at a good college", "Python developer"])
def test_non_headings_are_not_detected(line):
    assert heading_key(line) is None


def test_split_sections_keeps_header_and_order():
    split = split_sections(clean_text("\n".join(FULL_RESUME)))
    assert split.found == ["summary", "education", "skills", "projects", "experience", "certifications"]
    assert split.header[0] == "ASHA PATIL"
    assert any("CGPA" in line for line in split.sections["education"])


# ---------- stage 4: information extraction ----------
def test_contact_detection():
    c = parse_contact("a.b@example.com +91 98765 43210 linkedin.com/in/ab github.com/ab")
    assert c == {"email": True, "phone": True, "linkedin": True, "github": True}
    assert parse_contact("no contact here, year 2024 and 8.4 cgpa") == {"email": False, "phone": False, "linkedin": False, "github": False}


@pytest.mark.parametrize("header,name", [
    (["ASHA PATIL", "a@x.com"], "Asha Patil"),
    (["Resume", "Ravi Kumar Singh"], "Ravi Kumar Singh"),
    (["Curriculum Vitae", "9876543210", "a@x.com"], None),
    (["Asha"], None),
])
def test_name_detection(header, name):
    assert parse_name(header, header) == name


def test_education_entries_do_not_bleed_into_each_other():
    lines = ["B.Tech in Computer Science", "ABC Institute of Technology, Pune", "2024 - 2028 CGPA: 8.4",
             "HSC (12th) - Science, XYZ Junior College, 2024, 88.5%"]
    first, second = parse_education(lines)
    assert first["degree"] == "B.Tech" and first["cgpa"] == 8.4 and first["years"] == "2024 - 2028"
    assert first["institution"] == "ABC Institute of Technology, Pune"
    assert second["degree"] == "HSC" and second["percentage"] == 88.5 and second["cgpa"] is None


def test_degree_be_is_case_sensitive():
    assert parse_education(["B.E. Mechanical, DEF College, 2026"])[0]["degree"].startswith("B.E")
    assert parse_education(["I want to be a developer at a good company"]) == []


def test_entries_group_titles_and_bullets_and_unwrap_lines():
    lines = ["Placement Predictor", "- Built a model that predicts", "placement outcomes accurately.",
             "- Improved accuracy by 13%.", "Student Portal", "- Developed a web portal."]
    entries = parse_entries(lines)
    assert [e["title"] for e in entries] == ["Placement Predictor", "Student Portal"]
    assert entries[0]["bullets"][0] == "Built a model that predicts placement outcomes accurately."
    assert len(entries[0]["bullets"]) == 2


def test_entry_dates_are_picked_up():
    e = parse_entries(["Data Intern - Acme   Jun 2025 - Aug 2025", "- Analysed data."])[0]
    assert e["dates"] == "Jun 2025 - Aug 2025"


def test_certifications_and_action_verbs():
    assert parse_certifications(["- AWS Cloud Practitioner", "- AWS Cloud Practitioner", "x"]) == ["AWS Cloud Practitioner"]
    assert starts_with_action_verb("Built a parser") and not starts_with_action_verb("Responsible for parsing")


# ---------- stage 5: skill detection ----------
def detect(skills_lines=(), other=None):
    sections = {"skills": list(skills_lines), **(other or {})}
    return {d.name: d.evidence for d in MATCHER.detect(sections, [])}


def test_skills_matched_as_whole_words_with_aliases():
    found = detect(["Languages: Python, JavaScript, C++", "Tools: sklearn, nodejs, k8s, MS Excel, Power-BI"])
    assert {"Python", "JavaScript", "C++", "Scikit-learn", "Node.js", "Kubernetes", "Excel", "Power BI"} <= set(found)
    assert "Java" not in found  # not matched inside "JavaScript"


def test_ambiguous_names_need_a_skills_list_context():
    assert {"C", "R", "Go"} <= set(detect(["Languages: C, R, Go"]))
    prose = detect(other={"projects": ["I use R and C every day, I like to Go home and excel in communication and teamwork"]})
    assert not ({"C", "R", "Go", "Excel", "Communication", "Teamwork"} & set(prose))
    assert "Excel" in detect(other={"experience": ["Created dashboards in MS Excel"]})  # unambiguous form


def test_unambiguous_skills_found_in_prose_with_their_section_as_evidence():
    found = detect(["Python"], {"projects": ["Built an API with FastAPI and MySQL"], "experience": ["Wrote Python scripts"]})
    assert found["Python"] == ["skills", "experience"]
    assert found["FastAPI"] == ["projects"] and found["MySQL"] == ["projects"]


def test_no_skills_in_text_without_skills():
    assert detect(other={"projects": ["Organised a college fest with a team of 20 volunteers"]}) == {}


# ---------- stage 6-7: analysis and suggestions ----------
def test_full_resume_analysis():
    r = analyse(FULL_RESUME)
    assert r.detected_name == "Asha Patil" and r.page_count == 1
    assert r.sections_missing == [] and r.contact == {"email": True, "phone": True, "linkedin": True, "github": True}
    assert r.education[0]["cgpa"] == 8.4 and len(r.education) == 2
    assert [p["title"] for p in r.projects] == ["Placement Predictor", "Student Portal", "Campus Bus Tracker"]
    assert "Scikit-learn" in r.projects[0]["skills"] and r.projects[2]["skills"] == []
    assert r.experience[0]["dates"] == "Jun 2025 - Aug 2025" and len(r.certifications) == 2
    names = {s.name for s in r.skills}
    assert {"Python", "SQL", "Pandas", "REST APIs", "Machine Learning", "Git"} <= names
    assert r.completeness_score >= 90 and sum(p["earned"] for p in r.score_breakdown) == r.completeness_score
    assert all(p["earned"] <= p["max"] for p in r.score_breakdown) and sum(p["max"] for p in r.score_breakdown) == 100
    assert set(r.keywords) & {"data", "analytics", "dashboards", "reporting", "trends"}


def test_full_resume_gets_few_suggestions_and_only_justified_ones():
    texts = " ".join(s.text for s in analyse(FULL_RESUME).suggestions)
    assert "technologies used in every project" in texts  # "Campus Bus Tracker" names no technology
    assert "phone" not in texts and "Skills section" not in texts and "very short" not in texts


def test_resume_with_missing_sections_is_explained():
    r = analyse(MISSING_SECTIONS_RESUME)
    assert r.sections == ["education"] and set(r.sections_missing) == {"skills", "projects", "experience", "certifications", "summary"}
    assert r.skills == [] and r.projects == [] and r.completeness_score < 40
    sev = {s.category: s.severity for s in r.suggestions if s.category == "Missing section"}
    texts = " ".join(s.text for s in r.suggestions)
    assert "Skills section" in texts and "Projects section" in texts and "phone number" in texts
    assert "CGPA or percentage" in texts and "very short" in texts
    assert [s.severity for s in r.suggestions] == sorted((s.severity for s in r.suggestions), key={"high": 0, "medium": 1, "low": 2}.get)
    assert sev


def test_suggestions_for_weak_bullets():
    lines = ["Test Person", "t@x.com 9876543210", "PROJECTS", "App One", "- Responsible for the app", "- Helped with the app",
             "- Involved in app work", "- Part of a team doing app things", "SKILLS", "Python, SQL"]
    texts = " ".join(s.text for s in analyse(lines).suggestions)
    assert "action verbs" in texts and "Quantify" in texts


# ---------- live comparisons ----------
def docs():
    return [
        JobDoc(1, "Data Analyst", "Aurora", "python sql data dashboards statistics", [(IDS["Python"], "Python", True, 3), (IDS["SQL"], "SQL", True, 3), (IDS["Power BI"], "Power BI", False, 1)]),
        JobDoc(2, "Site Engineer", "Terra", "construction site drawings autocad", [(IDS["AutoCAD"], "AutoCAD", True, 3)]),
        JobDoc(3, "Backend Dev", "Zenith", "python backend fastapi docker apis", [(IDS["Python"], "Python", True, 3), (IDS["Docker"], "Docker", True, 2), (IDS["FastAPI"], "FastAPI", True, 2)]),
    ]


def test_job_relevance_ranks_related_jobs_first_and_lists_gaps():
    rel = job_relevance("Python SQL data dashboards and statistics projects", {IDS["Python"], IDS["SQL"]}, docs())
    assert [r.title for r in rel][0] == "Data Analyst" and rel[-1].title == "Site Engineer"
    assert rel[0].relevance > rel[1].relevance > rel[2].relevance and 0 <= rel[2].relevance
    backend = next(r for r in rel if r.title == "Backend Dev")
    assert backend.matched_skills == ["Python"] and backend.missing_skills == ["Docker", "FastAPI"]
    assert job_relevance("anything", set(), []) == []


def test_potentially_missing_skills_counts_only_what_neither_resume_nor_profile_has():
    rel = job_relevance("Python data", {IDS["Python"]}, docs())
    potential = potentially_missing_skills(rel, {"python"})
    names = [p["name"] for p in potential]
    assert "SQL" in names and "Docker" in names and "Python" not in names
    assert potentially_missing_skills(rel, {"python", "sql", "docker", "fastapi", "autocad"}) == []


def test_profile_comparison():
    detected = MATCHER.detect({"skills": ["Python, SQL"]}, [])
    cmp = compare_with_profile(detected, {IDS["Python"], IDS["Docker"]}, {IDS["Python"]: "Python", IDS["Docker"]: "Docker"}, 8.4, 8.0)
    assert [s["name"] for s in cmp["skills_not_in_profile"]] == ["SQL"]
    assert cmp["skills_not_on_resume"] == ["Docker"] and cmp["cgpa_mismatch"] is True
    assert compare_with_profile(detected, set(), {}, None, 8.0)["cgpa_mismatch"] is False
