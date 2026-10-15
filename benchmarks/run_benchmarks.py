"""Automated Cache ON/OFF benchmark.

Runs the API against a dedicated disposable database (benchmarks/docker-compose.bench.yaml),
never against the main/test DB. Settings are passed through environment variables;
the project's .env file is never modified.

Usage: python benchmarks/run_benchmarks.py [--users 35] [--duration 60] [--runs 5]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
import httpx
import redis

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.config import settings  # noqa: E402

REPORTS_DIR = os.path.join(PROJECT_ROOT, "benchmarks", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

COMPOSE = [
    "docker", "compose",
    "-f", "docker-compose.yaml",
    "-f", "benchmarks/docker-compose.bench.yaml",
]
BENCH_DB_URL = "postgresql+asyncpg://bench:bench@127.0.0.1:5434/bench_db"
BENCH_CONTAINER = "ProjectBenchDB"


def compose(*args, env=None):
    subprocess.run([*COMPOSE, *args], cwd=PROJECT_ROOT, env=env, check=True)


def psql(sql: str) -> str:
    res = subprocess.run(
        ["docker", "exec", BENCH_CONTAINER, "psql", "-U", "bench", "-d", "bench_db", "-At", "-c", sql],
        capture_output=True, text=True, check=True,
    )
    return res.stdout.strip()


def seed_database():
    env = {**os.environ, "PYTHONPATH": ".", "BENCH_DATABASE_URL": BENCH_DB_URL}
    subprocess.run([sys.executable, "benchmarks/seed.py"], cwd=PROJECT_ROOT, env=env, check=True)


def restart_api_and_wait(enable_caching: bool):
    env = {
        **os.environ,
        "ENABLE_CACHING": "true" if enable_caching else "false",
        "ENABLE_GLOBAL_RATE_LIMIT": "false",
    }
    print(f"[runner] Recreating API (ENABLE_CACHING={env['ENABLE_CACHING']})...")
    compose("up", "-d", "--force-recreate", "--no-deps", "api", env=env)
    for _ in range(60):
        try:
            if httpx.get("http://localhost:8000/health", timeout=2.0).status_code == 200:
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError("API failed to become healthy")


def parse_locust_stats(csv_prefix: str) -> dict:
    endpoints, aggregated = {}, {}
    with open(f"{csv_prefix}_stats.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            data = {
                "type": row["Type"],
                "name": row["Name"],
                "requests": int(row["Request Count"]),
                "failures": int(row["Failure Count"]),
                "rps": float(row["Requests/s"]),
                "p50": float(row["50%"]),
                "p95": float(row["95%"]),
                "p99": float(row["99%"]),
                "max": float(row["Max Response Time"]),
            }
            if row["Name"] == "Aggregated":
                aggregated = data
            else:
                endpoints[f"{row['Type']} {row['Name']}"] = data
    return {"aggregated": aggregated, "endpoints": endpoints}


def run_cycle(mode: str, run_num: int, users: int, duration: int, r: redis.Redis) -> dict:
    r.flushall()
    r.config_resetstat()
    psql("SELECT pg_stat_statements_reset();")

    prefix = os.path.join(REPORTS_DIR, f"{mode}_run{run_num}")
    cmd = [
        "locust", "-f", "benchmarks/locustfile.py", "--headless",
        "-u", str(users), "-r", "10", "--run-time", f"{duration}s",
        "--host", "http://localhost:8000", "--csv", prefix,
    ]
    print(f"[runner] {mode} run {run_num}: {users} users, {duration}s")
    subprocess.run(cmd, cwd=PROJECT_ROOT)

    info = r.info("stats")
    hits, misses = info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
    sql_calls = int(psql(
        "SELECT coalesce(sum(calls),0) FROM pg_stat_statements "
        "WHERE dbid = (SELECT oid FROM pg_database WHERE datname = 'bench_db') "
        "AND query NOT ILIKE '%pg_stat_statements%';"
    ) or 0)

    stats = parse_locust_stats(prefix)
    total = stats["aggregated"]["requests"] or 1
    stats["redis"] = {"keyspace_hits": hits, "keyspace_misses": misses}
    stats["sql"] = {"calls": sql_calls, "calls_per_request": round(sql_calls / total, 2)}
    stats["mode"], stats["run"] = mode, run_num
    agg = stats["aggregated"]
    print(f"[runner]   RPS={agg['rps']:.1f} p50={agg['p50']}ms p95={agg['p95']}ms "
          f"p99={agg['p99']}ms failures={agg['failures']} sql/req={stats['sql']['calls_per_request']}")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=35)
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()

    r = redis.Redis(host="localhost", port=6379, password=settings.redis_password)
    results = {"cache_on": [], "cache_off": []}

    try:
        compose("up", "-d", "--wait", "bench_db", "redis")
        psql("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")

        for mode, enabled in (("cache_on", True), ("cache_off", False)):
            print(f"\n>>> MODE: {mode}")
            seed_database()          # fresh data + fresh tokens for every mode
            restart_api_and_wait(enabled)
            subprocess.run(  # warmup, not recorded
                ["locust", "-f", "benchmarks/locustfile.py", "--headless", "-u", "10", "-r", "10",
                 "--run-time", "5s", "--host", "http://localhost:8000"],
                cwd=PROJECT_ROOT, capture_output=True,
            )
            for i in range(1, args.runs + 1):
                results[mode].append(run_cycle(mode, i, args.users, args.duration, r))
    finally:
        # Restore the default (cache on, no bench DB) API container.
        subprocess.run(["docker", "compose", "up", "-d", "--force-recreate", "--no-deps", "api"],
                       cwd=PROJECT_ROOT)

    path = os.path.join(REPORTS_DIR, "benchmark_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[runner] Summary written to {path}")


if __name__ == "__main__":
    main()
