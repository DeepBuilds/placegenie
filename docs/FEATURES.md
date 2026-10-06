# PlaceGenie AI - features in detail

How each module works and the exact rules it applies. Endpoint lists here are summaries; the complete list is in [API.md](API.md).
Every rule below is covered by the automated tests ([TESTING.md](TESTING.md)).

## Authentication and roles
- Students self-register at `/register`; everyone logs in at `/login` and is sent to `/student` or `/coordinator` by role.
- Passwords are hashed with bcrypt; sessions are JWT bearer tokens signed with `JWT_SECRET_KEY` (32+ characters, required).
- The token is kept in `localStorage`; logout discards it. Expired or invalid tokens send the user back to the login page.
- Public registration only creates students. Coordinators are created on the server with `python -m app.database.create_coordinator` (hidden password prompt).
- The role is read from the database on every request, so a role change or a disabled account takes effect immediately.
- Pages check the role too (a student opening `/coordinator/...` is sent to `/student`), but the backend is what enforces it.

## Student profile
Students manage their profile at `/student/profile`: personal and academic details, skills (with level), certifications, projects, experience, interests and placement preferences, plus a completeness score. The profile row is created at registration; the first save fills it in. Lookup lists (branches, skills, job roles) are seeded automatically at backend startup.

| Endpoint (student only) | Purpose |
|---|---|
| `GET /students/me` | full profile + completeness |
| `PUT /students/me` | save personal/academic details |
| `PUT /students/me/skills` | replace skill list |
| `PUT /students/me/preferences` | preferred roles/companies |
| `POST /students/me/{certifications,projects,experiences}` | add item |
| `PUT` / `DELETE /students/me/{certifications,projects,experiences}/{id}` | edit / remove item |
| `GET /branches`, `/skills`, `/job-roles` | lookup lists (any logged-in user) |

## Companies and jobs
Students browse `/student/jobs` (search + filters + pagination), `/student/jobs/:id` (full requirements) and `/student/companies`. Students only ever see **open** jobs; coordinators can see and manage everything. Eligibility is stored on the job (min CGPA, max backlogs, experience, allowed branches, required certifications, skills with required/preferred weight); eligibility is checked by the engine below.

Load the fictional demo data (10 companies, 19 jobs, varied requirements) once:
```bash
cd backend && .venv\Scripts\python -m app.database.seed_demo
```
It is re-runnable and never overwrites edits. It is not run at startup, so companies a coordinator deletes stay deleted.

| Endpoint | Who | Purpose |
|---|---|---|
| `GET /companies`, `/companies/{id}`, `/companies/{id}/jobs` | any logged-in user | list/search companies, detail, a company's jobs |
| `GET /jobs`, `/jobs/{id}` | any logged-in user | search + filter (`q, company_id, job_type, role_id, skill_id, branch_id, location, max_min_cgpa, hide_expired, sort, limit, offset`) |
| `POST /companies`, `PUT/DELETE /companies/{id}` | coordinator | manage companies |
| `POST /jobs`, `PUT/DELETE /jobs/{id}` | coordinator | manage jobs (PUT replaces the job incl. skills/branches/certifications) |

Companies or jobs that already have student applications cannot be deleted (409): close the job instead. Deleting a company deletes its jobs.

## Eligibility checking
`POST /api/v1/jobs/{job_id}/eligibility` (student only) compares the logged-in student's profile with a job and returns `result` (`ELIGIBLE` / `NOT_ELIGIBLE` / `INCOMPLETE_PROFILE`), `eligible`, every criterion (required value, your value, message, `passed`/`failed`/`not_evaluated`), `reasons`, `failed_requirements`, `missing_skills`, `missing_preferred_skills`, `missing_certifications` and `incomplete_fields`. The button is on the job details page.

It is **purely rule-based** (`backend/app/ai/eligibility.py`: plain functions, no database, no ML), so every verdict can be explained:
1. CGPA at least the job's minimum (0 = no minimum)
2. Branch in the job's allowed list (empty list = all branches)
3. Backlogs at most the job's limit (empty = no limit)
4. **All required** skills held (preferred skills are reported but never block)
5. All required certifications held (case/spacing-insensitive)
6. Experience months at least the minimum (from your experience entries, overlaps counted once, ongoing roles counted to today)
7. Job open and deadline not passed

If the profile lacks data for a rule (e.g. no CGPA or branch), that rule is `not_evaluated` rather than silently passing; a genuine failure always makes the result `NOT_ELIGIBLE`. Results are computed from the current profile on every request and are not stored. They are guidance only: the company and placement officers decide.

## Job recommendations
`GET /api/v1/recommendations` (student only; page `/student/recommendations`) ranks open, not-yet-expired jobs for the logged-in student with a transparent 0-100 score. Query: `role_id`, `location`, `eligible_only`, `sort` (`score_desc` default, `score_asc`, `deadline`, `title`), `limit` (default 10, max 50), `offset`. Each item has the job, `match_score`, `eligibility`, `matched_skills`, `missing_skills`, `missing_preferred_skills`, `reasons` (why recommended), `concerns` (what holds it back) and a per-factor `breakdown`; the page also returns eligibility `counts` and `profile_hints`. Nothing is stored: scores are computed from the current profile on every request.

**Algorithm** (`backend/app/ai/recommender.py`, explainable, no trained model):

    fit   = weighted average of the factors the student has data for        (0..1)
    score = fit x eligibility multiplier x 100

| Factor | Weight | How it is computed |
|---|---|---|
| Skill match | 45% | share of the job's skills the student holds (each required skill counts 1, each preferred skill 0.5) |
| Academic fit | 20% | 0 if the CGPA rule is failed, else 0.7 + 0.3 x headroom above the minimum |
| Preferred role | 15% | 1 = a preferred role, 0.5 = same role family, 0 = other |
| Interest match | 10% | TF-IDF cosine similarity (scikit-learn): interests + projects + experience + certifications vs the job text |
| Resume relevance | 10% | same TF-IDF similarity using the resume text (used only once a resume exists) |

Factors with no data (no skills added, no CGPA, no preferred roles, ...) are left out and the remaining weights are rescaled to 100%; missing data is never scored as zero. Eligibility (the engine above) then multiplies the result: eligible x1.0, incomplete profile x0.9, not eligible x0.5, so "stretch" jobs stay visible but rank below jobs the student can apply to. TF-IDF similarity of 0.25 or more counts as a full match (raw cosine between short texts is small). The engine sits behind the `Recommender` interface (`default_recommender()`), so an ML ranker can replace or augment it without changing the API or UI.

## Resume analysis
Students upload a **text-based PDF** at `/student/resume` and see the analysis at `/student/resume/analysis`. Scanned images are rejected with a clear message (no OCR). One resume per student: a new upload replaces the old one (and deletes its file).

| Endpoint (student only) | Purpose |
|---|---|
| `POST /resumes` (multipart `file`) | upload, validate, analyse, store -> full analysis |
| `GET /resumes/me` | current resume metadata, or `null` |
| `GET /resumes/{id}/analysis` | analysis + live comparison with profile and open jobs |
| `POST /resumes/{id}/analyze` | re-run the analysis on the stored text |
| `POST /resumes/{id}/sync-skills` | add detected skills to the student's profile (marked `source=resume`) |
| `GET /resumes/{id}/file` / `DELETE /resumes/{id}` | download / delete your own file |

**Pipeline** (`backend/app/ai/resume/`, one small module per stage): `extract.py` (pdfplumber text) -> `clean.py` (unicode, bullets, spacing) -> `sections.py` (heading detection) -> `parse.py` (name, contact, education, projects, experience, certifications via patterns) -> `skills.py` (whole-word dictionary match against the platform skill list + aliases; ambiguous names like C/R/Go/Excel only count inside a Skills list) -> `analyze.py` (completeness score out of 100, keywords by TF-IDF, rule-based suggestions, job relevance, potentially missing skills, profile comparison).
It is heuristic keyword/pattern analysis, not human-level understanding; the UI says so. Unusual layouts (multi-column, tables, graphics) can be read imperfectly.

**Stored:** file metadata, the cleaned text, the analysis (sections, contact flags, extracted entries, keywords, suggestions) and detected skills with where each was found. **Computed on every request (never stored):** job relevance (50% TF-IDF similarity + 50% share of the job's skills the resume shows), potentially missing skills, profile comparison and the profile-based suggestions.

**Security:** extension, content type and the `%PDF-` signature must all agree; size limit `RESUME_MAX_MB` (default 5, also refused early from `Content-Length`); page limit `RESUME_MAX_PAGES` (default 10); the stored name is a server-generated uuid (the client filename is only displayed, sanitised); files live in `backend/uploads/` (git-ignored); every query is scoped to the logged-in student, so another student's resume is simply "not found" (404).

## Skill-gap analysis
`GET /api/v1/jobs/{job_id}/skill-gap` (student only) compares the student's skills with one job. Shown on every job's details page and on its own page, `/student/skill-gap` (pick any open job; also linked from each recommendation). Read-only and computed from the current profile on every request.

Response: `match_percentage`, `required_match_percentage`, counts, `matched_skills` (with the student's own level), `missing_skills` (each with `priority` and `reasons`), `priority` (the top 5 to work on, ranked), `summary`, `notes`, `open_jobs_compared`. A job with no skills returns `match_percentage: null` and nothing to compare; a student with no skills gets 0% plus a note to add skills.

**Rules** (`backend/app/ai/skill_gap.py`, pure functions, no ML):
- **Match %** is the same formula as the recommender's skill score: each required skill counts 1, each preferred skill 0.5, so the two screens always agree. The job's own 1-5 skill weights are not part of the percentage.
- **Priority of a missing skill:** *high* = a required skill that is **essential** (the job gives it weight 3 or more out of 5) or that is **frequently requested** (asked for by at least 30% of currently open jobs); *medium* = any other required skill, or a preferred skill that is frequently requested; *low* = any other preferred skill. Within a level, skills are ordered by the job's weight, then how many open jobs ask for them, then name.
- Every priority carries plain-language reasons ("Required for this job", "Essential: weight 3 out of 5", "Asked for in 6 of 18 open jobs (33%)"). There are no learning times, courses or outcome claims.

## Applications and interviews
Students apply from a job's page, follow their applications at `/student/applications` (details at `/student/applications/:id`) and keep a diary of interviews at `/student/interviews` (details at `/student/interviews/:id`).

**Rules**
- **One application per student per job** (unique in the database too). A second attempt returns 409. After *withdrawing*, applying again re-opens the same record.
- Applying needs an open job whose deadline has not passed. Nobody is blocked for being ineligible (the company and placement cell decide): the apply button first shows what the student does not meet and asks them to confirm. The application page shows the *current* eligibility, computed live.
- **Statuses:** `applied -> shortlisted -> online_assessment -> technical_interview -> hr_interview -> selected`, or `rejected`, or `withdrawn`.
- **Only coordinators set the official status** (so placement statistics cannot be edited by the students they describe). Students can withdraw their own application, except after `selected` or `rejected`.
- **Interviews** (online assessment, technical, HR, other) have a date/time, notes, and a result (pending / passed / not cleared). Students manage interviews on their own applications; coordinators can add or edit them on any. Times are stored exactly as entered (one college, one time zone). Upcoming = now or later; past = earlier; a past interview with no result is flagged "add the result".

| Endpoint | Who | Purpose |
|---|---|---|
| `POST /applications` `{job_id}` | student | apply (201; 409 duplicate / deadline; 404 unknown or closed job) |
| `GET /applications/me?status=&job_id=` | student | my applications + per-status counts |
| `POST /applications/{id}/withdraw` | student | withdraw |
| `GET /applications?status=&job_id=&company_id=&q=&limit=&offset=` | coordinator | all applications |
| `PATCH /applications/{id}/status` `{status}` | coordinator | set the official status |
| `GET /applications/{id}` | owner or coordinator | detail incl. interviews and live eligibility |
| `POST /applications/{id}/interviews` | owner or coordinator | add an interview |
| `GET /interviews/me?when=upcoming\|past\|unscheduled\|all` | student | my interview diary + counts |
| `GET /interviews?when=` | coordinator | everyone's interviews |
| `GET` / `PATCH` / `DELETE /interviews/{id}` | owner or coordinator | view / change (only the fields sent) / delete |

Another student's application or interview is always "not found" (404).

## Placement chatbot
Students chat with the assistant at `/student/chat`: several saved conversations, a "New chat" button, and delete-one / clear-all-history.

**How a message is answered** (`backend/app/services/chatbot_engine.py`; the routes only call a service):
1. **Hiring decisions and schedules** ("will Google select me?", "when are the results?") get an honest "I do not have real-time information", never a guess.
2. **Questions about the student's own data** (eligibility, skill gap, recommendations, applications, interviews, resume, profile) are answered **directly from the database** with the same engines as the rest of the app. A language model is never used for these, so the numbers cannot be invented.
3. **Greetings and help** get short fixed replies.
4. **General placement questions** (interview prep, resumes, aptitude, job roles...) go to an LLM *if one is configured*, given reference notes from the built-in guide; otherwise, or if the LLM fails, the **built-in placement guide** answers. The guide is about 30 curated topics matched with TF-IDF similarity (`backend/app/ai/chatbot/knowledge.py`), not hundreds of canned replies.

Every assistant message carries a label saying how it was produced (your PlaceGenie data / built-in guide / AI-written / AI unavailable / something I cannot know).

**Running without an AI (default).** `LLM_PROVIDER=none` (or an empty key) works fully: the guide and the data answers above. Nothing else is needed.

**Connecting an LLM.** Set in `backend/.env` (restart the backend):

| Variable | Meaning |
|---|---|
| `LLM_PROVIDER` | `none` (default), `anthropic`, or `openai` (OpenAI or any OpenAI-compatible server) |
| `LLM_API_KEY` | your key; never commit it (`.env` is git-ignored) |
| `LLM_MODEL`, `LLM_BASE_URL` | optional; defaults are `claude-haiku-4-5-20251001` and `gpt-4o-mini`, and each provider's public endpoint |
| `LLM_TIMEOUT_SECONDS`, `LLM_MAX_TOKENS` | optional limits (20 s, 600 tokens) |
| `LLM_SHARE_PROFILE` | `true` sends a short summary (branch, CGPA, skills, preferred roles, counts of applications) so answers can be personal; `false` sends only the question |

Providers live in `backend/app/ai/chatbot/providers/` behind a small `LLMProvider` interface (`generate(system, turns)`); adding another is one class plus one line in `factory.py`. A missing key, an unknown provider name, a timeout, a 4xx/5xx, a bad reply or any provider error never breaks the chat: the student gets the built-in guide's answer with a notice, and the details go only to the server log (never the key).

**Privacy.** The LLM never receives the student's name, email, phone number, resume text, interview notes or messages from other students. Chat history stores only the message text, who said it, how a reply was produced and a timestamp (no prompts, profile snapshots or IP addresses). Students can delete one conversation or all of them; deleting an account removes its chats.

**Limits.** Messages are at most 1000 characters (`CHAT_MAX_MESSAGE_CHARS`), 15 per minute per student (`CHAT_RATE_LIMIT_PER_MINUTE`, answered with 429 and a `Retry-After` header) and 200 per conversation (`CHAT_MAX_MESSAGES_PER_CONVERSATION`).

| Endpoint (students only) | Purpose |
|---|---|
| `GET /chat/info` | AI or built-in-guide mode, starter questions, disclaimer |
| `POST /chat/messages` `{message, conversation_id?}` | send a message; starts a conversation when none is given |
| `GET /chat/conversations`, `GET /chat/conversations/{id}` | list (most recent first) / open one with its messages |
| `DELETE /chat/conversations/{id}`, `DELETE /chat/conversations` | delete one / all |

Another student's conversation is always "not found" (404). The assistant is guidance only and says so on the page.

## Student dashboard
The student's home page (`/student`) is one summary of the whole journey. It re-implements nothing: `GET /api/v1/dashboard` (student only, read-only) composes the existing services, so its numbers always match the individual pages, and every figure is computed from the database on each request.

| Widget | Shows | Built from |
|---|---|---|
| Summary cards | profile %, eligible jobs, active applications, upcoming interviews | profile, recommendations, applications, interviews |
| Next step + progress | 6 milestones (profile >= 80%, resume, applied, shortlisted, interview recorded, offer) and the first thing left to do | all of the above |
| Recommended for you | best 5 matches with score, eligibility and "applied" | recommendations |
| Eligible opportunities | how many open jobs you qualify for, the best ones you have not applied to, and those closing within 7 days | eligibility |
| Applications / Interviews | per-status bars, recent applications, upcoming interviews, past ones missing a result, pass rate | applications and interviews |
| Resume | status, completeness, skills found, top suggestions | resume analysis |
| Skill gaps | skills missing from the jobs that actually fit you (score >= 30%, at least 3 jobs), and the "closest opportunity" that only lacks skills | recommendations and skill gap |
| Placement statistics | open jobs, companies hiring, closing this week, share you are eligible for, most requested skills (marked "you have it" / "missing"), interview pass rate | job data |

Each widget has its own loading skeleton, empty state ("what to do next") and error state. If one section fails on the server it comes back as `null` with a message in `errors`, and the rest of the page still loads (that widget offers "Try again"). Quick actions: Complete Profile, Upload Resume, Find Jobs, View Recommendations, Check Skill Gaps, Prepare for Interview (opens the assistant with that question already asked) and Open Chatbot; the one matching your next step is highlighted. The navigation bar collapses into a menu on small screens.

## Coordinator dashboard
Log in as a coordinator (`python -m app.database.create_coordinator`) to reach `/coordinator`. Coordinator pages and APIs are separate from the student ones: a student who opens a coordinator page is redirected to their own dashboard, and every coordinator API answers a student with **403** (and a visitor who is not logged in with **401**). Nothing is duplicated: companies, jobs and applications use the same endpoints as the rest of the app; the new `/coordinators/*` endpoints only add the views that did not exist (cohort statistics, student search, reports).

| Page | What the coordinator can do | API |
|---|---|---|
| Dashboard | totals (students, companies, jobs, applications), shortlisted / selected students, rejected applications, placement rate, application funnel, latest applications, "needs attention" (unreviewed applications, jobs closing in 7 days, jobs nobody applied to, interviews this week) | `GET /coordinators/dashboard` |
| Students | search (name, email, college), filter (branch, year, minimum CGPA, resume, profile >= 80%, placement stage), sort, page | `GET /coordinators/students` |
| Student profile | profile, resume, skill gaps, the same 6-step progress the student sees, applications (change status here), interviews | `GET /coordinators/students/{id}` |
| Companies | view, search, add, edit, delete | `GET/POST /companies`, `PUT/DELETE /companies/{id}` |
| Jobs | view, filter (company, status, search), add, edit (skills with importance and weight, allowed branches, certifications), delete | `GET/POST /jobs`, `PUT/DELETE /jobs/{id}` |
| Applications | filter by company, job, status or search; set the official status | `GET /applications`, `PATCH /applications/{id}/status` |
| Progress | how many students reached each milestone, where everyone is now, who needs attention | `GET /coordinators/progress` |
| Analytics | applications by company, placement by branch and by CGPA band, interview pass rate, skills asked by jobs against skills students have | `GET /coordinators/analytics` |
| Report | placement report with charts, plus CSV downloads: students, applications, placements, companies, jobs, skills | `GET /coordinators/reports`, `GET /coordinators/reports/{kind}.csv` |

How the numbers are defined (all computed from the database on each request; nothing is stored or estimated):
- **Placement rate** = students with at least one *selected* application / registered students. It is shown only when there are at least 5 students (otherwise the page says why it is hidden). Branch and CGPA-band rates use the same rule for their own group size.
- **Shortlisted students** = students with an application being considered (shortlisted, online assessment, technical or HR interview). **Placement stage** of a student: *placed* (any selected application), *in process*, *applied*, *rejected* (every application rejected) or *not applied* (none, or only withdrawn ones).
- The cohort **progress** counts the same six milestones each student sees on their own dashboard, so the two views always agree; a test adds up every student's own tracker and compares.
- Deleting a company or job that has applications is refused (409) with a message; close the job instead. A student's withdrawal cannot be overridden by a coordinator.
- CSV files add an apostrophe in front of any cell that starts with `= + - @` so a student's name cannot run as a spreadsheet formula, and are downloaded through the logged-in API client (a plain link would not carry the token).

Authorization tests (`tests/test_authorization_matrix.py`) list every API route once as public, any-user, coordinator-only or student-only, and check the real status codes for visitors, students and coordinators for each. A new route that is not classified fails the suite, so access rules cannot be forgotten.

## Reporting and analytics
Two reports, both counted from the database every time they are opened (nothing is stored or cached), and both built from services that already existed, so a report can never disagree with a page.

**Student report** (`/student/report`, `GET /reports/me`, student only): the student's own applications and status distribution, interviews (passed / not cleared / pending, pass rate), overall outcome (placed, in process, applied, rejected, not applied), the top recommended jobs, skill gaps and the six-step placement progress. Reuses the student dashboard sections plus the application and interview lists. Export: **Download CSV** (`GET /reports/me.csv`, one row per application) and **Print / save as PDF** (the browser's print dialog; the navigation is hidden when printing).

**Coordinator report** (`/coordinator/reports`, `GET /coordinators/report`, coordinator only):

| Section | Chart | Definition |
|---|---|---|
| Student placement statistics | stage bars; placed vs not placed per branch and per CGPA band | placed = a student with at least one *selected* application; the rate needs >= 5 students (otherwise the page says "needs 5+ students") |
| Application status distribution | bars (only statuses that occur) | every application record, withdrawn included |
| Company-wise applications | stacked bars: in process / selected / rejected / applied or withdrawn | one bar per company that has applications; the page says how many have none |
| Job-wise applications | table, busiest 15 shown | one row per job; awaiting + in process + selected + rejected + withdrawn = applications (tested) |
| Selected students | table | one row per selected application, newest first |
| Common skill gaps | bars: students lacking each skill | skills that **open jobs** ask for, with `students lacking = all students - students having it`; skills every student has are left out |
| Placement progress | bars | the same milestones each student sees, so the two always agree |
| Interview results | stacked bar and pass rate | pass rate = passed / (passed + not cleared); results still pending are not counted |

Export: CSV downloads for students, applications, placements, companies, jobs and skills, plus Print / save as PDF. Charts are plain HTML bars (no chart library), every bar prints its number, and a chart with nothing to show is replaced by a sentence saying why. Only comparisons that mean something are drawn: no pie charts of two numbers, no chart of one value.

Efficiency: the coordinator report loads the cohort once and groups it in memory; the student report loads the applications and interviews once and shares them with the dashboard sections. Tests count the SQL statements and fail if the number grows with the number of students or applications.
