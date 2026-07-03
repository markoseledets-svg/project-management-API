# Project Manager API

A REST API for managing projects and tasks with JWT authentication and role-based access control. Built with FastAPI and PostgreSQL. Work in progress.

---

## Features

- User registration and login (JWT access token + refresh token with rotation)
- Project management — create, update, change status, soft-delete
- Multi-user collaboration — invite users to projects by email, assign roles (admin / editor / viewer)
- Task management — create, update, toggle completion, delete, scoped to a project
- RBAC — every operation is verified against the user's role in the project
- Swagger UI available at `/docs` in development mode

---

## Tech Stack

| | |
|---|---|
| Framework | FastAPI 0.138 |
| Language | Python 3.12 |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Migrations | Alembic |
| Auth | PyJWT + passlib (bcrypt) |
| Cache / Limits | Redis (redis.asyncio) |
| Validation | Pydantic v2 |
| Runtime | Uvicorn |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
.
├── app/
│   ├── main.py                 # app factory, middleware, exception handlers
│   └── api/
│       ├── dependencies/       # DI: db_dependencies, redis, identity
│       └── v1/
│           ├── router.py
│           └── routers/        # auth, projects, tasks, frontend
├── core/
│   ├── exceptions.py           # custom exceptions
│   └── security.py            # JWT, password hashing
├── database/
│   ├── db_config.py            # engine, connection pool
│   └── db_model.py            # ORM models
├── repository/                 # data access layer
├── services/                   # business logic layer
├── schemas/                    # Pydantic models
├── utils/
│   └── logger.py
├── alembic/
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```

---

## Setup

### Requirements

- Docker and Docker Compose, or Python 3.12+ with a local PostgreSQL instance.

### Docker (recommended)

```bash
git clone <repo-url>
cd project-manager-api

cp .env.example .env
# fill in .env with your values

docker compose up --build
```

Docker Compose starts the database, runs migrations, then starts the API. Available at `http://localhost:8000`.

### Local

```bash
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# set DATABASE_URL to point to your local PostgreSQL

alembic upgrade head

uvicorn app.main:app --reload
```

---

## Environment Variables

```env
# Database Credentials
POSTGRES_USER=my_db_user
POSTGRES_PASSWORD=my_db_password
POSTGRES_DB=my_database

# For Docker use 'db' as host; for local use 'localhost'
DATABASE_URL=postgresql+asyncpg://my_db_user:my_db_password@db:5432/my_database

# Connection Pool Settings
POOL_SIZE=10
POOL_OVERFLOW=10
POOL_TIMEOUT=30

# Security / Auth
ACCESS_SECRET_KEY=your_64_character_access_secret_here
REFRESH_SECRET_KEY=your_64_character_refresh_secret_here
ALGORITHM=HS256

# Redis Cache / Rate Limiting
REDIS_URL=redis://redis:6379/0
# TEST_REDIS_URL=redis://localhost:6379/0

# Email Sending (SMTP)
SMTP_LOGIN=your.email@gmail.com
SMTP_KEY=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465

# Test DB Credentials (for docker-compose)
POSTGRES_TEST_USER=my_test_user
POSTGRES_TEST_PASSWORD=my_test_password
POSTGRES_TEST_DB=my_test_database

# 'development' enables /docs; 'production' disables it
ENV=development
```

Generate secret keys (run twice for access and refresh):

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## Migrations

```bash
# apply all pending migrations
alembic upgrade head

# create a new migration after changing models
alembic revision --autogenerate -m "description"

# downgrade one step
alembic downgrade -1
```

---

## Running

```bash
# development (with auto-reload)
uvicorn app.main:app --reload

# production-like
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs` (only when `ENV=development`)

---

## Roadmap

#### Security
- [ ] Token family — detect refresh token reuse and invalidate the entire chain
- [x] Rate limiting on auth endpoints
- [x] Redis-based Access Token Blacklist (Logout mechanism)
- [ ] CORS hardening and close PostgreSQL port in production
- [ ] Coockies httponly, secure, same-site settings for tokens storing.

#### Features
- [ ] User CRUD (profile update, account management)
- [x] Email verification on registration (OTP via SMTP)
- [ ] Task priority and sorting
- [ ] Extended project member management (update roles, remove members)

#### Infrastructure
- [x] Redis for Rate Limiting, OTP storage, and Token Blacklisting
- [ ] Production deployment and infrastructure validation
