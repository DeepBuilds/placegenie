# PlaceGenie AI – Intelligent Placement Assistant

A web application that helps college students prepare for campus placements and helps the placement cell
(coordinators) run them. Semester III project: React + FastAPI + MySQL, with explainable rule-based "AI".

> PlaceGenie AI gives **guidance**. It never decides who gets hired: companies and placement officers do.

## Contents
[Objective](#project-objective) · [Features](#features) · [Technology](#technology-stack) · [Architecture](#architecture) ·
[Folders](#folder-structure) · [Requirements](#requirements) · [Installation](#installation) · [Demo accounts](#demo-accounts) ·
[How to demonstrate](#how-to-demonstrate-placegenie-ai) · [Testing](#testing) · [API](#api-documentation) ·
[Screenshots](#screenshots) · [More documentation](#more-documentation)

## Project objective
Students usually do not know which openings they are eligible for, why they are rejected by a filter, which skills
they lack, or how far along they are; coordinators track all of this in spreadsheets. PlaceGenie AI puts both sides on
one platform and explains every result:

- a student sees exactly which jobs they qualify for and **why** (rule by rule), which jobs suit them best, what to
  learn next, what their resume is missing, and where every application stands;
- a coordinator manages companies, jobs and applications, and sees live placement statistics and reports.

All "intelligent" features are transparent rules with written weights, plus TF-IDF text similarity. There is no
trained black-box model, so every number on screen can be explained.

## Features

**Student**
- Registration and login; profile with academics, skills (with level), projects, experience, certifications and
  preferences, plus a completeness score
- Job and company browsing with search, filters and pagination
- **Eligibility check** per job: CGPA, branch, backlogs, required skills, certifications, experience and deadline,
  each with a pass/fail reason
- **Recommendations**: jobs ranked by a 0-100 score (skills 45%, academics 20%, preferred role 15%, interests 10%,
  resume 10%), with reasons and concerns
- **Resume analysis** of a text PDF: sections, skills, completeness score, suggestions, job relevance; detected skills
  can be added to the profile
- **Skill gap** for any job: match %, missing skills ranked high/medium/low with reasons
- **Applications and interviews**: apply, withdraw, follow the official status, keep an interview diary
- **Placement assistant (chatbot)**: answers about the student's own data straight from the database; general
  questions from a built-in guide, or from an LLM if one is configured
- **Dashboard** and a printable **report** (CSV export)

**Coordinator**
- Dashboard: students, companies, jobs, applications, shortlisted/selected/rejected, placement rate, items needing attention
- Student search and filters; each student's full placement profile
- Companies and jobs: add, edit, delete (protected when applications exist); skills with weights, allowed branches, certifications
- Applications: filter by company, job or status; set the official status
- Cohort progress, analytics, and a placement report with charts; CSV exports (students, applications, placements, companies, jobs, skills)

Full rules for every module: [docs/FEATURES.md](docs/FEATURES.md).

## Technology stack
| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, React Router 7, Axios, Tailwind CSS 4 |
| Backend | Python 3.11+ (tested on 3.13), FastAPI, Pydantic 2, SQLAlchemy 2, Uvicorn |
| Database | MySQL 8 (PyMySQL driver) |
| AI / text | scikit-learn (TF-IDF similarity), pdfplumber (PDF text); optional Anthropic or OpenAI-compatible LLM for the chatbot |
| Security | bcrypt password hashing, JWT bearer tokens, role-based access |
| Testing | pytest (1,040 tests), Vitest + Testing Library (233 tests), oxlint |

## Architecture
```
React SPA  --HTTPS/JSON + JWT-->  FastAPI  /api/v1
                                     routers -> services -> repositories -> MySQL 8
                                                   \-> ai/ (eligibility, recommender, skill gap,
                                                            resume pipeline, chatbot intents)
                                     uploads/ (resume PDFs)      optional LLM API (chatbot only)
```
Routers only handle HTTP and roles, services hold the use cases, `ai/` holds pure decision rules, repositories hold
the SQL. Judgements (eligibility, scores, dashboards, reports) are computed from the current data on every request and
never stored. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Folder structure
```
placegenie/
├── backend/
│   ├── app/
│   │   ├── main.py          app, CORS, security headers, error handlers, routers
│   │   ├── core/            settings (config.py), password/JWT (security.py), role checks (deps.py)
│   │   ├── routers/         HTTP endpoints, one file per area
│   │   ├── services/        use cases (applications, dashboards, reports, chatbot...)
│   │   ├── ai/              rules: eligibility, recommender, skill_gap, resume/, chatbot/
│   │   ├── repositories/    database queries
│   │   ├── models/          SQLAlchemy tables
│   │   ├── schemas/         request/response models (Pydantic)
│   │   └── database/        engine, seed scripts, create_coordinator
│   ├── tests/               pytest suite
│   ├── uploads/             resume files (git-ignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/             one module per backend area (client.js adds the token)
│   │   ├── pages/student/   pages/coordinator/
│   │   ├── components/      navbar, widgets, charts, forms
│   │   ├── context/ hooks/ routes/ utils/
│   │   └── tests/           Vitest suite
│   ├── vite.config.js       dev proxy /api -> backend
│   └── .env.example
├── database/setup.sql       creates the MySQL database and user
├── docs/                    detailed documentation, demo resume, screenshots
├── DEVELOPMENT.md           how to work on the code
└── README.md
```

## Requirements
- **Python** 3.11 or newer
- **Node.js** 20.19+ or 22.12+ (required by Vite 8) with npm
- **MySQL** 8.0 server and an admin login (for example `root`); MySQL Workbench is optional
- **Git**

## Installation

Commands are for Windows (Command Prompt or PowerShell); macOS/Linux equivalents are noted.

### 1. Get the code
```bash
git clone <repository-url> placegenie
cd placegenie
```

### 2. Database setup
```bash
copy database\setup.sql database\setup.local.sql      # macOS/Linux: cp
```
Open `database/setup.local.sql`, replace every `change_me` with a password of your choice, then run it as the MySQL admin:
```bash
mysql -u root -p < database/setup.local.sql
```
This creates the `placegenie` database and a `placegenie` user limited to it. `setup.local.sql` is git-ignored, so
your password stays private. Tables are created automatically when the backend starts.
Full guide, troubleshooting and backups: [docs/DATABASE.md](docs/DATABASE.md).

### 3. Environment variables
```bash
copy backend\.env.example backend\.env                # macOS/Linux: cp
copy frontend\.env.example frontend\.env
```
In `backend/.env` set at least:

| Variable | Value |
|---|---|
| `DB_PASSWORD` | the password from step 2 |
| `JWT_SECRET_KEY` | a random value of 32+ characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

Everything else has working defaults (MySQL on `127.0.0.1:3306`, frontend on port 5173, chatbot without an external
AI). The frontend `.env` needs no changes. All variables: [docs/CONFIGURATION.md](docs/CONFIGURATION.md).
`.env` files are git-ignored; never commit them.

### 4. Backend startup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.database.seed_demo                       # optional: 10 fictional companies, 19 jobs
python -m app.database.create_coordinator              # first coordinator (asks for name, email, hidden password)
uvicorn app.main:app --reload --port 8000
```
Check http://127.0.0.1:8000/api/v1/health – it must show `"status": "ok"` and `"database": {"connected": true}`.
API explorer: http://127.0.0.1:8000/docs

### 5. Frontend startup
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. Students register on the site; coordinators log in with the account from step 4.

Production build: `npm run build` (output in `frontend/dist/`). Server deployment with HTTPS and nginx:
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Demo accounts
No accounts or passwords are stored in the repository. For a demonstration, create these **local demo** accounts
(use them only on your own machine and never on a shared server):

| Role | Email | Password | How it is created |
|---|---|---|---|
| Coordinator | `coordinator@placegenie.demo` | `PlaceGenie@2026` | `python -m app.database.create_coordinator` (name: *Demo Coordinator*) |
| Student | `student@placegenie.demo` | `PlaceGenie@2026` | registered in the app during the demo (name: *Ananya Kulkarni*) |

Passwords must have at least 8 characters with letters and numbers. A fictional sample resume for the demo student is
in [docs/demo/sample-resume.pdf](docs/demo/sample-resume.pdf). Load the demo companies and jobs first
(`python -m app.database.seed_demo`).

## How to demonstrate PlaceGenie AI

A complete walk-through, about 15 minutes. It uses the demo accounts and demo data above; the expected results were
checked against a real MySQL database. Keep two browser windows open (one normal, one private) so the coordinator and
the student can be logged in at the same time.

**Preparation:** database set up, backend and frontend running, `seed_demo` loaded, demo coordinator created.

| # | Step | Who / where | What to do | What you should see |
|---|---|---|---|---|
| 1 | **Coordinator creates jobs** | Coordinator → *Jobs* → **Add job** | Company *Aurora Analytics*, title *Data Engineer Intern*, type *Internship*, location *Pune*, minimum CGPA *7.5*, maximum backlogs *0*, a deadline in the future; skills **Python, SQL, Docker** (all *Required*, weight 3); allowed branches *Computer Science and Engineering* and *Information Technology* | "Job added."; the job appears in the list (20 jobs). Also show *Companies* (10 fictional companies) |
| 2 | **Student registers** | Private window → **Register** | Name *Ananya Kulkarni*, email `student@placegenie.demo`, password `PlaceGenie@2026` | Logged in and taken to the student dashboard, which says what to do first (complete the profile) |
| 3 | **Student completes profile** | *My profile* | Phone, college *Demo Institute of Technology*, branch *Computer Science and Engineering*, year 3, semester 5, CGPA *8.1*, backlogs 0, interests *data analysis, dashboards*; skills **Python, SQL, Excel, Statistics** (Intermediate); preferred role *Data Analyst*; one project *Sales Insights Dashboard* | The completeness bar reaches **100%** |
| 4 | **Student uploads resume** | *Resume* | Upload `docs/demo/sample-resume.pdf`. Optionally show that a `.txt` or Word file is refused | Upload accepted; the analysis opens |
| 5 | **Resume analysis** | *Resume analysis* | Walk through the page | Completeness score **97/100**, all sections found, 9 skills detected (Python, SQL, Excel, Statistics, Pandas, **Power BI**, Git, MySQL, Communication) with where each was found, suggestions, best-matching jobs. Click **Add 5 detected skills to my profile** (the number is the skills not yet in the profile) – this matters in step 8 |
| 6 | **Eligibility check** | *Jobs* → *Data Analyst* → **Check Eligibility**; then *Data Engineer Intern* | | *Data Analyst*: **Eligible**, every rule passed (CGPA 8.1 ≥ 7.0, branch allowed, backlogs within limit, required skills held). *Data Engineer Intern*: **Not eligible – missing required skill: Docker**, while CGPA and branch pass. Each rule shows required vs your value |
| 7 | **Recommendations** | *Recommended* | Open the breakdown of the top job | *Data Analyst* ranked first with a high score (≈ 90) and the reasons; *Data Engineer Intern* is shown lower, flagged not eligible (scores are multiplied by 0.5 when not eligible). Tick **Only jobs I'm eligible for** |
| 8 | **Skill gap** | *Skill gap* → choose *Data Engineer Intern*, then *Data Analyst* | | *Data Engineer Intern*: **67%** match, missing **Docker – high priority** ("Required for this job", "Essential: weight 3 out of 5"). *Data Analyst*: 100% after step 5 added Power BI (it was 88% with Power BI missing before) |
| 9 | **Application** | *Data Analyst* job page → **Apply** | Confirm; then try to apply again | Status **Applied**; the second attempt is refused ("You have already applied to this job") |
| 10 | **Coordinator updates status** | Coordinator → *Applications* | Filter by company *Aurora Analytics*; change Ananya's status to **Shortlisted** → Update | The student's *Applications* page now shows *Shortlisted* on the status tracker |
| 11 | **Interview tracking** | Student → application → **Add interview** | *Technical interview*, a date next week, notes *SQL joins and a dashboard case study* | Appears under *Interviews → Upcoming*; after the date, record the result (Passed / Not cleared) |
| 12 | **Dashboard** | Student → *Dashboard* | | Progress **5 of 6 steps** (profile, resume, applied, shortlisted, interview recorded; only "offer" left), top recommendations, upcoming interview, skill gaps. Ask the **Assistant**: *"Am I eligible for Data Engineer Intern?"* – it answers from the database (not eligible, Docker missing) |
| 13 | **Coordinator monitoring** | Coordinator → *Dashboard*, *Students*, *Progress* | Open Ananya from *Students* | Totals (1 student, 20 jobs, 1 application, 1 shortlisted); placement rate shown as "needs at least 5 students" instead of a misleading percentage; Ananya's full placement profile, the same progress as the student sees |
| 14 | **Reports** | Coordinator → *Report*; student → *Report* | Download **Applications CSV**; **Print / save as PDF** | Placement report with charts (status distribution, company-wise and job-wise applications, skill gaps); the CSV opens in Excel. The student's report shows *In the selection process* |

Optional finish: set the status to **Selected** and show that the student's outcome, the dashboard and the coordinator's
"Selected students" table all update immediately (nothing is cached).

Points worth explaining in a viva: every eligibility verdict lists the rule that failed; the recommendation score is a
weighted sum shown in the breakdown; the chatbot never invents numbers (data questions are answered from the
database); students cannot see or change each other's data or the official status.

## Testing
```bash
cd backend  && python -m pytest       # 1,040 tests (~15 min): every module, authorization of all 72 routes,
                                      # malformed input on every route, security, query efficiency
cd frontend && npm test               # 233 tests
cd frontend && npm run lint && npm run build
```
Backend tests use a temporary SQLite database and never touch MySQL or your `.env` secrets.
What each test file covers and the manual checks done before release: [docs/TESTING.md](docs/TESTING.md).

## API documentation
- Interactive (all request/response schemas, try it out): **http://127.0.0.1:8000/docs** (or `/redoc`)
- Reference of all 72 endpoints with who may call each: [docs/API.md](docs/API.md)

Base path `/api/v1`. Log in with `POST /auth/login`, then send `Authorization: Bearer <token>`.

## Screenshots
Add images to `docs/screenshots/` and they will appear here.

| Screen | File |
|---|---|
| Login | `docs/screenshots/login.png` |
| Student dashboard | `docs/screenshots/student-dashboard.png` |
| Eligibility check | `docs/screenshots/eligibility.png` |
| Recommendations | `docs/screenshots/recommendations.png` |
| Resume analysis | `docs/screenshots/resume-analysis.png` |
| Skill gap | `docs/screenshots/skill-gap.png` |
| Placement assistant | `docs/screenshots/chatbot.png` |
| Coordinator dashboard | `docs/screenshots/coordinator-dashboard.png` |
| Placement report | `docs/screenshots/coordinator-report.png` |

<!-- Example once the files exist:
![Student dashboard](docs/screenshots/student-dashboard.png)
-->

## More documentation
| Document | Contents |
|---|---|
| [DEVELOPMENT.md](DEVELOPMENT.md) | daily workflow, code conventions, adding an endpoint or table |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | layers, request flow, design principles, module map |
| [docs/FEATURES.md](docs/FEATURES.md) | the exact rules of every module (eligibility, scoring, resume, skill gap, chatbot, reports) |
| [docs/API.md](docs/API.md) | all endpoints, roles, status codes |
| [docs/DATABASE.md](docs/DATABASE.md) | setup, troubleshooting, design rules, every table and column, backups |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | every environment variable |
| [docs/TESTING.md](docs/TESTING.md) | running and writing tests, what is covered |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | production setup with nginx, HTTPS, systemd |
| [docs/CHECKLIST.md](docs/CHECKLIST.md) | final project checklist |

## Known limitations
- Login attempts are not rate limited (the chatbot is); tokens stay valid until they expire (60 minutes by default).
- No database migration tool: new tables are created automatically, changed tables need manual changes.
- Resume analysis needs a text-based PDF (no OCR for scanned images) and uses keyword/pattern rules, so unusual layouts can be read imperfectly.
- Times are stored without a time zone (one college, one time zone).
