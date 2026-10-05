# PlaceGenie AI – Intelligent Placement Assistant

Web-based placement assistant for college students and placement coordinators.
It is a guidance tool; it does not replace recruitment decisions by companies or placement officers.

> **Current status:** Phase 1 (setup) and Phase 2 (database models) are done. Phase 3 (authentication and role-based access) is done, backend and frontend.

## Tech stack
| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, React Router, Axios, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic |
| Database | MySQL 8 (via PyMySQL) |
| AI/ML (later phases) | scikit-learn, pandas, NumPy |

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

## Tests
```bash
cd backend && .venv\Scripts\python -m pytest     # 52 tests: health, auth/RBAC, database models
cd frontend && npm test                            # 12 tests: protected routes, login, register
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
