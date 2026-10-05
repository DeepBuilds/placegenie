"""Stages 6-7 - resume analysis and suggestions.

`analyze_text` turns resume text into a stored analysis (sections, extracted entries, detected
skills, keywords, completeness score, improvement suggestions).

The functions below it combine the resume with live data (the student's profile and the current
job list) and are evaluated on request, so they never go stale:
  job_relevance, potentially_missing_skills, compare_with_profile, profile_suggestions.

Everything here is heuristic keyword/pattern analysis. It does not "understand" a resume the way
a person does, and the UI says so.
"""
import re
from dataclasses import dataclass, field

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from app.ai.recommender import PREFERRED_SKILL_FACTOR, TEXT_SIMILARITY_SATURATION
from app.ai.resume.clean import clean_text, is_bullet, strip_bullet, word_count
from app.ai.resume.parse import (
    find_resume_cgpa,
    parse_certifications,
    parse_contact,
    parse_education,
    parse_entries,
    parse_name,
    starts_with_action_verb,
)
from app.ai.resume.sections import SECTION_LABELS, split_sections
from app.ai.resume.skills import DetectedSkill, SkillMatcher
from app.ai.text_similarity import tfidf_similarities

CORE_SECTIONS = ["education", "skills", "projects"]
OPTIONAL_SECTIONS = ["experience", "certifications", "summary"]

_RESUME_STOPWORDS = {
    "experience", "project", "projects", "university", "college", "institute", "school", "student", "work",
    "working", "using", "used", "use", "team", "year", "years", "summary", "objective", "skills", "education",
    "certification", "certifications", "course", "courses", "present", "current", "also", "various", "based",
    "good", "strong", "knowledge", "basic", "email", "phone", "mobile", "linkedin", "github", "gmail", "com",
    "cgpa", "gpa", "percentage", "wrote", "weekly", "web", "new", "many", "different", "things", "tasks", "like", "likes", "engineering", "technology", "bachelor", "master", "degree", "tech", "intern",
    "internship", "developed", "built", "created", "designed", "implemented", "application", "applications",
    "system", "systems", "module", "features", "feature", "details", "responsible", "including", "include",
}
_STOP = set(ENGLISH_STOP_WORDS) | _RESUME_STOPWORDS


# ---------- result containers ----------
@dataclass
class Suggestion:
    severity: str  # "high" | "medium" | "low"
    category: str
    text: str

    def as_dict(self) -> dict:
        return {"severity": self.severity, "category": self.category, "text": self.text}


@dataclass
class ResumeAnalysisResult:
    cleaned_text: str
    detected_name: str | None
    word_count: int
    page_count: int
    sections: list[str]
    sections_missing: list[str]
    contact: dict[str, bool]
    education: list[dict]
    projects: list[dict]
    experience: list[dict]
    certifications: list[str]
    skills: list[DetectedSkill]
    keywords: list[str]
    completeness_score: int
    score_breakdown: list[dict] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)


# ---------- keywords ----------
_NOISE_RE = re.compile(r"\S+@\S+|(?:https?://|www\.)\S+|\b\S+\.(?:com|in|org|net)\S*|(?:linkedin|github)\.\S+", re.IGNORECASE)


def extract_keywords(resume_text: str, corpus: list[str], skip_terms: set[str], limit: int = 12) -> list[str]:
    """Top TF-IDF terms of the resume that also occur in the current job descriptions.

    Idf comes from the job texts, so words common to every job count little and distinctive words
    count more. Skills already detected, emails, links and names are not repeated here.
    """
    text = _NOISE_RE.sub(" ", resume_text)
    if not text.strip():
        return []
    try:
        vectorizer = TfidfVectorizer(
            stop_words=list(_STOP), sublinear_tf=True, lowercase=True,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#\-]{2,}\b",
        )
        matrix = vectorizer.fit_transform([*corpus, text])
    except ValueError:
        return []
    row = matrix[len(corpus)].toarray()[0]
    terms = vectorizer.get_feature_names_out()
    in_jobs = matrix[: len(corpus)].getnnz(axis=0) > 0 if corpus else None  # term appears in some job text
    ranked = sorted(((w, t, ok) for w, t, ok in zip(row, terms, in_jobs if in_jobs is not None else [True] * len(terms)) if w > 0 and ok), reverse=True)
    out = []
    for _, term, _ in ranked:
        term = term.strip("-")
        if term.lower() in skip_terms or len(term) < 3 or term in out:
            continue
        out.append(term)
        if len(out) == limit:
            break
    return out


# ---------- completeness ----------
def _score(parts: list[tuple[str, int, int, str]]) -> tuple[int, list[dict]]:
    breakdown = [{"label": label, "earned": earned, "max": maximum, "note": note} for label, earned, maximum, note in parts]
    return sum(p[1] for p in parts), breakdown


def completeness(contact, name, sections, education, projects, experience, certifications, n_skills, words) -> tuple[int, list[dict]]:
    has = lambda key: key in sections
    parts = [
        ("Contact details", (8 if contact["email"] else 0) + (6 if contact["phone"] else 0) + (6 if contact["linkedin"] or contact["github"] else 0), 20,
         "email 8, phone 6, LinkedIn or GitHub 6"),
        ("Name at the top", 5 if name else 0, 5, "a name was found near the top"),
        ("Education", 15 if education else (8 if has("education") else 0), 15, "section with at least one recognised degree"),
        ("Skills", (8 if has("skills") else 0) + (12 if n_skills >= 8 else 8 if n_skills >= 4 else 4 if n_skills >= 1 else 0), 20,
         "skills section 8, plus up to 12 for 8+ recognised skills"),
        ("Projects", 15 if projects else (7 if has("projects") else 0), 15, "section with at least one project"),
        ("Experience / internships", 10 if experience else (4 if has("experience") else 0), 10, "optional for freshers"),
        ("Certifications", 5 if certifications else 0, 5, "optional"),
        ("Summary / objective", 5 if has("summary") else 0, 5, "optional"),
        ("Reasonable length", 5 if 200 <= words <= 900 else 2 if 120 <= words < 200 or 900 < words <= 1200 else 0, 5, "about 200-900 words"),
    ]
    return _score(parts)


# ---------- suggestions ----------
def build_suggestions(r: ResumeAnalysisResult, sections: dict[str, list[str]]) -> list[Suggestion]:
    s: list[Suggestion] = []
    add = lambda sev, cat, text: s.append(Suggestion(sev, cat, text))

    if not r.contact["email"]:
        add("high", "Contact", "Add a professional email address near the top so recruiters can reach you.")
    if not r.contact["phone"]:
        add("high", "Contact", "Add a phone number near the top.")
    if not (r.contact["linkedin"] or r.contact["github"]):
        add("low", "Contact", "Add your LinkedIn or GitHub link; recruiters like to see your profile and code.")
    if not r.detected_name:
        add("medium", "Header", "Put your full name as the first line so it is easy to find (it could not be detected).")

    labels = {"education": "high", "skills": "high", "projects": "medium", "experience": "low", "certifications": "low", "summary": "low"}
    advice = {
        "education": "Add an Education section with your degree, college, years and CGPA.",
        "skills": "Add a Skills section listing your technical skills; most recruiters scan for it first.",
        "projects": "Add a Projects section: 2-3 projects with the technologies you used and what you achieved.",
        "experience": "If you have internships or training, add an Experience section. If not, projects and certifications can fill this gap.",
        "certifications": "List any certifications or online courses you have completed.",
        "summary": "Consider a 2-3 line summary or career objective stating the role you are targeting.",
    }
    for key in [*CORE_SECTIONS, *OPTIONAL_SECTIONS]:
        if key in r.sections_missing:
            add(labels[key], "Missing section", advice[key])

    n = len(r.skills)
    if "skills" in r.sections and n < 5:
        add("medium", "Skills", f"Only {n} recognised skill(s). Add the tools, languages and technologies you actually know (at least 5-8 is typical).")
    if r.education and all(e["cgpa"] is None and e["percentage"] is None for e in r.education):
        add("medium", "Education", "Add your CGPA or percentage; many companies filter on it.")

    if r.projects:
        with_skills = sum(1 for p in r.projects if re.search(r"\b(tech|stack|built with|using|used)\b", p["description"] + p["title"], re.IGNORECASE) or p.get("skills"))
        if with_skills < len(r.projects):
            add("medium", "Projects", "Mention the technologies used in every project (for example: 'Tech: React, FastAPI, MySQL').")

    bullets = [strip_bullet(b) for part in (sections.get("projects", []), sections.get("experience", [])) for b in part if is_bullet(b)]
    if len(bullets) >= 3:
        verbs = sum(starts_with_action_verb(b) for b in bullets)
        if verbs / len(bullets) < 0.4:
            add("medium", "Writing", "Start bullet points with action verbs such as Built, Designed, Implemented or Improved.")
        numeric = sum(bool(re.search(r"\d", b)) for b in bullets)
        if numeric / len(bullets) < 0.2:
            add("medium", "Writing", "Quantify results where you can (users, speed-ups, accuracy, team size), for example 'reduced load time by 30%'.")

    if r.word_count < 150:
        add("high", "Length", "The resume is very short. Add more detail about your education, skills and projects.")
    elif r.word_count < 250:
        add("low", "Length", "The resume is quite short; consider describing your projects in a little more detail.")
    if r.word_count > 900 or r.page_count > 2:
        add("medium", "Length", "Aim for one page (two at most) for a fresher resume; keep only the most relevant content.")

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(s, key=lambda x: order[x.severity])


# ---------- the main entry point ----------
def analyze_text(raw_text: str, page_count: int, matcher: SkillMatcher, keyword_corpus: list[str]) -> ResumeAnalysisResult:
    cleaned = clean_text(raw_text)
    split = split_sections(cleaned)
    all_lines = [ln for ln in cleaned.splitlines() if ln.strip()]

    contact = parse_contact(cleaned)
    name = parse_name(split.header, all_lines)
    education = parse_education(split.sections.get("education", []))
    projects = parse_entries(split.sections.get("projects", []))
    experience = parse_entries(split.sections.get("experience", []))
    certifications = parse_certifications(split.sections.get("certifications", []))
    skills = matcher.detect(split.sections, split.header)

    for project in projects:  # which known skills each project mentions
        found = matcher.detect({"projects": [project["title"], project["description"]]}, [])
        project["skills"] = [d.name for d in found]

    found = split.found
    missing = [k for k in [*CORE_SECTIONS, *OPTIONAL_SECTIONS] if k not in found]
    words = word_count(cleaned)
    score, breakdown = completeness(contact, name, found, education, projects, experience, certifications, len(skills), words)

    skip = {w.lower() for d in skills for w in re.split(r"[\s/]+", d.name)} | {d.name.lower() for d in skills}
    keywords = extract_keywords(cleaned, keyword_corpus, skip)

    result = ResumeAnalysisResult(
        cleaned_text=cleaned, detected_name=name, word_count=words, page_count=page_count, sections=found,
        sections_missing=missing, contact=contact, education=education, projects=projects, experience=experience,
        certifications=certifications, skills=skills, keywords=keywords, completeness_score=score, score_breakdown=breakdown,
    )
    result.suggestions = build_suggestions(result, split.sections)
    return result


# =====================================================================
# Live comparisons (profile and jobs). Computed on request, never stored.
# =====================================================================
@dataclass
class JobDoc:
    job_id: int
    title: str
    company: str
    text: str
    skills: list[tuple[int, str, bool, int]]  # (skill_id, name, required, weight)


@dataclass
class JobRelevance:
    job_id: int
    title: str
    company: str
    relevance: int  # 0..100
    matched_skills: list[str]
    missing_skills: list[str]  # required skills the resume does not show


def job_relevance(resume_text: str, resume_skill_ids: set[int], jobs: list[JobDoc], limit: int = 5) -> list[JobRelevance]:
    """relevance = 50% text similarity (TF-IDF cosine) + 50% share of the job's skills found in the resume."""
    if not jobs:
        return []
    sims = tfidf_similarities([resume_text], [j.text for j in jobs])[0]
    scored = []
    for job, sim in zip(jobs, sims):
        text_part = min(1.0, sim / TEXT_SIMILARITY_SATURATION)
        got = total = 0.0
        matched, missing = [], []
        for sid, name, required, weight in job.skills:
            w = weight * (1.0 if required else PREFERRED_SKILL_FACTOR)
            total += w
            if sid in resume_skill_ids:
                got += w
                matched.append(name)
            elif required:
                missing.append(name)
        skill_part = got / total if total else None
        relevance = text_part if skill_part is None else 0.5 * text_part + 0.5 * skill_part
        scored.append(JobRelevance(job.job_id, job.title, job.company, round(relevance * 100), sorted(matched, key=str.lower), sorted(missing, key=str.lower)))
    scored.sort(key=lambda j: (-j.relevance, j.title))
    return scored[:limit]


def potentially_missing_skills(relevant: list[JobRelevance], have_skill_names: set[str], limit: int = 8) -> list[dict]:
    """Required skills of the jobs this resume is closest to that neither resume nor profile shows."""
    counts: dict[str, list[str]] = {}
    for job in relevant:
        if job.relevance <= 0:
            continue
        for name in job.missing_skills:
            if name.lower() not in have_skill_names:
                counts.setdefault(name, []).append(job.title)
    ranked = sorted(counts.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))
    return [{"name": n, "jobs_requiring": len(t), "example_jobs": t[:2]} for n, t in ranked[:limit]]


def compare_with_profile(resume_skills: list[DetectedSkill], profile_skill_ids: set[int], profile_skill_names: dict[int, str],
                         resume_cgpa: float | None, profile_cgpa: float | None) -> dict:
    resume_ids = {d.skill_id for d in resume_skills}
    return {
        "skills_not_in_profile": [{"skill_id": d.skill_id, "name": d.name} for d in resume_skills if d.skill_id not in profile_skill_ids],
        "skills_not_on_resume": sorted((profile_skill_names[i] for i in profile_skill_ids - resume_ids), key=str.lower),
        "resume_cgpa": resume_cgpa,
        "profile_cgpa": profile_cgpa,
        "cgpa_mismatch": resume_cgpa is not None and profile_cgpa is not None and abs(resume_cgpa - profile_cgpa) > 0.05,
    }


def profile_suggestions(comparison: dict, potential: list[dict], profile_missing: list[str]) -> list[Suggestion]:
    s: list[Suggestion] = []
    if comparison["skills_not_in_profile"]:
        names = ", ".join(x["name"] for x in comparison["skills_not_in_profile"][:8])
        s.append(Suggestion("medium", "Profile", f"Your resume shows skills missing from your profile ({names}). Add them so eligibility and recommendations use them."))
    if comparison["skills_not_on_resume"]:
        names = ", ".join(comparison["skills_not_on_resume"][:8])
        s.append(Suggestion("medium", "Resume", f"Your profile lists skills your resume does not mention ({names}). Add them to your resume if you can back them up."))
    if comparison["cgpa_mismatch"]:
        s.append(Suggestion("high", "Consistency", f"CGPA differs: resume {comparison['resume_cgpa']:.2f} vs profile {comparison['profile_cgpa']:.2f}. Make them match."))
    if potential:
        names = ", ".join(p["name"] for p in potential[:5])
        s.append(Suggestion("low", "Skill gap", f"Jobs closest to your resume often require: {names}. If you already have these skills, add them; otherwise they are worth learning."))
    if profile_missing:
        s.append(Suggestion("low", "Profile", "Your profile is missing: " + ", ".join(profile_missing) + "."))
    return s
