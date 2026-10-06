# PlaceGenie AI - testing

## Running the tests

```bash
# backend (from backend/, virtual environment active or use .venv\Scripts\python)
python -m pytest                       # all 1,046 tests, about 15 minutes
python -m pytest tests/test_jobs.py    # one file
python -m pytest -k eligibility        # by name
python -m pytest -x -q                 # stop at the first failure, short output

# frontend (from frontend/)
npm test                               # 234 tests, about 15 seconds
npm run lint                           # oxlint
npm run build                          # production build must succeed
```

The backend tests never use your MySQL database or your `.env` secrets: every test gets a fresh in-memory SQLite
database and its own JWT secret (`backend/tests/conftest.py`). Uploaded files go to a temporary folder. The frontend
tests mock the API, so the backend does not need to be running.

## What is covered

### Backend (`backend/tests/`)
| File | Covers |
|---|---|
| `test_health.py` | health endpoint, API docs |
| `test_auth.py` | registration, login, wrong password vs unknown email (same answer), disabled accounts, expired/tampered tokens, roles |
| `test_models.py` | tables, relations, cascades, unique rules |
| `test_profile.py` | profile, skills, certifications, projects, experience, preferences: CRUD, validation, completeness, ownership |
| `test_jobs.py` | companies and jobs: CRUD, search (wildcards treated literally), every filter, sorting, pagination, visibility of closed jobs, delete protection |
| `test_eligibility_rules.py`, `test_eligibility_api.py` | each rule (CGPA, branch, backlogs, skills, certifications, experience, deadline), boundary values, missing data, several failures at once |
| `test_recommender.py`, `test_recommendations_api.py` | scoring factors and weights, ranking, eligibility penalty, empty profile, no jobs, determinism |
| `test_resume_pipeline.py`, `test_resume_api.py` | PDF validation (type, signature, size, pages, corrupt, empty), extraction, sections, skills, analysis, path safety, ownership |
| `test_skill_gap_rules.py`, `test_skill_gap_api.py` | full/partial/zero match, no skills, priorities and reasons, agreement with the recommender and eligibility |
| `test_applications_api.py` | apply, duplicates, deadlines, withdraw, status changes, interviews (create, update, dates, ownership) |
| `test_chatbot_units.py`, `test_chat_api.py` | intents, data answers, LLM configured / missing / failing, empty and overlong messages, rate limit, privacy, ownership |
| `test_dashboard_api.py` | student dashboard sections, empty states, agreement with the other pages, partial failures |
| `test_coordinator_api.py` | coordinator dashboard numbers, student search and filters, cohort progress, analytics, CSV reports |
| `test_reports_api.py` | student and coordinator reports against hand-worked sample data; empty datasets; query counts |
| `test_authorization_matrix.py` | every API route classified as public / any user / coordinator / student and checked for each role; unclassified routes fail |
| `test_robustness.py` | every route called with odd ids, malformed JSON, wrong types, NaN, huge strings, SQL-like text as each role: never a 5xx |
| `test_security.py` | CORS, database down, unexpected errors, security headers, no secrets or hashes in any response, secret files not in git |
| `test_query_efficiency.py` | 17 list/dashboard/report endpoints: the number of SQL queries must not grow with the data |
| `test_source_hygiene.py` | no invisible control characters in the source |

### Frontend (`frontend/src/tests/`)
One file per area: `auth`, `profile`, `jobs`, `eligibility`, `recommendations`, `resume`, `skillgap`, `applications`,
`chat`, `dashboard`, `navbar`, `coordinator`, `reports`. They render the real pages with a mocked API and check what the
user sees and can do: forms and validation messages, empty and error states, role redirects, filters kept in the URL,
status updates, downloads and chart scaling.

## Manual checks done before release
Beyond the automated tests, the application was checked against a real MySQL database:
- every student and coordinator page opened in the browser with realistic data (including a real PDF resume),
  plus invalid ids and pages of the other role, with the browser console and the server log checked for errors;
- report figures compared with independent SQL counts;
- eight simultaneous registrations with the same email and eight simultaneous applications to the same job: exactly
  one succeeds, the others get a clear 409;
- every input length limit compared with its database column size.

## Writing a new test
- Use the fixtures in `conftest.py`: `client`, `db_session`, `student_token`, `coordinator_token`, `coordinator`.
  `seed_demo_data(db_session)` loads the demo companies and jobs.
- Helpers for building a cohort of students with applications and interviews are in `test_coordinator_api.py`
  (`make_student`, `apply`, `add_interview`).
- A new API route must be added to the lists in `test_authorization_matrix.py`, otherwise that test fails.
