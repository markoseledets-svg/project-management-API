import itertools
import json
import random

from locust import HttpUser, between, task

with open("benchmarks/sessions.json") as f:
    SESSIONS = json.load(f)

SESSIONS_BY_EMAIL = {s["user"]: s for s in SESSIONS}
SESSIONS_BY_ID = {s["public_id"]: s for s in SESSIONS if "public_id" in s}

OWNER_PAIRS = [
    (s, p) for s in SESSIONS for p in s["projects"] if p["user_role"] == "owner"
]

_sessions = itertools.cycle(SESSIONS)
_owner_pairs = itertools.cycle(OWNER_PAIRS)

ME = "/api/v1/auth/me"
MEMBERS = "/api/v1/projects/members/{pid}"
CHANGE_ROLE = "/api/v1/projects/change-role/{pid}"
TASKS = "/api/v1/projects/{pid}/tasks/"
CREATE_TASK = "/api/v1/projects/{pid}/tasks/"


class Member(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        session = next(_sessions)
        self.client.cookies.update(session["cookies"])
        self.projects = session["projects"]
        # RoleChecker only ever flips editor <-> viewer, so owner/admin roles are stable
        # for the whole run: every request below must succeed.
        self.stable_writers = [
            p for p in self.projects if p["user_role"] in {"owner", "admin"}
        ]
        self.adminable = self.stable_writers

    def random_pid(self):
        return random.choice(self.projects)["pid"]

    @task(5)
    def list_members(self):
        if not self.adminable:
            return
        pid = random.choice(self.adminable)["pid"]
        page = 1 if random.random() < 0.8 else 2
        with self.client.get(
            MEMBERS.format(pid=pid),
            params={"page": page, "limit": 20},
            name="GET members",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(4)
    def list_tasks(self):
        page = 1 if random.random() < 0.8 else 2
        with self.client.get(
            TASKS.format(pid=self.random_pid()),
            params={"page": page, "limit": 20},
            name="GET tasks",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def me(self):
        with self.client.get(ME, name="GET me", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def create_task(self):
        if not self.stable_writers:
            return
        pid = random.choice(self.stable_writers)["pid"]
        with self.client.post(
            CREATE_TASK.format(pid=pid),
            json={"task_name": "bench task", "description": "bench"},
            name="POST task",
            catch_response=True,
        ) as resp:
            if resp.status_code != 201:
                resp.failure(f"Unexpected status: {resp.status_code}")


class RoleChecker(HttpUser):
    fixed_count = 5
    wait_time = between(2, 4)

    def on_start(self):
        session, project = next(_owner_pairs)
        self.client.cookies.update(session["cookies"])
        self.pid = project["pid"]

    @task
    def role_change_is_visible(self):
        members_url = MEMBERS.format(pid=self.pid)
        params = {"page": 1, "limit": 20}

        before = self.client.get(members_url, params=params, name="CHECK members before")
        if before.status_code != 200:
            return
        candidates = [
            m for m in before.json()["items"]
            if m["user_role"] in ("editor", "viewer")
        ]
        if not candidates:
            return

        target = random.choice(candidates)
        target_session = SESSIONS_BY_ID.get(target["public_id"]) or SESSIONS_BY_EMAIL.get(target["email"])
        if not target_session:
            return

        new_role = "viewer" if target["user_role"] == "editor" else "editor"

        patch = self.client.patch(
            CHANGE_ROLE.format(pid=self.pid),
            json={"user_public_id": target["public_id"], "user_role": new_role},
            name="PATCH change-role",
        )
        if patch.status_code != 204:
            return

        expected = 403 if new_role == "viewer" else 201
        with self.client.post(
            CREATE_TASK.format(pid=self.pid),
            json={"task_name": "role probe", "description": "bench"},
            cookies=target_session["cookies"],
            name=f"CHECK {new_role} write -> {expected}",
            catch_response=True,
        ) as resp:
            if resp.status_code == expected:
                resp.success()
            else:
                resp.failure(
                    f"Stale permissions! Expected {expected} for {new_role}, got {resp.status_code}"
                )

        with self.client.get(
            members_url, params=params, name="CHECK members after", catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"status {response.status_code}")
                return
            actual = next(
                (m["user_role"] for m in response.json()["items"]
                 if m["public_id"] == target["public_id"]),
                None,
            )
            if actual != new_role:
                response.failure(f"stale members list: expected {new_role}, got {actual}")
            else:
                response.success()