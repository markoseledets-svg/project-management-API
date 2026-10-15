import asyncio
import json
import os
import random

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.exc import ProgrammingError
from uuid6 import uuid7

from core.config import settings
from core.security import generate_access_jwt
from database.db_model import (
    ProjectModel,
    ProjectStatus,
    TaskModel,
    TaskStatus,
    UserModel,
    UserProjectRelation,
    UserRole,
    Base
)

from sqlalchemy.engine import make_url

POOL_SIZE = settings.pool_size
POOL_OVERFLOW = settings.max_overflow
POOL_TIMEOUT = settings.pool_timeout

TARGET_DB_URL = settings.bench_database_url
if not TARGET_DB_URL:
    raise SystemExit("BENCH_DATABASE_URL is not set (dedicated benchmark database required).")

_target = make_url(TARGET_DB_URL)
_protected = {
    (u.host, u.port, u.database)
    for u in (make_url(url) for url in (settings.database_url, settings.test_database_url) if url)
    if u.database
}
if "bench" not in (_target.database or "").lower() or (_target.host, _target.port, _target.database) in _protected:
    raise SystemExit(
        f"REFUSING TO SEED '{_target.database}': name must contain 'bench' "
        "and must differ from DATABASE_URL / TEST_DATABASE_URL."
    )


N_USERS, N_PROJECTS = 50, 10
TASKS_PER_PROJECT = 150
rng = random.Random(42)


async def main():
    engine = create_async_engine(
        TARGET_DB_URL,
        echo=False,
        pool_size=POOL_SIZE,
        max_overflow=POOL_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=1800,
        pool_pre_ping=True,
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as s:
        try:
            await s.execute(
            text(
                "TRUNCATE TABLE auth_identity, invitations, projects, refresh_tokens, "
                "tasks, user_project_relation, users RESTART IDENTITY CASCADE"
            )
        )
        except ProgrammingError:
            await s.rollback()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        users = [
            UserModel(public_id=uuid7(), email=f"user{i}@email.com")
            for i in range(N_USERS)
        ]
        s.add_all(users)
        await s.flush()

        projects = [
            ProjectModel(
                project_public_id=uuid7(),
                project_name=f"bench-proj{i}",
                status=ProjectStatus.ACTIVE,
            )
            for i in range(N_PROJECTS)
        ]
        s.add_all(projects)
        await s.flush()

        memberships = {u.public_id: [] for u in users}
        project_member_ids = {p.project_public_id: [] for p in projects}
        relations = []

        for i, p in enumerate(projects):
            owner = users[i % N_USERS]
            guaranteed = [
                u for j, u in enumerate(users)
                if j % N_PROJECTS == i and u is not owner
            ]
            pool = [u for u in users if u is not owner and u not in guaranteed]
            target = rng.randint(8, 10)
            extra = rng.sample(pool, max(0, target - len(guaranteed)))
            others = guaranteed + extra
            for idx, u in enumerate([owner] + others):
                user_role = (
                    UserRole.OWNER
                    if idx == 0
                    else rng.choice([UserRole.ADMIN, UserRole.EDITOR, UserRole.VIEWER])
                )
                relations.append(
                    UserProjectRelation(
                        user_public_id=u.public_id,
                        project_public_id=p.project_public_id,
                        user_role=user_role,
                    )
                )
                memberships[u.public_id].append(
                    (str(p.project_public_id), user_role.value)
                )
                project_member_ids[p.project_public_id].append(u.public_id)

        s.add_all(relations)
        await s.flush()

        tasks = []
        for p in projects:
            member_ids = project_member_ids[p.project_public_id]
            for t in range(TASKS_PER_PROJECT):
                status = rng.choice(
                    [
                        TaskStatus.TODO,
                        TaskStatus.IN_PROGRESS,
                        TaskStatus.REVIEW,
                        TaskStatus.COMPLETED,
                    ]
                )
                tasks.append(
                    TaskModel(
                        task_public_id=uuid7(),
                        task_name=f"bench_task_{t}",
                        description=f"bench_task_{t}",
                        status=status,
                        project_public_id=p.project_public_id,
                        assignee_id=None if status == TaskStatus.TODO else rng.choice(member_ids),
                    )
                )
        s.add_all(tasks)
        await s.commit()

    sessions = []
    for u in users:
        projs = memberships[u.public_id]
        if not projs:
            continue
        access_token = generate_access_jwt(
            user_public_id=u.public_id,
            token_family_id=uuid7(),
        )
        sessions.append(
            {
                "user": u.email,
                "public_id": str(u.public_id),
                "cookies": {"access_token": access_token},
                "projects": [{"pid": pid, "user_role": role} for pid, role in projs],
            }
        )
    os.makedirs("benchmarks", exist_ok=True)
    with open("benchmarks/sessions.json", "w") as f:
        json.dump(sessions, f, indent=4, ensure_ascii=False)

    await engine.dispose()

asyncio.run(main())