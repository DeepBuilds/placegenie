# PlaceGenie AI – Intelligent Placement Assistant

Web-based placement assistant for college students and placement coordinators.
It is a guidance tool; it does not replace recruitment decisions by companies or placement officers.

> **Current status:** Phase 1 (setup) and Phase 2 (database models) are done. Phases 1-8 are done: setup, database, authentication and role-based access, the student profile, companies/jobs, eligibility checking, job recommendations, and resume analysis.

## Tech stack
| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Axios, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic |
| Database | MySQL 8 (via PyMySQL) |
| AI/ML | scikit-learn (TF-IDF similarity), pdfplumber (PDF text); pandas/NumPy in later phases |

## Folder structure
```
placegenie/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, CORS, router registration
│   │   ├── core/              settings (config.py), later security
│   │   ├── database/          engine + session
│   │   ├── routers/           HTTP endpoints (health.py for now)
│   │   ├── models/ schemas/ services/ repositories/ ai/ utils/   (filled in later phases)
│   ├── tests/
│   ├── uploads/               resume uploads (git-ignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/ (api, components, context, hooks, layouts, pages, routes, utils)
│   ├── vite.config.js         dev proxy: /api -> backend
│   └── .env.example
├── database/setup.sql         creates the MySQL database + user
└── README.md
```

## Prerequisites
Python 3.11+, Node.js 18+, MySQL 8 running locally, Git.

## 1. Database setup
1. Edit the password in `database/setup.sql`, then run (as MySQL admin):
   ```bash
   mysql -u root -p < database/setup.sql
   ```
   (Or paste the statements into MySQL Workbench.)
2. Put the same password in `backend/.env` as `DB_PASSWORD`.

## 2. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env  -> then edit values
uvicorn app.main:app --reload --port 8000
```
- Health check: http://127.0.0.1:8000/api/v1/health
- Swagger docs: http://127.0.0.1:8000/docs

## 3. Frontend
```bash
cd frontend
npm install
copy .env.example .env          # macOS/Linux: cp
npm run dev
```
Open http://localhost:5173 — the home page shows backend and MySQL status.

## Environment variables
Backend (`backend/.env`, see `.env.example`): `DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME`, `JWT_SECRET_KEY` (used from Phase 3), `CORS_ORIGINS`, `LLM_PROVIDER/LLM_API_KEY` (optional, Phase 11).
Frontend (`frontend/.env`): `VITE_API_BASE_URL` (default `/api/v1`), `VITE_PROXY_TARGET` (default `http://127.0.0.1:8000`).
`.env` files are git-ignored; never commit secrets.

## How frontend and backend communicate
In development Vite proxies `/api/*` to the backend, so the browser talks to one origin. All calls go through `frontend/src/api/client.js`. CORS is also configured in the backend (`CORS_ORIGINS`) for direct calls or deployment.

## Authentication
- Students self-register at `/register`; everyone logs in at `/login` and is sent to `/student` or `/coordinator` by role.
- Passwords are hashed with bcrypt; sessions are JWT bearer tokens (`JWT_SECRET_KEY` in `backend/.env` is required; generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
- The token is kept in `localStorage`; logout discards it. Expired or invalid tokens send the user back to the login page.
- Public registration only creates students. Create a coordinator (hidden password prompt) with:
  ```bash
  cd backend && .venv\Scripts\python -m app.database.create_coordinator
  ```

## Student profile (Phase 4)
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

## Companies and jobs (Phase 5)
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

Companies or jobs that already have student applications cannot be deleted (409): close the job instead. Deleting a company deletes its jobs. The coordinator management screens are part of the later coordinator dashboard (Phase 13); until then use the Swagger UI at `/docs` as a coordinator.

## Eligibility checking (Phase 6)
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

## Job recommendations (Phase 7)
`GET /api/v1/recommendations` (student only; page `/student/recommendations`) ranks open, not-yet-expired jobs for the logged-in student with a transparent 0-100 score. Query: `role_id`, `location`, `eligible_only`, `sort` (`score_desc` default, `score_asc`, `deadline`, `title`), `limit` (default 10, max 50), `offset`. Each item has the job, `match_score`, `eligibility`, `matched_skills`, `missing_skills`, `missing_preferred_skills`, `reasons` (why recommended), `concerns` (what holds it back) and a per-factor `breakdown`; the page also returns eligibility `counts` and `profile_hints`. Nothing is stored: scores are computed from the current profile on every request.

**Algorithm** (`backend/app/ai/recommender.py`, explainable, no trained model):

    fit   = weighted average of the factors the student has data for        (0..1)
    score = fit x eligibility multiplier x 100

| Factor | Weight | How it is computed |
|---|---|---|
| Skill match | 45% | share of the job's skills the student holds (required = 1, preferred = 0.5, scaled by the job's own skill weights) |
| Academic fit | 20% | 0 if the CGPA rule is failed, else 0.7 + 0.3 x headroom above the minimum |
| Preferred role | 15% | 1 = a preferred role, 0.5 = same role family, 0 = other |
| Interest match | 10% | TF-IDF cosine similarity (scikit-learn): interests + projects + experience + certifications vs the job text |
| Resume relevance | 10% | same TF-IDF similarity using the resume text (used only once a resume exists, Phase 8) |

Factors with no data (no skills added, no CGPA, no preferred roles, ...) are left out and the remaining weights are rescaled to 100%; missing data is never scored as zero. Eligibility (Phase 6 engine) then multiplies the result: eligible x1.0, incomplete profile x0.9, not eligible x0.5, so "stretch" jobs stay visible but rank below jobs the student can apply to. TF-IDF similarity of 0.25 or more counts as a full match (raw cosine between short texts is small). The engine sits behind the `Recommender` interface (`default_recommender()`), so an ML ranker can replace or augment it without changing the API or UI.

## Resume analysis (Phase 8)
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

If you upgraded from Phase 7 with an existing database, the two empty tables `resume_analyses` and `resume_detected_skills` gained columns; drop them and restart the backend so they are recreated (there is no migration tool yet).

## Tests
```bash
cd backend && .venv\Scripts\python -m pytest     # 298 tests: health, auth/RBAC, models, profile, companies/jobs, eligibility, recommendations, resumes
cd frontend && npm test                            # 74 tests: auth, profile, jobs, job details, companies, eligibility, recommendations, resumes
cd frontend && npm run lint && npm run build
```

## Database tables (Phase 2)
23 tables, created automatically when the backend starts (`create_all`; no migrations yet):
`users, students, coordinators` (identity and profiles) - `branches, skills, job_roles` (lookups) -
`student_skills, certifications, projects, experiences, student_preferred_roles, student_preferred_companies` (profile) -
`companies, jobs, job_skills, job_allowed_branches, job_required_certifications` (jobs and eligibility rules) -
`resumes, resume_analyses, resume_detected_skills` - `applications, interview_stages` - `chat_messages`.
Eligibility results, recommendations and skill gaps are deliberately not stored; they are computed on request.
Model tests run on in-memory SQLite (`pytest`); the schema also compiles for MySQL.
