# PlaceGenie AI - API reference

Base URL: `http://127.0.0.1:8000/api/v1` (in development the frontend reaches it as `/api/v1` through the Vite proxy).
Interactive documentation with every request and response schema: **http://127.0.0.1:8000/docs** (Swagger UI) or `/redoc`.

This page is generated from the running application's OpenAPI schema (72 endpoints). The "Who" column comes from
`backend/tests/test_authorization_matrix.py`, which checks every one of these rules on every test run.

## Conventions
- **Authentication:** `POST /auth/login` returns `access_token`; send it as `Authorization: Bearer <token>`. Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
- **Roles:** students register themselves; coordinators are created with `python -m app.database.create_coordinator`. The role is read from the database on every request.
- **Status codes:** `200/201/204` success - `401` not logged in or token invalid/expired - `403` wrong role - `404` not found (also another student's data, and impossible ids such as `/jobs/0`) - `409` conflict (duplicate email or application, deleting a company/job that has applications, deadline passed) - `413` file too large - `422` invalid input (`detail` is a list of field errors) - `429` too many failed logins or chat messages (see the `Retry-After` header) - `503` database unavailable - `500` unexpected error (no internal details are returned).
- **Errors** always look like `{"detail": "..."}` (or a list of field errors for 422).
- **Lists** that page take `limit` and `offset` and return `items`, `total`, `limit`, `offset`.
- **CSV exports** are UTF-8 with a byte-order mark (opens correctly in Excel); cells that could run as spreadsheet formulas are prefixed with `'`.

## Health

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/health` | Anyone | Liveness + database connectivity check. |  |  |

## Authentication

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| POST | `/auth/login` | Anyone | Log in as a student or coordinator. The returned `user.role` decides the dashboard. |  | JSON |
| POST | `/auth/logout` | Logged in (student or coordinator) | Tokens are stateless JWTs, so logout means the client discards its token. |  |  |
| GET | `/auth/me` | Logged in (student or coordinator) | Current user (the frontend uses this to validate a stored token). |  |  |
| POST | `/auth/register` | Anyone | Register a new student account and sign in. |  | JSON |

## Reference data

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/branches` | Logged in (student or coordinator) | List Branches |  |  |
| GET | `/job-roles` | Logged in (student or coordinator) | List Job Roles |  |  |
| GET | `/skills` | Logged in (student or coordinator) | List Skills |  |  |

## Student profile

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/students/me` | Student | Full profile of the logged-in student, including completeness. |  |  |
| PUT | `/students/me` | Student | Replace basic and academic details. |  | JSON |
| POST | `/students/me/certifications` | Student | Add Certification |  | JSON |
| DELETE | `/students/me/certifications/{item_id}` | Student | Delete Certification |  |  |
| PUT | `/students/me/certifications/{item_id}` | Student | Update Certification |  | JSON |
| POST | `/students/me/experiences` | Student | Add Experience |  | JSON |
| DELETE | `/students/me/experiences/{item_id}` | Student | Delete Experience |  |  |
| PUT | `/students/me/experiences/{item_id}` | Student | Update Experience |  | JSON |
| PUT | `/students/me/preferences` | Student | Update Preferences |  | JSON |
| POST | `/students/me/projects` | Student | Add Project |  | JSON |
| DELETE | `/students/me/projects/{item_id}` | Student | Delete Project |  |  |
| PUT | `/students/me/projects/{item_id}` | Student | Update Project |  | JSON |
| PUT | `/students/me/skills` | Student | Replace the student's whole skill list (ids come from GET /skills). |  | JSON |

## Companies

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/companies` | Logged in (student or coordinator) | List Companies | `q`, `limit`, `offset` |  |
| POST | `/companies` | Coordinator | Create Company |  | JSON |
| DELETE | `/companies/{company_id}` | Coordinator | Delete Company |  |  |
| GET | `/companies/{company_id}` | Logged in (student or coordinator) | Get Company |  |  |
| PUT | `/companies/{company_id}` | Coordinator | Update Company |  | JSON |
| GET | `/companies/{company_id}/jobs` | Logged in (student or coordinator) | Jobs Of Company | `limit`, `offset` |  |

## Jobs

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/jobs` | Logged in (student or coordinator) | Search and filter jobs. Students only ever see open jobs; coordinators see all (optionally by status). | `q`, `company_id`, `job_type`, `role_id`, `skill_id`, `branch_id`, `location`, `max_min_cgpa`, `hide_expired`, `status`, `sort`, `limit`, `offset` |  |
| POST | `/jobs` | Coordinator | Create Job |  | JSON |
| DELETE | `/jobs/{job_id}` | Coordinator | Delete Job |  |  |
| GET | `/jobs/{job_id}` | Logged in (student or coordinator) | Get Job |  |  |
| PUT | `/jobs/{job_id}` | Coordinator | Update Job |  | JSON |
| POST | `/jobs/{job_id}/eligibility` | Student | Rule-based check of the logged-in student's profile against this job's requirements. |  |  |
| GET | `/jobs/{job_id}/skill-gap` | Student | Compare the logged-in student's skills with this job's skills: matched, missing, match % and priorities. |  |  |

## Recommendations

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/recommendations` | Student | Open jobs ranked for the logged-in student with a transparent 0-100 match score. | `role_id`, `location`, `eligible_only`, `sort`, `limit`, `offset` |  |

## Resumes

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| POST | `/resumes` | Student | Upload a PDF resume. It is validated, analysed and stored; it replaces any earlier resume. |  | file upload |
| GET | `/resumes/me` | Student | The logged-in student's current resume, or null if none was uploaded. |  |  |
| DELETE | `/resumes/{resume_id}` | Student | Delete Resume |  |  |
| GET | `/resumes/{resume_id}/analysis` | Student | Resume Analysis |  |  |
| POST | `/resumes/{resume_id}/analyze` | Student | Re-run the analysis on the stored text (no new upload needed). |  |  |
| GET | `/resumes/{resume_id}/file` | Student | Download the student's own PDF. |  |  |
| POST | `/resumes/{resume_id}/sync-skills` | Student | Add the skills detected in this resume to the student's own profile. |  |  |

## Applications

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/applications` | Coordinator | Every student's applications (coordinators only). | `status`, `job_id`, `company_id`, `q`, `limit`, `offset` |  |
| POST | `/applications` | Student | Apply for an open job. One application per student per job (409 if already applied). |  | JSON |
| GET | `/applications/me` | Student | The logged-in student's applications, newest first, with per-status counts. | `status`, `job_id` |  |
| GET | `/applications/{application_id}` | Logged in (student or coordinator) | Application Detail |  |  |
| POST | `/applications/{application_id}/interviews` | Logged in (student or coordinator) | Record an interview / test stage for an application. |  | JSON |
| PATCH | `/applications/{application_id}/status` | Coordinator | Set the official application status (shortlisted, selected, ...). Coordinators only. |  | JSON |
| POST | `/applications/{application_id}/withdraw` | Student | Withdraw your own application (not possible once it is selected or rejected). |  |  |

## Interviews

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/interviews` | Coordinator | Every student's interviews (coordinators only). | `when` |  |
| GET | `/interviews/me` | Student | The logged-in student's interviews: upcoming (soonest first), past (latest first) or unscheduled. | `when` |  |
| DELETE | `/interviews/{interview_id}` | Logged in (student or coordinator) | Delete Interview |  |  |
| GET | `/interviews/{interview_id}` | Logged in (student or coordinator) | Interview Detail |  |  |
| PATCH | `/interviews/{interview_id}` | Logged in (student or coordinator) | Change the stage, date/time, notes or result. Only the fields you send are changed. |  | JSON |

## Chatbot

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| DELETE | `/chat/conversations` | Student | Delete the student's entire chat history. |  |  |
| GET | `/chat/conversations` | Student | The logged-in student's conversations, most recent first. |  |  |
| DELETE | `/chat/conversations/{conversation_id}` | Student | Delete Conversation |  |  |
| GET | `/chat/conversations/{conversation_id}` | Student | Get Conversation |  |  |
| GET | `/chat/info` | Student | Whether an AI model or the built-in guide is answering, plus starter questions. |  |  |
| POST | `/chat/messages` | Student | Send a message and get the assistant's reply. Without `conversation_id` a new conversation starts. |  | JSON |

## Dashboard

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/dashboard` | Student | Everything the student's home page shows, composed from the existing modules. |  |  |

## Reports

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/reports/me` | Student | The logged-in student's own report: applications, statuses, interviews, outcome, recommended jobs, skill gaps and progress. |  |  |
| GET | `/reports/me.csv` | Student | My Report Csv |  |  |

## Coordinators

| Method | Path | Who | What it does | Query parameters | Body |
|---|---|---|---|---|---|
| GET | `/coordinators/analytics` | Coordinator | Analytics |  |  |
| GET | `/coordinators/dashboard` | Coordinator | Headline numbers for the placement cell, computed fresh from the database. |  |  |
| GET | `/coordinators/me` | Coordinator | Coordinator Me |  |  |
| GET | `/coordinators/progress` | Coordinator | How far the whole cohort has got (same milestones as each student's own tracker). |  |  |
| GET | `/coordinators/report` | Coordinator | The placement cell's report: placement statistics, company-wise and job-wise applications, selected students, skill gaps and progress. |  |  |
| GET | `/coordinators/reports` | Coordinator | The reports that can be downloaded. |  |  |
| GET | `/coordinators/reports/{kind}.csv` | Coordinator | Download Report |  |  |
| GET | `/coordinators/students` | Coordinator | Search and filter the student list. | `q`, `branch_id`, `year`, `min_cgpa`, `stage`, `has_resume`, `profile_ready`, `sort`, `limit`, `offset` |  |
| GET | `/coordinators/students/{student_id}` | Coordinator | One student's placement profile: profile, resume, progress, skill gaps, applications and interviews. |  |  |
