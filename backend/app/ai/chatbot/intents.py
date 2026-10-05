"""Decides what a student's message is about, using plain, explainable keyword patterns.

Questions about the student's own PlaceGenie data ("am I eligible for...", "my applications", "my next
interview") are routed to deterministic data handlers, so those answers always come from the database and
never from a language model's guess. Everything else is a general question for the guide / LLM.

Patterns run on lower-case text with punctuation removed. Order matters: the first matching intent wins.
"""
import re
from dataclasses import dataclass

# ---- intent names ----
REALTIME = "realtime"  # asks for a hiring decision / schedule that PlaceGenie cannot know
ELIGIBILITY = "eligibility"
SKILL_GAP = "skill_gap"
RECOMMEND = "recommend"
APPLICATIONS = "applications"
INTERVIEWS = "interviews"
RESUME = "resume"
PROFILE = "profile"
GREETING = "greeting"
THANKS = "thanks"
HELP = "help"
GENERAL = "general"  # a placement question for the guide / LLM

_PERSONAL = re.compile(r"\b(i|my|me|mine|im|ive|i m|i ve)\b")
_PREP_WORDS = re.compile(r"\b(prepare|preparation|tips|crack|advice|dress|practice|practise)\b")


def normalize(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9+#.' ]", " ", text)
    text = re.sub(r"(?<![a-z0-9])\.|\.(?![a-z0-9])", " ", text)  # drop sentence dots, keep node.js
    text = text.replace("'", "")
    return " ".join(text.split())


_REALTIME_PATTERNS = [
    r"\bwill\b.{0,35}\b(select|selected|hire|hired|shortlist|shortlisted|take|recruit|recruited|offer|offered)\b.{0,12}\b(me|my)\b",
    r"\bwill i (get|be) (placed|selected|hired|shortlisted|an offer|a job|called)\b",
    r"\b(did|has|have|is|was)\b.{0,45}\b(select|selected|shortlist|shortlisted|reject|rejected|announce|announced|released|declared|hired)\b",
    r"\bam i (selected|shortlisted|placed|rejected|hired)\b",
    r"\bchances? of\b.{0,20}\b(selected|selection|placed|placement|hired|getting)\b|\bwhat are my chances\b",
    r"\b(result|results)\b.{0,30}\b(declared|announced|out|date)\b|\bwhen (will|do|does|are)\b.{0,40}\b(result|results|visit|come|campus|drive|drives|announce)\b",
    r"\bwhich companies\b.{0,25}\b(coming|visiting|visit|come)\b|\bcompanies (coming|visiting)\b|\bdrive dates?\b|\bvisiting dates?\b",
]
_ELIGIBILITY_WORDS = re.compile(r"\b(eligible|eligibility|qualify|qualified|qualifies)\b|\bcan i apply\b|\bam i allowed\b|\bdo i (meet|satisfy)\b|\bmeet the (requirements|criteria)\b")
_SKILL_GAP_PATTERNS = [
    r"\bskills? gap\b|\bgap in (my )?skills\b",
    r"\bmissing skills?\b|\bskills? (i|am)\b.{0,20}\b(missing|lack|lacking)\b",
    r"\bwhat am i missing\b|\bwhat do i (lack|miss)\b",
    r"\bskills?\b.{0,30}\b(do|should|must|will) i\b.{0,20}\b(need|learn|have|improve|add)\b",
    r"\bwhat (should|do) i (need to )?learn\b",
]
_RECOMMEND = re.compile(
    r"\brecommend(ed|ation|ations)?\b|\bsuitable (jobs?|roles?|openings?)\b|\bsuits? me\b|\bbest (jobs?|roles?|matches?) for me\b"
    r"|\bjobs? (that )?match(es)? (my|me)\b|\bwhich jobs? should i\b|\bwhat jobs? (can|should) i\b|\bjobs? for me\b|\bmatching jobs?\b"
)
_APPLICATIONS = re.compile(
    r"\bmy applications?\b|\bapplication status\b|\bstatus of my\b|\bwhere (have|did) i applied\b|\bjobs? (that )?i (have )?applied\b"
    r"|\bhave i applied\b|\bapplied (jobs?|to)\b|\bapplications? (i have|i made|i submitted)\b|\bhow many (jobs|applications)\b"
)
_INTERVIEWS = re.compile(
    r"\b(my|next|upcoming|scheduled)\b.{0,25}\binterviews?\b|\bwhen is my (next )?(interview|test|round)\b|\bdo i have (any |an )?(interviews?|tests?)\b"
    r"|\binterviews? (do i have|scheduled)\b|\bshow (me )?(my )?(upcoming )?interviews\b"
)
_RESUME_SUBJECT = re.compile(r"\b(my|the) (resume|cv)\b|\bresume (score|analysis|feedback|review)\b")
_RESUME_REVIEW = re.compile(
    r"\b(score|analysis|analy[sz]e|check|review|improve|improvement|improvements|rate|feedback|fix|wrong|missing|weak|better|evaluate)\b"
)
_PROFILE = re.compile(
    r"\bmy (profile|skills|cgpa|branch|details|projects|certifications|certificates)\b|\bprofile (complete|completeness|strength|score)\b"
    r"|\bcomplete my profile\b|\bwhat skills do i have\b"
)
_GREETING = re.compile(r"^(hi+|hello+|hey+|hola|namaste|good (morning|afternoon|evening|day)|greetings)\b")
_THANKS = re.compile(r"\b(thanks|thank you|thankyou|thx|ty|much appreciated)\b")
_HELP = re.compile(r"^(help|help me|menu|options|commands)$|\bwhat can you do\b|\bwhat do you do\b|\bhow can you help\b|\bwho are you\b|\bwhat are you\b")


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


@dataclass(frozen=True)
class JobRef:
    id: int
    title: str
    company: str


def detect_intent(message: str, jobs: list[JobRef] | None = None) -> str:
    text = normalize(message)
    if not text:
        return GENERAL
    personal = bool(_PERSONAL.search(text))
    job_mentioned = bool(jobs) and find_jobs(text, jobs).kind != "none"

    if _any(_REALTIME_PATTERNS, text):
        return REALTIME
    if _ELIGIBILITY_WORDS.search(text) and (personal or job_mentioned):
        return ELIGIBILITY
    if _any(_SKILL_GAP_PATTERNS, text) and (personal or job_mentioned or "skill gap" in text):
        return SKILL_GAP
    if _RECOMMEND.search(text):
        return RECOMMEND
    if _APPLICATIONS.search(text):
        return APPLICATIONS
    if _INTERVIEWS.search(text) and not _PREP_WORDS.search(text):
        return INTERVIEWS
    if _RESUME_SUBJECT.search(text) and _RESUME_REVIEW.search(text):
        return RESUME
    if _PROFILE.search(text):
        return PROFILE
    if _HELP.search(text) and len(text.split()) <= 6:
        return HELP
    if _THANKS.search(text) and len(text.split()) <= 6:
        return THANKS
    if _GREETING.search(text) and len(text.split()) <= 5:
        return GREETING
    return GENERAL


# =====================================================================
# Which job is the student talking about?
# =====================================================================
@dataclass(frozen=True)
class JobMatch:
    kind: str  # "none" | "one" | "many"
    jobs: tuple[JobRef, ...] = ()

    @property
    def job(self) -> JobRef | None:
        return self.jobs[0] if self.kind == "one" else None


def _phrase_in(phrase: str, text: str) -> bool:
    return bool(phrase) and re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def _split_title(title: str) -> tuple[str, str]:
    """'Backend Developer (Python)' -> ('backend developer', 'python')"""
    base = re.sub(r"\(.*?\)", " ", title)
    extra = " ".join(re.findall(r"\((.*?)\)", title))
    return normalize(base), normalize(extra)


# First words too generic to identify a company on their own.
_GENERIC_FIRST_WORDS = {"the", "global", "india", "indian", "national", "first", "new", "tech", "software", "systems", "solutions",
                        "digital", "data", "cloud", "core", "infra", "info", "smart", "bright", "blue", "green", "star"}


def _company_mentioned(company: str, text: str) -> bool:
    full = normalize(company)
    if _phrase_in(full, text):
        return True
    first = full.split(" ")[0] if full else ""
    return len(first) >= 4 and first not in _GENERIC_FIRST_WORDS and _phrase_in(first, text)


def find_jobs(text: str, jobs: list[JobRef]) -> JobMatch:
    """Jobs whose title (and/or company) appear in the message. Titles are matched without any
    bracketed part, which is then used to tell similar jobs apart."""
    text = normalize(text)
    by_title = []
    for j in jobs:
        base, extra = _split_title(j.title)
        if _phrase_in(base, text):
            by_title.append((j, extra))
    by_company = [j for j in jobs if _company_mentioned(j.company, text)]

    if by_title:
        candidates = [j for j, _ in by_title]
        bases = {j.id: _split_title(j.title)[0] for j in candidates}
        # Ignore a title that is only part of another matched title ("Scientist" inside "Data Scientist"),
        # but keep two different titles that were both named ("Data Scientist or ML Engineer").
        candidates = [j for j in candidates if not any(bases[j.id] != bases[o.id] and bases[j.id] in bases[o.id] for o in candidates)]
        if len(candidates) > 1:
            narrowed = [j for j in candidates if _phrase_in(_split_title(j.title)[1], text)]
            candidates = narrowed or candidates
        if len(candidates) > 1 and by_company:
            narrowed = [j for j in candidates if j in by_company]
            candidates = narrowed or candidates
        return JobMatch("one" if len(candidates) == 1 else "many", tuple(candidates))
    if by_company:
        return JobMatch("one" if len(by_company) == 1 else "many", tuple(by_company))
    return JobMatch("none")
