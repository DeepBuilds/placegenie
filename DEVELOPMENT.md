# Developing PlaceGenie AI

How to work on the code. To install and run the project, see the [README](README.md).

## Daily workflow

Two terminals:

```bash
# 1 - backend, reloads on save
cd backend
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 2 - frontend, hot reload
cd frontend
npm run dev                            # http://localhost:5173
```

API playground: http://127.0.0.1:8000/docs (click **Authorize** and paste a token from `POST /auth/login`).

Before committing:

```bash
cd backend  && python -m pytest -x -q
cd frontend && npm run lint && npm test && npm run build
```

## Backend conventions

The layers only call downwards: **router -> service -> repository / ai -> model**.

| Layer | Rule |
|---|---|
| `routers/` | HTTP only: declare the path, the role (`Depends(require_student)`, `require_coordinator` or `get_current_user`), the request and response schemas, and call **one** service function. No SQL, no business rules |
| `services/` | the use case. Raise `HTTPException` with a clear, user-facing message (404 for "not found or not yours", 409 for conflicts) |
| `repositories/` | SQLAlchemy queries. Load related rows with `selectinload` so lists never run one query per row (a test counts queries) |
| `ai/` | pure functions: plain data in, plain data with reasons out. No database, no HTTP; easy to unit-test and to explain |
| `schemas/` | Pydantic models. Input models carry the limits (`max_length` that fits the column, `ge`/`le`); ids use `PathId` / `QueryId` / `BodyId` from `schemas/ids.py` |
| `models/` | SQLAlchemy tables |

Other rules:
- **Ownership:** a student's own data is always looked up together with their `student_id`; another student's record is
  "not found" (404), never "forbidden", so ids cannot be probed.
- **Secrets** come from `core/config.py` (environment); never put a key or password in code.
- **Errors** are user-facing sentences. Unexpected exceptions are logged and returned as a generic 500 by `main.py`.
- **Text matching** in rules is case-insensitive and whole-word; user text used in a `LIKE` search is escaped.

### Adding an endpoint (checklist)
1. Schema(s) in `app/schemas/`, function in a service, route in a router (register a new router in `app/main.py`).
2. Add the route to the right list in `backend/tests/test_authorization_matrix.py` (the suite fails until you do).
3. Tests for success, validation errors, the wrong role and another user's data.
4. Call it from `frontend/src/api/<area>.js`.
5. Regenerate or update [docs/API.md](docs/API.md).

### Changing the database
Add or change a model in `app/models/` and import it in `app/models/__init__.py`. New tables are created at startup;
**existing tables are not altered** (there is no migration tool). On your development database, drop the changed table
(or the whole database) and restart. Update [docs/DATABASE.md](docs/DATABASE.md).

## Frontend conventions
- Pages in `src/pages/student/` or `src/pages/coordinator/`, registered in `src/App.jsx` inside the matching
  `<ProtectedRoute role="...">`, and linked from `src/components/Navbar.jsx`.
- All HTTP goes through `src/api/client.js` (adds the token; a 401 logs the user out). Show errors with
  `getErrorMessage(err)` from `src/utils/errors.js`.
- Load data with `useLoad(fetcher, key)`; keep list filters in the URL with `useUrlFilters()` so links and the back
  button work.
- Every data view has a loading state, an empty state that says what to do next, and an error state.
- Use labels, `aria-*` and `role="alert"` / `role="status"` for messages; the tests find elements the way a screen
  reader does.
- Tailwind classes only; shared input/button styles are exported from `src/components/profile/Section.jsx`.

## Useful commands

| Task | Command (from `backend/`) |
|---|---|
| Create a coordinator | `python -m app.database.create_coordinator` |
| Load demo companies and jobs | `python -m app.database.seed_demo` |
| Re-insert reference lists | `python -m app.database.seed` (also runs at startup) |
| Run one test | `python -m pytest tests/test_jobs.py::test_company_crud -q` |
| Lint the frontend | `npm run lint` (from `frontend/`) |

## Project history
The project was built in phases, one commit each (`git log --oneline`): setup, database, authentication, profile,
companies and jobs, eligibility, recommendations, resume analysis, skill gap, applications and interviews, chatbot,
student dashboard, coordinator dashboard, reports, audit, documentation.
