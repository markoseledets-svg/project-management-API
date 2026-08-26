# Project Manager API

A modern, full-featured REST API for project and task management with role-based access control (RBAC), multi-session management, and JWT token rotation. Built with FastAPI, PostgreSQL, Redis, and SQLAlchemy 2.0.

---

## Features

### 🔐 Authentication & Session Management
- **JWT Auth with Rotation & Family Tracking:** Access + refresh tokens in secure HTTP-only cookies with automatic rotation and token reuse detection.
- **Active Session Dashboard:** View active sessions with parsed device, browser, and OS metadata (`GET /api/v1/auth/active-sessions`).
- **Granular Session Revocation:** Revoke specific device sessions (`POST /api/v1/auth/logout-session/{token_public_id}`) or logout from all devices at once (`POST /api/v1/auth/logout-everywhere`).
- **Redis Token Blacklisting:** Instant access token & session invalidation using Redis.
- **Rate Limiting:** Built-in rate limiting across auth endpoints (by IP, email, and user identity).
- **Email Verification (OTP):** Secure registration and forgotten password workflows via SMTP (Brevo/custom).
- **Account Soft-Deletion & Recovery:** 14-day grace period on account deletion (`DELETE /api/v1/auth/delete-account`) with instant one-click restoration via restore tokens (`POST /api/v1/auth/restore-account`).
- **Password Management:** Change password with automatic revocation of all other active sessions, plus OTP-based forgotten password recovery.

### 📁 Project Management & RBAC
- **CRUD Operations:** Create, update, archive/activate, soft-delete, and hard-delete projects.
- **Safety Confirmations:** Hard deletion requires exact project name confirmation and archived status.
- **Multi-User Collaboration:** Invite users to projects via email with assigned roles.
- **Hierarchical Role System:** `OWNER > ADMIN > EDITOR > VIEWER` with strict permission checks on all actions.
- **Project Membership:** Manage member roles, remove members, leave projects, or transfer ownership.

### 📋 Task Management
- **Project-Scoped Tasks:** Create, edit, reassign, and delete tasks within projects.
- **Status Workflow:** Transition tasks through statuses: `TODO` → `IN_PROGRESS` → `REVIEW` → `COMPLETED`.
- **Assignee Support:** Assign and reassign project members to specific tasks.

### 💻 User Interface
- **Interactive Web App (`/app`):** Built-in dashboard to manage projects, tasks, invitations, and active sessions.
- **Interactive Swagger Docs (`/docs`):** Automatically available in development mode.

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | **FastAPI 0.138** |
| Language | **Python 3.12** |
| Database | **PostgreSQL 17** |
| ORM | **SQLAlchemy 2.0 (async)** + **asyncpg** |
| Migrations | **Alembic** |
| Cache & Blacklist | **Redis 7.2** (`redis.asyncio`) |
| Auth & Security | **PyJWT**, **Passlib (bcrypt)**, **uuid6** |
| Validation | **Pydantic v2** |
| Device Parsing | **user-agents** |
| Templating | **Jinja2** |
| Testing | **Pytest**, **Polyfactory**, **FakeRedis** |
| Containerization | **Docker** + **Docker Compose** |

---

## Project Structure

```
.
├── app/
│   ├── main.py                 # FastAPI application factory, middleware, exception handlers
│   └── api/
│       ├── dependencies/       # Dependency Injection (DB session, Redis, rate limiting, auth)
│       └── v1/
│           ├── router.py       # API router aggregator
│           └── routers/        # auth, projects, tasks, frontend routes
├── core/
│   ├── exceptions.py           # Custom API exceptions & error handlers
│   ├── security.py             # JWT token handling, hashing, cookie helpers
│   └── rate_limiter.py
├── database/
│   ├── db_config.py            # Async engine, connection pool configuration
│   ├── redis_config.py         # Redis connection pool
│   └── db_model.py             # SQLAlchemy ORM models (User, RefreshToken, Project, Task, Invitation)
├── repository/                 # Repository layer (DB queries and transactions)
├── services/                   # Business logic layer (Auth, Project, Task, Email, Redis)
├── schemas/                    # Pydantic schemas (requests, responses, validation)
├── templates/                  # Frontend UI templates (app.html, index.html, email.html)
├── tests/
│   ├── conftest.py             # Fixtures, test engine, fake Redis, test client
│   ├── factories/              # Polyfactory model factories
│   ├── auth_test.py            # Authentication, session, and password tests
│   ├── project_test.py         # Project CRUD and permissions tests
│   ├── task_test.py            # Task workflow and assignment tests
│   └── invitation_test.py      # Project invitation tests
├── utils/
│   ├── logger.py               # Application logger
│   └── user_agent_parser.py    # Device / Browser parser for active sessions
├── alembic/                    # Database migrations
├── docker-compose.yaml         # Multi-container setup (API, Migrate, DB, Test DB, Redis)
├── Dockerfile
└── requirements.txt
```

---

## Quick Start

### Docker (Recommended)

```bash
# 1. Clone repository
git clone <repo-url>
cd project-management-API

# 2. Configure environment
cp .env.example .env
# Fill in required credentials in .env

# 3. Build and launch services
docker compose up --build
```

The application will be accessible at:
- Web App: `http://localhost:8000/app`
- Swagger API Docs: `http://localhost:8000/docs` (in `ENV=development`)

---

### Local Development

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment variables
cp .env.example .env

# 4. Run database migrations
alembic upgrade head

# 5. Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Testing

The test suite uses **Pytest** with **Polyfactory** and **FakeRedis** against an isolated PostgreSQL test database with transaction rollback after each test.

```bash
# Run all 59 tests
pytest

# Run tests with output details
pytest -v

# Run specific test modules
pytest tests/auth_test.py
pytest tests/project_test.py
pytest tests/task_test.py
pytest tests/invitation_test.py
```

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL user | `projectDBuser` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `secret_password` |
| `POSTGRES_DB` | Main database name | `projectDB` |
| `DATABASE_URL` | Asyncpg connection string | `postgresql+asyncpg://user:pwd@db:5432/projectDB` |
| `POOL_SIZE` | Database connection pool size | `10` |
| `MAX_OVERFLOW` | Max extra pool connections | `10` |
| `POOL_TIMEOUT` | Connection acquisition timeout (s) | `30` |
| `ACCESS_SECRET_KEY` | Secret for Access JWTs (64 chars) | *Generated key* |
| `REFRESH_SECRET_KEY` | Secret for Refresh JWTs (64 chars) | *Generated key* |
| `RESTORE_SECRET_KEY` | Secret for Account Restore JWTs | *Generated key* |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ENV` | Environment (`development` / `production`) | `development` |
| `REDIS_PASSWORD` | Redis auth password | `redis_secret` |
| `REDIS_URL` | Redis connection URL | `redis://:pwd@redis:6379/0` |
| `SMTP_LOGIN` | SMTP server username | `your_email@gmail.com` |
| `SMTP_KEY` | SMTP server password / API key | `smtp_app_key` |
| `SMTP_SERVER` | SMTP host address | `smtp-relay.brevo.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `TEST_DATABASE_URL` | Isolated test DB connection | `postgresql+asyncpg://...` |

Generate secret keys:
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## Database Migrations

```bash
# Apply migrations to head
alembic upgrade head

# Generate a new migration
alembic revision --autogenerate -m "migration_description"

# Rollback one migration
alembic downgrade -1
```

---

## Roadmap

#### Security & Auth
- [x] Refresh token rotation with token family reuse detection
- [x] Redis-based retry window for concurrent refresh requests
- [x] Rate limiting on sensitive endpoints (IP / email / user based)
- [x] Redis-based access token & family blacklisting on logout
- [x] Granular session management (`/active-sessions`, `/logout-session`, `/logout-everywhere`)
- [x] HTTP-only cookies with `SameSite=Lax` and configurable `Secure` flags
- [x] Email OTP verification for registration & password reset
- [x] Account soft-deletion with 14-day grace period and one-click restore

#### Projects & Tasks
- [x] Role-based access control (`OWNER`, `ADMIN`, `EDITOR`, `VIEWER`)
- [x] Project invitations workflow (send, accept, reject, revoke)
- [x] Member management (role changes, transfer ownership, remove member, leave)
- [x] Safe hard-deletion with name confirmation
- [x] Task status processing (`TODO` → `IN_PROGRESS` → `REVIEW` → `COMPLETED`)
- [x] Task assignees
- [ ] Task priority, tags, and filtering/sorting
- [ ] OAuth2 / Social Login (Google, GitHub)

#### Infrastructure
- [x] Redis caching, rate limiting, and session blacklisting
- [x] Full automated test suite (59 unit & integration tests)
- [ ] Background workers for automated expired token & soft-deleted account cleanup
- [ ] Production CI/CD pipeline and cloud deployment


