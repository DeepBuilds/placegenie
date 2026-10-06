# PlaceGenie AI - environment variables

Settings are read from environment variables, or from a `.env` file in the folder the program starts in
(`backend/.env` for the backend, `frontend/.env` for Vite). Both `.env` files are git-ignored; the committed
`.env.example` files contain placeholders only. Copy and edit:

```bash
copy backend\.env.example backend\.env        # macOS/Linux: cp backend/.env.example backend/.env
copy frontend\.env.example frontend\.env
```

## Backend (`backend/.env`)

Defined in `backend/app/core/config.py`. Restart the backend after a change.

### Application
| Variable | Default | Meaning |
|---|---|---|
| `APP_NAME` | `PlaceGenie AI` | shown in `/health` and the API docs |
| `APP_ENV` | `development` | shown in `/health`; informational (behaviour does not change) |
| `APP_VERSION` | `0.1.0` | shown in `/health` |

### Database (required)
| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` | `127.0.0.1` | MySQL server |
| `DB_PORT` | `3306` | |
| `DB_USER` | `placegenie` | the user created by `database/setup.sql` |
| `DB_PASSWORD` | *(empty)* | **secret** - the password you chose in `setup.local.sql` |
| `DB_NAME` | `placegenie` | |

### Security (required)
| Variable | Default | Meaning |
|---|---|---|
| `JWT_SECRET_KEY` | *(empty)* | **secret** - signs login tokens. Must be at least 32 characters; the app refuses to issue tokens otherwise. Generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it logs everyone out |
| `JWT_ALGORITHM` | `HS256` | leave as is |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | how long a login lasts |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | comma-separated list of the frontend addresses allowed to call the API from a browser. Use the exact production URL (scheme + host + port), never `*` |

### Resume uploads
| Variable | Default | Meaning |
|---|---|---|
| `UPLOAD_DIR` | `uploads` | folder for resume PDFs; a relative path is inside `backend/` |
| `RESUME_MAX_MB` | `5` | largest accepted file |
| `RESUME_MAX_PAGES` | `10` | longest accepted resume |

### Chatbot (all optional)
| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `none` | `none` = built-in placement guide only (the app is fully usable); `anthropic` = Claude; `openai` = OpenAI or any OpenAI-compatible server |
| `LLM_API_KEY` | *(empty)* | **secret** - the provider's API key. Empty means the built-in guide answers |
| `LLM_MODEL` | *(empty)* | empty = `claude-haiku-4-5-20251001` (anthropic) or `gpt-4o-mini` (openai) |
| `LLM_BASE_URL` | *(empty)* | empty = the provider's public endpoint; set it for a self-hosted OpenAI-compatible server |
| `LLM_TIMEOUT_SECONDS` | `20` | after this the built-in guide answers instead |
| `LLM_MAX_TOKENS` | `600` | longest AI reply |
| `LLM_SHARE_PROFILE` | `true` | `true` sends a short, contact-free profile summary (branch, CGPA, skills, preferred roles, application counts) for personal answers; `false` sends only the question |
| `CHAT_RATE_LIMIT_PER_MINUTE` | `15` | messages per student per minute (stored in the database, so it holds across several server processes) |
| `CHAT_MAX_MESSAGE_CHARS` | `1000` | longest message |
| `CHAT_MAX_MESSAGES_PER_CONVERSATION` | `200` | |
| `CHAT_HISTORY_TURNS` | `10` | earlier messages given to the LLM as context |

The LLM never receives the student's name, email, phone number, resume text or interview notes.

## Frontend (`frontend/.env`)

Read by Vite when it starts (`npm run dev`) or builds (`npm run build`); a built site has the values baked in.

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | where the browser sends API calls. Keep `/api/v1` when the API is served from the same address (dev proxy or a reverse proxy); use a full URL such as `https://api.example.edu/api/v1` if the API is on another host (then add the site's address to `CORS_ORIGINS`) |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:8000` | development only: where the Vite dev server forwards `/api` |

Nothing secret belongs in the frontend `.env`: everything in it ends up in the JavaScript sent to browsers.

## Tests

The backend tests do not read your `.env` secrets or touch MySQL: `backend/tests/conftest.py` sets its own JWT secret
and uses a temporary in-memory SQLite database for every test.
