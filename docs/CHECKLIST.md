# PlaceGenie AI - final project checklist

Status at the end of the project (verified 6 October 2026 on Windows 11, Python 3.13, Node.js 24, MySQL 8.0).

## Build and run
- [x] Backend starts (`uvicorn app.main:app`) with no errors; `/api/v1/health` reports `"status": "ok"`
- [x] Database connects: health shows `"database": {"connected": true}`; tables and reference data are created at startup
- [x] Frontend production build succeeds (`npm run build`)
- [x] Frontend lint is clean (`npm run lint`)
- [x] Backend tests: **1,046 passed**
- [x] Frontend tests: **234 passed**

## Features (each covered by automated tests and checked in the browser)
- [x] Registration, login, logout, role-based pages and API (student / coordinator)
- [x] Student profile with skills, projects, experience, certifications, preferences and completeness
- [x] Companies and jobs: browse, search, filter; coordinator add/edit/delete
- [x] Eligibility engine with a reason for every rule
- [x] Explainable job recommendations (weighted score with breakdown)
- [x] Resume upload (PDF validation) and analysis; detected skills can be added to the profile
- [x] Skill-gap analysis with priorities and reasons
- [x] Applications (one per job, withdraw, official status by coordinator) and interview tracking
- [x] Placement chatbot: data answers from the database, built-in guide, optional LLM with fallback
- [x] Student dashboard and student report (CSV, print)
- [x] Coordinator dashboard, students, companies, jobs, applications, progress, analytics, placement report, CSV exports

## Security
- [x] `backend/.env`, `frontend/.env`, `database/*.local.sql` and uploaded files are git-ignored (checked with `git check-ignore`)
- [x] Only `.env.example` files (placeholders) are committed; no password, key or token in the repository or its history
- [x] Failed logins limited per email and per address (429 with `Retry-After`)
- [x] Passwords hashed with bcrypt; JWT secret must be 32+ characters; the role is re-read from the database on each request
- [x] Every API route's access rule is tested for visitors, students and coordinators
- [x] Students cannot read or change another student's data (404)
- [x] Input validation on every route (malformed input never causes a server error); ids bounded
- [x] Resume uploads: extension, content type and PDF signature checked; size and page limits; server-generated file names
- [x] CORS limited to the configured frontend; security headers on every response
- [x] Errors never expose stack traces, SQL or secrets; CSV exports protected against formula injection

## Quality
- [x] No query-per-row (N+1) problems on 17 list, dashboard and report endpoints (tested)
- [x] Concurrent duplicate registrations and applications handled cleanly on MySQL
- [x] Empty states, loading states and error states on every page
- [x] Pages usable on a phone-sized screen (no horizontal scrolling)

## Documentation
- [x] [README](../README.md): objective, features, stack, architecture, folders, requirements, installation, database
      setup, environment variables, startup, demo accounts, demo walk-through, testing, API, screenshots placeholder
- [x] [DEVELOPMENT.md](../DEVELOPMENT.md), [ARCHITECTURE](ARCHITECTURE.md), [FEATURES](FEATURES.md), [API](API.md),
      [DATABASE](DATABASE.md), [CONFIGURATION](CONFIGURATION.md), [TESTING](TESTING.md), [DEPLOYMENT](DEPLOYMENT.md)
- [x] Demo walk-through checked step by step against a real MySQL database; fictional sample resume in `docs/demo/`
- [ ] Screenshots: add images to `docs/screenshots/` (see the README section)

## Before a viva or demo
- [ ] MySQL running; `python -m app.database.seed_demo` loaded
- [ ] Demo coordinator created (`create_coordinator`); demo student **not** yet registered (it is registered live)
- [ ] Backend and frontend running; health page shows the database connected
- [ ] `docs/demo/sample-resume.pdf` at hand
- [ ] Two browser windows (one private) for coordinator and student

## Known limitations (documented, accepted for this version)
- Login limits are kept in memory per server process; tokens stay valid until expiry (60 minutes), even after logout
- No schema migration tool
- Resume analysis needs a text-based PDF and is keyword/pattern based
- Deleting a user directly in MySQL leaves their resume file on disk (the app has no account deletion)
