# PlaceGenie AI - architecture

## Overview

```
 Browser (React 19 single-page app)
   |  HTTPS, JSON, "Authorization: Bearer <JWT>"
   v
 /api/v1  FastAPI backend (Python)
   routers/        HTTP only: parse input, check role, call a service
   services/       the use cases (apply to a job, build a dashboard, ...)
   ai/             pure decision rules: eligibility, recommender, skill gap, resume pipeline, chatbot intents
   repositories/   SQL queries (SQLAlchemy 2)
   models/         tables                     schemas/   request/response shapes (Pydantic)
   |
   v
 MySQL 8                      backend/uploads/  (resume PDFs)        optional LLM API (chatbot only)
```

**Request flow, e.g. "check my eligibility for job 7":**
`POST /api/v1/jobs/7/eligibility` -> `routers/jobs.py` (requires a student token) -> `services/eligibility_service.py`
(loads the student's profile and the job through the repositories) -> `ai/eligibility.py` (plain functions: profile +
job in, verdict with one reason per rule out) -> JSON back to the job page.

## Principles

1. **Explainable rules, not a black box.** Eligibility, recommendations, skill gaps and resume analysis are
   deterministic rules with written weights and thresholds. Every result carries its reasons ("CGPA 7.2 is below the
   minimum 7.5"), so any number on screen can be explained in a viva. The only machine-learning-style component is
   TF-IDF text similarity (scikit-learn) inside the recommender, resume relevance and the chatbot's guide lookup.
2. **One source of truth for each rule.** A rule lives in one place and is reused: the skill-match formula is shared by
   the recommender and the skill-gap page; the student dashboard, the coordinator view of a student and the student
   report all call the same services, so they cannot disagree (tests compare them).
3. **Compute, do not store, judgements.** Only facts are stored; scores, eligibility, dashboards and reports are
   recalculated from the database on every request.
4. **The backend enforces access; the frontend only reflects it.** Every route declares who may call it, and a test
   (`test_authorization_matrix.py`) fails if a new route is not classified.
5. **Guidance, not decisions.** The app never decides who gets hired; the official application status is set only by
   a coordinator, and pages say that results are guidance.

## Backend modules

| Area | Router | Service | Rules (`app/ai/`) |
|---|---|---|---|
| Login, register | `auth.py` | `auth_service.py` | - (bcrypt + JWT in `core/security.py`; roles in `core/deps.py`) |
| Profile | `students.py`, `reference.py` | `profile_service.py` | completeness score |
| Companies, jobs | `companies.py`, `jobs.py` | `job_service.py` | - |
| Eligibility | `jobs.py` | `eligibility_service.py` | `eligibility.py` |
| Recommendations | `recommendations.py` | `recommendation_service.py` | `recommender.py`, `text_similarity.py` |
| Resume | `resumes.py` | `resume_service.py` | `resume/` extract -> clean -> sections -> parse -> skills -> analyze |
| Skill gap | `jobs.py` | `skill_gap_service.py` | `skill_gap.py` |
| Applications, interviews | `applications.py`, `interviews.py` | `application_service.py` | - |
| Chatbot | `chat.py` | `chat_service.py`, `chatbot_engine.py`, `chat_data.py` | `chatbot/` intents, knowledge (guide), prompt, providers |
| Student dashboard | `dashboard.py` | `dashboard_service.py` | reuses the services above |
| Coordinator | `coordinators.py` | `coordinator_service.py` | reuses the services above |
| Reports | `reports.py`, `coordinators.py` | `reporting_service.py`, `report_service.py` (CSV) | - |

Cross-cutting pieces in `app/main.py`: CORS, an early size check for uploads, security headers, and error handlers
(database conflict 409, invalid value 422, database down 503, anything else a JSON 500 without internals).
`app/schemas/ids.py` bounds every id.

### Chatbot design
Questions about the student's own data (eligibility, applications, skill gaps...) are answered from the database by
the same services as the pages, never by a language model. General placement questions go to an LLM only if one is
configured (`LLM_PROVIDER`), otherwise to the built-in guide (about 30 curated topics, matched by TF-IDF). Providers sit
behind a small interface (`ai/chatbot/providers/`), and any provider failure falls back to the guide.

## Frontend

| Folder | Contents |
|---|---|
| `src/api/` | one small module per backend area; `client.js` is the Axios instance that adds the token and logs out on 401 |
| `src/context/`, `src/hooks/` | `AuthContext` (current user, login/logout), `useAuth`, `useLoad` (load data with loading/error state), `useUrlFilters` (filters kept in the URL) |
| `src/routes/ProtectedRoute.jsx` | sends visitors to `/login` and users with the wrong role to their own home |
| `src/pages/student/`, `src/pages/coordinator/` | one file per page |
| `src/components/` | shared pieces: navbar, dashboard widgets, charts (plain HTML bars), forms, status badges |
| `src/utils/` | formatting and validation helpers |
| `src/tests/` | Vitest + Testing Library tests, one file per area |

In development Vite serves the app on port 5173 and forwards `/api` to the backend, so the browser sees one origin.

## Data model in one paragraph
A `user` has a role. A student `user` has one `students` row with skills, projects, experience, certifications and
preferences, at most one active resume (with its stored analysis), applications to jobs (each with interview stages)
and chat conversations. A `company` has `jobs`; each job lists required/preferred skills with weights, allowed
branches and required certifications. Details: [DATABASE.md](DATABASE.md).

## Technology choices
| Choice | Why |
|---|---|
| FastAPI + Pydantic | input validation and the interactive `/docs` page come from the type hints |
| SQLAlchemy 2 + PyMySQL | typed models, works with MySQL in use and SQLite in tests |
| scikit-learn TF-IDF | text similarity that is simple to explain; no training data needed |
| pdfplumber | reliable text extraction from text-based PDFs |
| React + Vite + Tailwind | fast development, small production build |
| JWT bearer tokens | stateless; the role is still re-read from the database on every request |
