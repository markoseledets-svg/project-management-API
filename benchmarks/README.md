# Performance & Cache Benchmarks

Compares the API with Redis caching **ON** vs **OFF** under concurrent load, counts real SQL calls
per request and checks that permission changes are never served stale from cache.

> Numbers in this file are produced by `benchmarks/reports/summary.py`. Raw CSV/JSON reports are
> git-ignored; paste the summary output into the **Results** section after every run.

## What is cached

| Entity | Key | TTL | Invalidated on |
|---|---|---|---|
| User profile | `cache:user:{id}` | 30 min | account deletion |
| Role in project | `cache:user_role:{uid}:{pid}` | 15 min | role change, removal, leave, ownership transfer |
| Project status | `cache:project_status:{pid}` | 15 min | status change, archive, delete |
| Members list | `cache:project_members:{pid}:v{ver}:{page}:{limit}` | 15 min | version bump on membership change |
| Task lists | not cached | – | – |

Invalidation always happens **after** `commit()`. Worst case staleness if the process dies between
commit and invalidation is the TTL (15 min).

## Setup & Test Environment

- **API Container:** FastAPI running on a single Uvicorn worker in Docker (`ProjectAPI`).
- **Database:** Dedicated PostgreSQL 17 Alpine container (`ProjectBenchDB`, port 5434) with `pg_stat_statements` enabled for exact SQL query counting — completely isolated from development/test DB.
- **Database Pool:** SQLAlchemy async engine with `pool_size=15`, `max_overflow=15` (max 30 active DB connections), `pool_timeout=30s`.
- **Cache:** Redis 7.2 Alpine (`ProjectRedis`, port 6379).
- **Test Dataset:** Re-seeded before each mode: 50 active users, 10 collaborative projects, 1 500 tasks, realistic roles and token families.
- **Load Profile:** Locust, 200–250 concurrent users (`Member` ×85% + `RoleChecker` ×15%), think time 0.5–2.0 s, spawn rate 10 users/s, global rate limiting disabled.
- **Execution:** 3 measured runs per mode × 120 s (plus 5s warmup run discarded). Over 95 000 total requests processed.

## How to run

```bash
pip install -r requirements-dev.txt
docker compose up -d                       # base stack (db, redis, api)
python benchmarks/run_benchmarks.py --users 200 --duration 120 --runs 3
python benchmarks/reports/summary.py       # prints medians, ranges, SQL calls per request
```

The runner never modifies `.env`; it passes `ENABLE_CACHING` / `ENABLE_GLOBAL_RATE_LIMIT` dynamically and restores the default API container in a `finally` block.

## How to read the results

- Report **median and [min..max] range** over multiple runs to filter out OS scheduling noise.
- Closed-loop load (think time) ties RPS to active users and latency.
- Stale-permission check: every `CHECK viewer write -> 403` and `CHECK editor write -> 201` verifies that role modifications immediately invalidate permissions in cache (0 stale reads permitted).

---

## Results

**Run Specifications:** 3 runs × 120s per mode @ 250 concurrent virtual users (~95 000 total requests).

### Aggregate Performance (Median [min..max] over 3 runs)

| Metric | Cache ON (Redis) | Cache OFF (PostgreSQL only) | Impact / Difference |
|---|:---:|:---:|:---:|
| **RPS (Throughput)** | **144.4 [144.2 .. 144.5]** | 123.9 [122.6 .. 124.7] | **+16.5% higher throughput** |
| **p50 Latency** | **22.0 ms [22 .. 23]** | 180.0 ms [140 .. 190] | **8.2× faster (88% reduction)** |
| **p95 Latency** | **120.0 ms [110 .. 130]** | 880.0 ms [830 .. 940] | **7.3× faster** |
| **p99 Latency** | **410.0 ms [390 .. 450]** | 1200.0 ms [1100 .. 1300] | **2.9× faster** |
| **SQL Calls / Request** | **3.25 [3.25 .. 3.29]** | 7.93 [7.93 .. 7.94] | **-59% database load offloaded** |
| **Redis Keyspace Hits / Misses** | ~43 200 / ~38 100 | 0 / ~29 600 | **~53% cache hit ratio on mixed traffic** |
| **Success Rate** | **99.97%** (15 / 51 300) | **99.99%** (4 / 44 500) | Enterprise grade stability |

### Per-Endpoint Comparison (Median p50 / p95)

| Endpoint | Method | Cache ON (p50 / p95) | Cache OFF (p50 / p95) | Acceleration |
|---|:---:|:---:|:---:|:---:|
| User Profile (`/users/me`) | `GET` | **11 ms / 58 ms** | 110 ms / 730 ms | **10.0× faster** |
| Project Members (`/projects/{id}/members`) | `GET` | **19 ms / 99 ms** | 190 ms / 860 ms | **10.0× faster** |
| Project Tasks (`/tasks/`) | `GET` | **26 ms / 140 ms** | 210 ms / 920 ms | **8.0× faster** |
| Role Check Before / After | `GET` | **17–22 ms / 78–99 ms** | 66–110 ms / 460–770 ms | **5.0× faster** |
| Create Task (Write) | `POST` | **62 ms / 150 ms** | 210 ms / 900 ms | **3.4× faster** (DB pool freed from reads) |
| Change Member Role (Write) | `PATCH` | **62 ms / 120 ms** | 130 ms / 660 ms | **2.1× faster** |
| Permission Verification | `POST` | **57–60 ms / 110 ms** | 100–110 ms / 570–580 ms | **1.8× faster** |

---

## Failure Analysis & Root Cause Diagnosis

During stress testing across 95 000+ requests under 200–250 concurrent users:

1. **Client Socket Resets (`fail=1` / `fail=2`, `Unexpected status: 0`):**
   - **Occurrences:** 1 in CACHE_ON run 1, 1 in run 2; 1 in CACHE_OFF run 1, 2 in run 2, 1 in run 3 (~0.01% of requests).
   - **Cause:** Client-side network socket drop in Locust when Uvicorn's single-process event loop momentarily reached OS listen backlog limits during ramp-up spikes. Completely normal for a single-worker container under 200+ users.

2. **Redis Connection Pool Exhaustion (`fail=13` in CACHE_ON run 3):**
   - **Occurrences:** Exactly 13 requests failed with HTTP 503 at timestamp `12:07:06Z` (the exact second Locust hit peak 250 concurrent users).
   - **Root Cause:** Redis pool had `max_connections=50`. In `redis.asyncio`, when 50 connections are simultaneously leased, `get_available_connection()` immediately raises `MaxConnectionsError: Too many connections` without queuing. In `get_user_credentials`, `check_banned_tokens` did not have a fallback handler, bubbling 503 to FastAPI.
   - **Verification:** Database pool (`max_overflow=15`, `pool_timeout=30s`) never timed out (maximum response time was only 1.07s). Once users staggered across random wait intervals (0.5–2s), 0 additional errors occurred for the remaining 85 seconds.
   - **Remediation & Security Decision:** 
     1. **Preserved Fail-Closed Invariant:** `check_banned_tokens` intentionally remains fail-closed (no bypass on Redis failure). In a production security model, allowing requests through when the token blacklist cannot be verified would open an attack window after account compromise or `logout-everywhere`.
     2. **Connection Pool Sizing:** Bumped `redis_max_connections` to 100 in `core/config.py` and `database/redis_config.py` to provide sufficient connection capacity for 200+ concurrent clients without saturating the pool.
