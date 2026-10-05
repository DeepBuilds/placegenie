"""Stage 4 - information extraction.

Pattern-based (regular expressions and simple layout rules), not "understanding". Each function
returns an empty/None result rather than guessing when the resume does not follow the usual layout.
"""
import re

from app.ai.resume.clean import is_bullet, strip_bullet

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\d.])(?:\+\d{1,3}[\s-]?)?\(?\d{3,5}\)?[\s-]?\d{3,5}[\s-]?\d{2,5}(?![\d.])")
LINKEDIN_RE = re.compile(r"linkedin\.com/(?:in|pub)/", re.IGNORECASE)
GITHUB_RE = re.compile(r"github\.com/", re.IGNORECASE)

_NOT_A_NAME = {"resume", "curriculum", "vitae", "cv", "profile", "email", "phone", "mobile", "contact",
               "address", "objective", "summary", "linkedin", "github", "portfolio"}

MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_PART = rf"(?:{MONTH}\s*)?(?:19|20)\d{{2}}"
DATE_RANGE_RE = re.compile(rf"({DATE_PART})\s*(?:-|to)\s*({DATE_PART}|present|current|now|ongoing)", re.IGNORECASE)

_DEGREE_CI = re.compile(
    r"\b(b\.?\s?tech|m\.?\s?tech|bachelor(?:s)?|master(?:s)?|mba|bca|mca|b\.?\s?sc|m\.?\s?sc|diploma|ph\.?\s?d|"
    r"hsc|ssc|higher secondary|secondary school|12th|10th|xii|intermediate)\b", re.IGNORECASE)
_DEGREE_CS = re.compile(r"\b(B\.?\s?E\.?|M\.?\s?E\.?)(?=[\s,(:-]|$)")  # upper-case only: "be" is a common word
_INSTITUTION_RE = re.compile(r"\b(university|college|institute|school|academy|polytechnic|vidyalaya|iit|nit)\b", re.IGNORECASE)
_CGPA_RE = re.compile(r"(?:cgpa|gpa|cpi|sgpa)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,2})?)\s*(?:/\s*(10|4)(?:\.0+)?)?", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(\d{2}(?:\.\d{1,2})?)\s*%")
_YEARS_RE = re.compile(r"((?:19|20)\d{2})(?:\s*(?:-|to)\s*((?:19|20)\d{2}|present|current))?", re.IGNORECASE)


# ---------- contact & name ----------
def parse_contact(text: str) -> dict[str, bool]:
    digits_ok = any(10 <= len(re.sub(r"\D", "", m.group())) <= 13 for m in PHONE_RE.finditer(text))
    return {
        "email": bool(EMAIL_RE.search(text)),
        "phone": digits_ok,
        "linkedin": bool(LINKEDIN_RE.search(text)),
        "github": bool(GITHUB_RE.search(text)),
    }


def parse_name(header: list[str], all_lines: list[str]) -> str | None:
    """The first short, letters-only line near the top that is not a label or contact detail."""
    candidates = (header or all_lines)[:6]
    for line in candidates:
        if "@" in line or "http" in line.lower() or re.search(r"\d", line):
            continue
        words = line.replace(",", " ").split()
        if not 2 <= len(words) <= 4 or len(line) > 40:
            continue
        if any(w.lower().strip(".:") in _NOT_A_NAME for w in words):
            continue
        if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", w) for w in words):
            continue
        return line.title() if line.isupper() else line
    return None


# ---------- education ----------
def parse_education(lines: list[str]) -> list[dict]:
    entries = []
    degree_idx = [i for i, ln in enumerate(lines) if _DEGREE_CI.search(ln) or _DEGREE_CS.search(ln)]
    for n, i in enumerate(degree_idx):
        end = degree_idx[n + 1] if n + 1 < len(degree_idx) else len(lines)
        window = lines[i:min(end, i + 4)]
        above = lines[i - 1] if i > 0 and (n == 0 or i - 1 > degree_idx[n - 1]) else ""
        if above and _INSTITUTION_RE.search(above) and not _YEARS_RE.search(above):
            window = [above, *window]  # an institution line above the degree belongs to this entry
        block = " ".join(strip_bullet(w) for w in window)

        degree_match = _DEGREE_CI.search(lines[i]) or _DEGREE_CS.search(lines[i])
        institution = next((strip_bullet(w) for w in window if _INSTITUTION_RE.search(w)), None)
        years = _YEARS_RE.search(block)
        cgpa = _CGPA_RE.search(block)
        percent = _PERCENT_RE.search(block)
        entries.append({
            "degree": degree_match.group(0).strip() if degree_match else strip_bullet(lines[i]),
            "institution": institution,
            "years": years.group(0) if years else None,
            "cgpa": float(cgpa.group(1)) if cgpa and float(cgpa.group(1)) <= 10 else None,
            "percentage": float(percent.group(1)) if percent and float(percent.group(1)) <= 100 else None,
            "text": strip_bullet(lines[i]),
        })
    return entries


# ---------- projects & experience ----------
_VERBS = {
    "built", "developed", "designed", "created", "implemented", "led", "managed", "analysed", "analyzed",
    "optimized", "optimised", "improved", "reduced", "increased", "automated", "deployed", "integrated",
    "tested", "maintained", "collaborated", "researched", "wrote", "engineered", "architected", "launched",
    "delivered", "trained", "evaluated", "configured", "established", "organized", "organised", "coordinated",
    "presented", "migrated", "refactored", "debugged", "documented", "assisted", "contributed", "performed",
    "achieved", "conducted", "executed", "supported", "utilized", "utilised", "applied", "worked", "completed",
}


def starts_with_action_verb(text: str) -> bool:
    first = re.match(r"[A-Za-z]+", text)
    return bool(first) and first.group(0).lower() in _VERBS


def _title_like(text: str) -> bool:
    return len(text) <= 90 and text[:1].isupper() and not text.endswith((".", ","))


def parse_entries(lines: list[str]) -> list[dict]:
    """Group a section's lines into entries: a short title line followed by detail lines.

    Layout rules (heuristics - unusual layouts may be split imperfectly):
      * a short, capitalised line that does not end with "." starts a NEW entry when it comes
        first, or right after a bullet, or after a sentence that ended with "."
      * the line(s) right after a title, and any bullet, are that entry's details
      * a line that does not look like a title continues the previous line (PDF line wrapping)
    """
    entries: list[dict] = []
    last = None  # kind of the previous line: "title", "bullet" or "text"

    def new_entry(title: str) -> None:
        entries.append({"title": title, "details": [], "bullets": []})

    for line in lines:
        text = strip_bullet(line)
        if not text:
            continue
        if is_bullet(line):
            if not entries:
                new_entry(text[:90])
            else:
                entries[-1]["details"].append(text)
                entries[-1]["bullets"].append(text)
            last = "bullet"
            continue

        title_like = _title_like(text)
        starts_new = not entries or (title_like and (last == "bullet" or (last == "text" and entries[-1]["details"][-1].endswith("."))))
        if starts_new:
            new_entry(text)
            last = "title"
        elif last == "title":
            entries[-1]["details"].append(text)
            last = "text"
        else:  # wrapped continuation of the previous bullet / sentence
            if entries[-1]["details"]:
                entries[-1]["details"][-1] += " " + text
                if entries[-1]["bullets"] and last == "bullet":
                    entries[-1]["bullets"][-1] += " " + text
            else:
                entries[-1]["details"].append(text)
            last = last if last == "bullet" else "text"

    results = []
    for e in entries:
        dates = DATE_RANGE_RE.search(" ".join([e["title"], *e["details"][:1]]))
        results.append({
            "title": e["title"],
            "dates": dates.group(0) if dates else None,
            "description": " ".join(e["details"]).strip(),
            "bullets": e["bullets"],
        })
    return results


def parse_certifications(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        text = strip_bullet(line)
        if 4 <= len(text) <= 150 and text not in out:
            out.append(text)
    return out[:15]


def find_resume_cgpa(education: list[dict]) -> float | None:
    return next((e["cgpa"] for e in education if e.get("cgpa") is not None), None)
