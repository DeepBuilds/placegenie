# PlaceGenie AI - deployment

This describes running PlaceGenie AI on one server for a college (for example a Linux VM in the college data centre).
For a classroom demo on a laptop, the development setup in the [README](../README.md) is enough.

```
             https://placement.example.edu
                         |
                      nginx  ---- /            -> frontend/dist (static files, built once)
                         \------- /api/        -> uvicorn on 127.0.0.1:8000 (FastAPI)
                                                     |-- MySQL 8 (same server or a database server)
                                                     \-- backend/uploads/ (resume PDFs, persistent disk)
```

Serving the site and the API from the same address keeps the browser on one origin, so `VITE_API_BASE_URL` stays
`/api/v1` and CORS only needs that one address.

## 1. Before you deploy
- [ ] A strong, new `JWT_SECRET_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), never the development one.
- [ ] A new database password, used only on this server.
- [ ] `CORS_ORIGINS` set to the exact public address, e.g. `https://placement.example.edu`.
- [ ] HTTPS certificate (for example Let's Encrypt). Login tokens must never travel over plain HTTP.
- [ ] `APP_ENV=production` (shown in `/health`, so you can tell instances apart).
- [ ] Backups planned for the database **and** `backend/uploads/` ([DATABASE.md](DATABASE.md#maintenance)).
- [ ] `LLM_PROVIDER=none` unless the college has approved sending questions to an external AI provider.

## 2. Database
Install MySQL 8, then follow [DATABASE.md](DATABASE.md) steps 1-2 with the new password. If MySQL is on another
machine, change `'localhost'` in `setup.local.sql` to the backend server's address and set `DB_HOST`.
Load demo data (`seed_demo`) only on a demo server, not on a real one.

## 3. Backend
```bash
sudo useradd --system --home /opt/placegenie placegenie        # an account without login rights
sudo -u placegenie git clone <repository-url> /opt/placegenie/app
cd /opt/placegenie/app/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env && chmod 600 .env                           # then fill in the production values
.venv/bin/python -m app.database.create_coordinator               # the first coordinator account
```

Run it as a service (`/etc/systemd/system/placegenie.service`):

```ini
[Unit]
Description=PlaceGenie AI API
After=network.target mysql.service

[Service]
User=placegenie
WorkingDirectory=/opt/placegenie/app/backend
ExecStart=/opt/placegenie/app/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now placegenie
curl http://127.0.0.1:8000/api/v1/health        # "database": {"connected": true}
```

Notes: no `--reload` in production. Several workers are safe: logins are stateless tokens and the chat rate limit is
stored in the database. The backend creates missing tables at startup.

## 4. Frontend
Build on the server (or on any machine with Node.js 20.19+ / 22.12+) and copy `dist/`:

```bash
cd /opt/placegenie/app/frontend
npm ci
echo "VITE_API_BASE_URL=/api/v1" > .env
npm run build                 # creates frontend/dist/
```

## 5. nginx
```nginx
server {
    listen 443 ssl;
    server_name placement.example.edu;
    ssl_certificate     /etc/letsencrypt/live/placement.example.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/placement.example.edu/privkey.pem;

    root /opt/placegenie/app/frontend/dist;
    index index.html;

    location / {
        try_files $uri /index.html;         # React Router pages such as /student/jobs
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 6m;            # RESUME_MAX_MB plus room for the form
    }
}

server {                                    # send plain HTTP to HTTPS
    listen 80;
    server_name placement.example.edu;
    return 301 https://$host$request_uri;
}
```

The API docs stay available at `/docs`. If they should not be public, block `/docs`, `/redoc` and `/openapi.json` in nginx.

## 6. Updating
```bash
cd /opt/placegenie/app && sudo -u placegenie git pull
cd backend && .venv/bin/pip install -r requirements.txt && sudo systemctl restart placegenie
cd ../frontend && npm ci && npm run build
```
Take a database backup first. There is no migration tool: new tables are created automatically, but if a release
changes an existing table, apply that change by hand ([DATABASE.md](DATABASE.md#maintenance)).

## 7. After deploying, check
- [ ] `https://<site>/api/v1/health` shows `"status": "ok"` and `"connected": true`
- [ ] the login page loads over HTTPS, and `http://` redirects to `https://`
- [ ] a coordinator can log in; a new student can register, upload a PDF and see the analysis
- [ ] opening `https://<site>/student/jobs` directly (refresh) shows the page, not a 404
- [ ] `backend/.env` is readable only by the service account
- [ ] a backup has been taken and restored once on another machine

## Windows server
The same layout works on Windows: run the backend with `.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2`
as a service (for example with NSSM), and serve `frontend\dist` with IIS (URL Rewrite: send unknown paths to
`index.html`, reverse-proxy `/api` to port 8000) or nginx for Windows.

## Known limitations
- Failed logins are limited per email and per address in each server process (a restart or a second worker has its own count). For a public server, also add an nginx `limit_req` on `/api/v1/auth/login`; uvicorn's `--proxy-headers` (above) makes the real client address visible to the limiter.
- A token stays valid until it expires (`ACCESS_TOKEN_EXPIRE_MINUTES`) even after logout; keep the lifetime short.
- No schema migration tool (see above).
