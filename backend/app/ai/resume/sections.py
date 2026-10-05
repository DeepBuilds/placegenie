"""Stage 3 - split the resume into sections.

A line is treated as a heading when, after removing punctuation, it is short and equals one
of the well-known heading phrases (EDUCATION, Technical Skills, Work Experience, ...).
Everything before the first heading is the "header" (name and contact details).
"""
import re
from dataclasses import dataclass, field

HEADINGS: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "professional summary", "career summary", "objective", "career objective", "profile", "about me", "about"),
    "education": ("education", "academic background", "academic qualifications", "academics", "qualifications", "educational qualifications", "academic profile"),
    "skills": ("skills", "technical skills", "key skills", "core skills", "core competencies", "technologies", "technical proficiency", "skills and tools", "tools and technologies", "technical expertise", "programming languages", "languages and tools", "tools"),
    "projects": ("projects", "academic projects", "personal projects", "key projects", "project work", "major projects", "technical projects", "project experience"),
    "experience": ("experience", "work experience", "professional experience", "internships", "internship experience", "employment history", "work history", "industrial training", "internship"),
    "certifications": ("certifications", "certificates", "certifications and courses", "courses", "licenses and certifications", "training and certifications", "courses and certifications", "licenses"),
    "achievements": ("achievements", "awards", "awards and achievements", "accomplishments", "extracurricular activities", "extracurricular", "positions of responsibility", "activities", "leadership", "hobbies", "interests", "languages"),
}
_LOOKUP = {phrase: key for key, phrases in HEADINGS.items() for phrase in phrases}

SECTION_LABELS = {
    "summary": "Summary / Objective",
    "education": "Education",
    "skills": "Skills",
    "projects": "Projects",
    "experience": "Experience / Internships",
    "certifications": "Certifications",
    "achievements": "Achievements / Activities",
}


@dataclass
class SplitResume:
    header: list[str]
    sections: dict[str, list[str]] = field(default_factory=dict)  # key -> content lines, in resume order

    @property
    def found(self) -> list[str]:
        return list(self.sections)


def heading_key(line: str) -> str | None:
    if not line or line.startswith("- ") or len(line) > 45:
        return None
    candidate = re.sub(r"[^a-z& ]", " ", line.lower()).replace("&", " and ")
    candidate = " ".join(candidate.split())
    if not candidate or len(candidate.split()) > 5:
        return None
    return _LOOKUP.get(candidate)


def split_sections(cleaned: str) -> SplitResume:
    header: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in cleaned.splitlines():
        key = heading_key(line.strip())
        if key:
            current = key
            sections.setdefault(key, [])  # a repeated heading continues the same section
            continue
        if not line.strip():
            continue
        (sections[current] if current else header).append(line.strip())
    return SplitResume(header=header, sections=sections)
