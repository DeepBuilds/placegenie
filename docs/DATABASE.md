# PlaceGenie AI - database

MySQL 8, accessed through SQLAlchemy 2 with the PyMySQL driver. 24 tables, all InnoDB with `utf8mb4`.

## Setting up the database (once)

You need a running MySQL 8 server and an admin account (usually `root`).

**1. Create the database and the application user.** `database/setup.sql` creates the `placegenie` database and a
`placegenie` user that can only use that database. Make a private copy and choose a password:

```bash
# from the project root
copy database\setup.sql database\setup.local.sql        # macOS/Linux: cp database/setup.sql database/setup.local.sql
# edit database/setup.local.sql: replace every change_me with your own password
mysql -u root -p < database/setup.local.sql
```

`*.local.sql` is git-ignored, so the real password never reaches the repository. The script is safe to run again
(it resets the password if the user already exists). In MySQL Workbench you can open the file and run it instead.

**2. Tell the backend.** In `backend/.env` set `DB_PASSWORD` to the same password (and `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_NAME` if you changed them). See [CONFIGURATION.md](CONFIGURATION.md).

**3. Start the backend once.** On startup it creates any missing tables (`create_all`) and inserts the reference lists
(8 branches, the skill list, job roles). Both steps only add what is missing, so restarts are harmless. Check
`http://127.0.0.1:8000/api/v1/health`: it must show `"database": {"connected": true}`.

**4. Optional demo data.** Ten fictional companies and nineteen jobs with varied requirements:

```bash
cd backend
.venv\Scripts\python -m app.database.seed_demo          # macOS/Linux: .venv/bin/python -m app.database.seed_demo
```

It is idempotent (re-running adds nothing new and never overwrites a coordinator's edits) and is not run automatically.

**5. Create a coordinator account** (students register themselves in the app):

```bash
.venv\Scripts\python -m app.database.create_coordinator   # asks for name, email and a hidden password
```

### Troubleshooting
| Symptom | Cause and fix |
|---|---|
| health shows `"connected": false` | wrong `DB_*` values in `backend/.env`, or MySQL is not running |
| `Access denied for user 'placegenie'@'localhost'` | the password in `.env` differs from the one in `setup.local.sql`; re-run the script |
| `Access denied ... @'127.0.0.1'` | the script creates both `localhost` and `127.0.0.1` users; make sure you ran the whole file |
| `cryptography package is required` | `pip install -r requirements.txt` (MySQL 8 uses `caching_sha2_password`) |
| `Unknown database 'placegenie'` | step 1 was not run |

## Design rules

- **Store facts, compute judgements.** Profiles, jobs, resumes, applications and interviews are stored. Eligibility
  results, recommendation scores, skill gaps, dashboards and reports are **computed from the current data on every
  request** and never stored, so they can never be out of date.
- **One application per student per job** is enforced by a unique key (`applications.student_id, job_id`), not only in code.
- **Deletion:** deleting a user removes their student profile and everything that belongs to it (skills, projects,
  resume rows, applications, interviews, chats) through `ON DELETE CASCADE`. A company or job that already has
  applications cannot be deleted through the API (409); close the job instead. Deleting a branch, skill or job role
  is not offered in the app.
- **Enums** are stored as their upper-case names (`SELECTED`, `TECHNICAL_INTERVIEW`); the API uses lower-case values.
- **Times** are stored as entered, without a time zone (one college, one time zone).
- **Uploaded files** are not in the database: `resumes.file_path` points to `backend/uploads/resumes/<uuid>.pdf`.
  Back up that folder together with the database.

## Maintenance

| Task | How |
|---|---|
| Back up | `mysqldump -u placegenie -p placegenie > placegenie-backup.sql` and copy `backend/uploads/` |
| Restore | `mysql -u placegenie -p placegenie < placegenie-backup.sql` and put `uploads/` back |
| Start from an empty database | `DROP DATABASE placegenie;` then re-run `setup.local.sql` and restart the backend |
| Change the schema | there is no migration tool: `create_all` adds new tables but does not alter existing ones. For a changed table, back up, drop that table and restart (or use `ALTER TABLE`). Adding Alembic is the next step for a long-lived installation |

Known limitation: removing a user directly in MySQL removes their resume row but not the PDF in `backend/uploads/resumes/`.
The app itself has no "delete account" feature, so this only happens through manual database changes.

## Tables

| Group | Tables |
|---|---|
| Identity | `users` (login, role), `students` (profile), `coordinators` |
| Reference data | `branches`, `skills` (with category), `job_roles` |
| Student profile | `student_skills` (with level and source), `certifications`, `projects`, `experiences`, `student_preferred_roles`, `student_preferred_companies` |
| Companies and jobs | `companies`, `jobs`, `job_skills` (required/preferred, weight 1-5), `job_allowed_branches` (none = every branch), `job_required_certifications` |
| Resumes | `resumes` (file metadata and cleaned text), `resume_analyses` (stored analysis), `resume_detected_skills` |
| Applications | `applications` (status), `interview_stages` (stage, date, result, notes) |
| Chatbot | `chat_conversations`, `chat_messages` |

```
users 1-1 students 1-* student_skills *-1 skills
                   1-* certifications / projects / experiences
                   1-* resumes (one active) 1-1 resume_analyses, 1-* resume_detected_skills
                   1-* applications *-1 jobs *-1 companies
                                    1-* interview_stages
                   1-* chat_conversations 1-* chat_messages
jobs 1-* job_skills *-1 skills;  jobs 1-* job_allowed_branches *-1 branches;  jobs 1-* job_required_certifications
users 1-1 coordinators
```

## Column reference

Generated from the SQLAlchemy models (`backend/app/models/`), shown with MySQL types.

### Identity


#### `users`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `email` | VARCHAR(255) | no | unique |
| `password_hash` | VARCHAR(255) | no |  |
| `role` | ENUM(STUDENT, COORDINATOR) | no |  |
| `is_active` | BOOL | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `students`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `user_id` | INTEGER | no | -> `users.id` (on delete CASCADE); unique |
| `full_name` | VARCHAR(100) | no |  |
| `phone` | VARCHAR(20) | yes |  |
| `college` | VARCHAR(150) | yes |  |
| `branch_id` | INTEGER | yes | -> `branches.id` (on delete SET NULL); indexed |
| `year` | INTEGER | yes |  |
| `semester` | INTEGER | yes |  |
| `cgpa` | NUMERIC(4, 2) | yes |  |
| `backlogs` | INTEGER | no |  |
| `interests` | TEXT | yes |  |
| `preferred_location` | VARCHAR(100) | yes |  |
| `preferred_job_type` | ENUM(FULL_TIME, INTERNSHIP, CONTRACT) | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `coordinators`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `user_id` | INTEGER | no | -> `users.id` (on delete CASCADE); unique |
| `full_name` | VARCHAR(100) | no |  |
| `department` | VARCHAR(100) | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### Reference data (seeded automatically)


#### `branches`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `name` | VARCHAR(100) | no | unique |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `skills`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `name` | VARCHAR(100) | no | unique |
| `category` | VARCHAR(50) | yes | indexed |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `job_roles`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `name` | VARCHAR(100) | no | unique |
| `category` | VARCHAR(50) | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### Student profile


#### `student_skills`

| Column | Type | Null | Notes |
|---|---|---|---|
| `student_id` | INTEGER | no | primary key; -> `students.id` (on delete CASCADE) |
| `skill_id` | INTEGER | no | primary key; -> `skills.id` (on delete CASCADE); indexed |
| `proficiency` | ENUM(BEGINNER, INTERMEDIATE, ADVANCED) | no |  |
| `source` | ENUM(MANUAL, RESUME) | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `certifications`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `student_id` | INTEGER | no | -> `students.id` (on delete CASCADE); indexed |
| `name` | VARCHAR(150) | no |  |
| `issuer` | VARCHAR(100) | yes |  |
| `issued_on` | DATE | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `projects`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `student_id` | INTEGER | no | -> `students.id` (on delete CASCADE); indexed |
| `title` | VARCHAR(150) | no |  |
| `description` | TEXT | yes |  |
| `tech_stack` | VARCHAR(255) | yes |  |
| `url` | VARCHAR(255) | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `experiences`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `student_id` | INTEGER | no | -> `students.id` (on delete CASCADE); indexed |
| `organization` | VARCHAR(150) | no |  |
| `role` | VARCHAR(100) | no |  |
| `start_date` | DATE | yes |  |
| `end_date` | DATE | yes |  |
| `description` | TEXT | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `student_preferred_roles`

| Column | Type | Null | Notes |
|---|---|---|---|
| `student_id` | INTEGER | no | primary key; -> `students.id` (on delete CASCADE) |
| `role_id` | INTEGER | no | primary key; -> `job_roles.id` (on delete CASCADE) |

#### `student_preferred_companies`

| Column | Type | Null | Notes |
|---|---|---|---|
| `student_id` | INTEGER | no | primary key; -> `students.id` (on delete CASCADE) |
| `company_id` | INTEGER | no | primary key; -> `companies.id` (on delete CASCADE) |

### Companies and jobs


#### `companies`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `name` | VARCHAR(150) | no | unique |
| `industry` | VARCHAR(100) | yes |  |
| `website` | VARCHAR(255) | yes |  |
| `location` | VARCHAR(100) | yes |  |
| `description` | TEXT | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `jobs`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `company_id` | INTEGER | no | -> `companies.id` (on delete CASCADE); indexed |
| `role_id` | INTEGER | yes | -> `job_roles.id` (on delete SET NULL); indexed |
| `title` | VARCHAR(150) | no |  |
| `description` | TEXT | yes |  |
| `location` | VARCHAR(100) | yes |  |
| `job_type` | ENUM(FULL_TIME, INTERNSHIP, CONTRACT) | no |  |
| `min_cgpa` | NUMERIC(4, 2) | no |  |
| `max_backlogs` | INTEGER | yes |  |
| `min_experience_months` | INTEGER | no |  |
| `deadline` | DATE | yes |  |
| `status` | ENUM(DRAFT, OPEN, CLOSED) | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `job_skills`

| Column | Type | Null | Notes |
|---|---|---|---|
| `job_id` | INTEGER | no | primary key; -> `jobs.id` (on delete CASCADE) |
| `skill_id` | INTEGER | no | primary key; -> `skills.id` (on delete CASCADE); indexed |
| `importance` | ENUM(REQUIRED, PREFERRED) | no |  |
| `weight` | INTEGER | no |  |

#### `job_allowed_branches`

| Column | Type | Null | Notes |
|---|---|---|---|
| `job_id` | INTEGER | no | primary key; -> `jobs.id` (on delete CASCADE) |
| `branch_id` | INTEGER | no | primary key; -> `branches.id` (on delete CASCADE) |

#### `job_required_certifications`

| Column | Type | Null | Notes |
|---|---|---|---|
| `job_id` | INTEGER | no | primary key; -> `jobs.id` (on delete CASCADE) |
| `certification_name` | VARCHAR(150) | no | primary key |

### Resumes


#### `resumes`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `student_id` | INTEGER | no | -> `students.id` (on delete CASCADE); indexed |
| `file_path` | VARCHAR(255) | no |  |
| `original_name` | VARCHAR(255) | no |  |
| `mime_type` | VARCHAR(100) | no |  |
| `size_bytes` | INTEGER | no |  |
| `extracted_text` | LONGTEXT | yes |  |
| `is_active` | BOOL | no |  |
| `uploaded_at` | DATETIME | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `resume_analyses`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `resume_id` | INTEGER | no | -> `resumes.id` (on delete CASCADE); unique |
| `completeness_score` | INTEGER | yes |  |
| `detected_name` | VARCHAR(100) | yes |  |
| `word_count` | INTEGER | yes |  |
| `page_count` | INTEGER | yes |  |
| `sections` | JSON | yes |  |
| `contact` | JSON | yes |  |
| `keywords` | JSON | yes |  |
| `education` | JSON | yes |  |
| `projects` | JSON | yes |  |
| `experience` | JSON | yes |  |
| `certifications` | JSON | yes |  |
| `suggestions` | JSON | yes |  |
| `analyzed_at` | DATETIME | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `resume_detected_skills`

| Column | Type | Null | Notes |
|---|---|---|---|
| `analysis_id` | INTEGER | no | primary key; -> `resume_analyses.id` (on delete CASCADE) |
| `skill_id` | INTEGER | no | primary key; -> `skills.id` (on delete CASCADE); indexed |
| `evidence` | VARCHAR(100) | yes |  |

### Applications and interviews


#### `applications`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `student_id` | INTEGER | no | -> `students.id` (on delete CASCADE) |
| `job_id` | INTEGER | no | -> `jobs.id` (on delete CASCADE); indexed |
| `status` | ENUM(APPLIED, SHORTLISTED, ONLINE_ASSESSMENT, TECHNICAL_INTERVIEW, HR_INTERVIEW, SELECTED, REJECTED, WITHDRAWN) | no |  |
| `applied_at` | DATETIME | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

Unique together: (student_id, job_id)

#### `interview_stages`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `application_id` | INTEGER | no | -> `applications.id` (on delete CASCADE); indexed |
| `stage` | ENUM(ONLINE_ASSESSMENT, TECHNICAL_INTERVIEW, HR_INTERVIEW, OTHER) | no |  |
| `scheduled_at` | DATETIME | yes |  |
| `outcome` | ENUM(PENDING, PASSED, FAILED) | no |  |
| `notes` | TEXT | yes |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### Chatbot


#### `chat_conversations`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `student_id` | INTEGER | no | -> `students.id` (on delete CASCADE) |
| `title` | VARCHAR(100) | no |  |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

#### `chat_messages`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | INTEGER | no | primary key |
| `conversation_id` | INTEGER | no | -> `chat_conversations.id` (on delete CASCADE) |
| `role` | ENUM(USER, ASSISTANT) | no |  |
| `content` | TEXT | no |  |
| `source` | VARCHAR(20) | yes |  |
| `created_at` | DATETIME | no |  |
