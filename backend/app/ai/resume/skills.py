"""Stage 5 - skill detection by dictionary matching.

The dictionary is the platform's own skills list (the same one used for profiles and jobs), plus
a small alias table ("js" -> JavaScript, "k8s" -> Kubernetes). Matching is on whole words, so
"Java" does not match inside "JavaScript".

Some skill names are also ordinary words or single letters ("C", "R", "Go", "Excel",
"Communication"). Those are only accepted when they appear as an item of the Skills section
(or of a technology line), never from running prose, to avoid false positives.
"""
import re
from dataclasses import dataclass

# alias (lower case) -> canonical skill name. Aliases pointing to a skill that is not in the
# platform's skill list are ignored.
ALIASES = {
    "js": "JavaScript", "node": "Node.js", "nodejs": "Node.js", "node js": "Node.js",
    "reactjs": "React", "react.js": "React", "react js": "React", "expressjs": "Express.js", "express": "Express.js",
    "postgres": "PostgreSQL", "postgresql": "PostgreSQL", "mongo": "MongoDB", "mongo db": "MongoDB",
    "k8s": "Kubernetes", "gcp": "Google Cloud", "google cloud platform": "Google Cloud", "azure": "Microsoft Azure",
    "amazon web services": "AWS", "ml": "Machine Learning", "nlp": "Natural Language Processing",
    "dl": "Deep Learning", "sklearn": "Scikit-learn", "scikit learn": "Scikit-learn",
    "dsa": "Data Structures and Algorithms", "data structures": "Data Structures and Algorithms",
    "oop": "Object-Oriented Programming", "oops": "Object-Oriented Programming",
    "object oriented programming": "Object-Oriented Programming", "powerbi": "Power BI", "power-bi": "Power BI",
    "ms excel": "Excel", "microsoft excel": "Excel", "advanced excel": "Excel",
    "rest api": "REST APIs", "restful": "REST APIs", "restful api": "REST APIs", "restful apis": "REST APIs",
    "rest": "REST APIs", "ci cd": "CI/CD", "cicd": "CI/CD", "spring": "Spring Boot", "springboot": "Spring Boot",
    "cpp": "C++", "c plus plus": "C++", "golang": "Go", "html5": "HTML", "css3": "CSS",
    "android": "Android Development", "android studio": "Android Development",
    "manual testing": "Software Testing", "unit testing": "Software Testing", "cybersecurity": "Cyber Security",
    "database management system": "DBMS", "database management systems": "DBMS", "computer network": "Computer Networks",
    "statistical analysis": "Statistics", "team work": "Teamwork", "communication skills": "Communication",
    "problem solving skills": "Problem Solving",
    "operating system": "Operating Systems", "data visualisation": "Data Visualization",
    "natural language processing": "Natural Language Processing", "unit tests": "Software Testing",
}

# Terms that are also ordinary words / single letters. They are only accepted as an *item* of the
# Skills section (or of a technology line), never from running prose. Unambiguous forms such as
# "ms excel", "communication skills" or "rest apis" are matched anywhere.
SECTION_ONLY = {"c", "r", "go", "excel", "communication", "teamwork", "problem solving", "express", "rest"}


@dataclass
class DetectedSkill:
    skill_id: int
    name: str
    category: str | None
    evidence: list[str]  # sections where it was found, e.g. ["skills", "projects"]


class SkillMatcher:
    def __init__(self, catalog: list[tuple[int, str, str | None]]):
        self.catalog = {name.lower(): (sid, name, cat) for sid, name, cat in catalog}
        self.terms: list[tuple[str, str, re.Pattern]] = []  # (term, canonical lower name, regex)
        for lower, (_sid, _name, _cat) in self.catalog.items():
            self._add_term(lower, lower)
        for alias, target in ALIASES.items():
            if target.lower() in self.catalog:
                self._add_term(alias, target.lower())

    def _add_term(self, term: str, canonical: str) -> None:
        # A space in the term matches spaces or hyphens ("power bi" / "power-bi"); a hyphen in the
        # term also matches a missing separator ("scikit-learn" / "scikitlearn"). A term written
        # with a space does NOT match the joined word, so "team work" never matches "teamwork".
        parts = re.split(r"([\s\-]+)", term)
        body = "".join(
            (r"[\s\-]+" if any(ch.isspace() for ch in p) else r"[\s\-]*") if i % 2 else re.escape(p)
            for i, p in enumerate(parts)
        )
        pattern = re.compile(rf"(?<![a-z0-9+#.]){body}(?![a-z0-9+#])", re.IGNORECASE)
        self.terms.append((term, canonical, pattern))

    # ---- matching helpers ----
    @staticmethod
    def _tokens(lines: list[str]) -> set[str]:
        """Items of a skills-style list: 'Languages: C, Python | R' -> {'C', 'Python', 'R', ...}"""
        tokens = set()
        for line in lines:
            line = re.sub(r"^[A-Za-z /&]{2,30}:\s*", "", line.lstrip("- "))  # drop a "Languages:" label
            for tok in re.split(r"[,;|/•()·]| - ", line):
                tok = tok.strip().rstrip(".")
                if tok:
                    tokens.add(tok)
        return tokens

    def _found_in(self, lines: list[str], is_skill_list: bool) -> set[str]:
        """Canonical (lower-case) skill names present in these lines."""
        text = "\n".join(lines)
        tokens = self._tokens(lines) if is_skill_list else set()
        token_lower = {re.sub(r"[\s\-]+", " ", t.lower()) for t in tokens}  # "Problem-solving" == "problem solving"
        found = set()
        for term, canonical, pattern in self.terms:
            if term not in SECTION_ONLY:
                if pattern.search(text):
                    found.add(canonical)
            elif is_skill_list:
                if len(term) <= 2:  # "C", "R", "Go": exact, case-sensitive list item
                    if self.catalog[canonical][1] in tokens:
                        found.add(canonical)
                elif term in token_lower:
                    found.add(canonical)
        return found

    def detect(self, sections: dict[str, list[str]], header: list[str]) -> list[DetectedSkill]:
        evidence: dict[str, list[str]] = {}
        groups = {**sections, "other": header}
        for name, lines in groups.items():
            if not lines:
                continue
            skill_list = name == "skills"
            for canonical in self._found_in(lines, is_skill_list=skill_list):
                evidence.setdefault(canonical, []).append(name)
        # Technology lines inside projects/experience ("Tech: C, Python") may also hold restricted items.
        for name in ("projects", "experience"):
            tech_lines = [ln for ln in sections.get(name, []) if re.search(r"\b(tech|technologies|stack|tools|built with|languages)\b", ln, re.IGNORECASE)]
            for canonical in self._found_in(tech_lines, is_skill_list=True):
                evidence.setdefault(canonical, [])
                if name not in evidence[canonical]:
                    evidence[canonical].append(name)

        out = []
        for canonical, where in evidence.items():
            sid, display, category = self.catalog[canonical]
            order = {"skills": 0, "projects": 1, "experience": 2}
            out.append(DetectedSkill(sid, display, category, sorted(where, key=lambda w: order.get(w, 9))))
        return sorted(out, key=lambda d: d.name.lower())
