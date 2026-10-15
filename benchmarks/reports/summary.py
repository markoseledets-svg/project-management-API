import json
import statistics as st

with open("benchmarks/reports/benchmark_summary.json", encoding="utf-8") as f:
    d = json.load(f)


def med(mode, getter):
    return st.median(getter(r) for r in d[mode])


def spread(mode, getter):
    vals = [getter(r) for r in d[mode]]
    return min(vals), max(vals)


print("=== PER RUN ===")
for mode in ("cache_on", "cache_off"):
    print(f"\n{mode.upper()}")
    for r in d[mode]:
        a = r["aggregated"]
        print(f"  run {r['run']}: RPS={a['rps']:.1f} p50={a['p50']:.0f} p95={a['p95']:.0f} "
              f"p99={a['p99']:.0f} fail={a['failures']} sql/req={r['sql']['calls_per_request']} "
              f"redis hits/misses={r['redis']['keyspace_hits']}/{r['redis']['keyspace_misses']}")

print("\n=== MEDIAN [min..max] OVER RUNS ===")
for mode in ("cache_on", "cache_off"):
    for key in ("p50", "p95", "p99"):
        def get_stat(r, k=key):
            return r["aggregated"][k]
        lo, hi = spread(mode, get_stat)
        print(f"{mode:9} {key}: {med(mode, get_stat):6.1f} ms  [{lo:.0f}..{hi:.0f}]")
    def get_sql(r):
        return r["sql"]["calls_per_request"]
    print(f"{mode:9} SQL calls/request: {med(mode, get_sql):.2f}")

print("\n=== PER ENDPOINT (median p50 / p95) ===")
names = sorted({k for m in d for r in d[m] for k in r["endpoints"]})
for ep in names:
    row = []
    for mode in ("cache_on", "cache_off"):
        p50 = st.median(r["endpoints"].get(ep, {}).get("p50", 0) for r in d[mode])
        p95 = st.median(r["endpoints"].get(ep, {}).get("p95", 0) for r in d[mode])
        row.append(f"{mode}: {p50:.0f}/{p95:.0f}ms")
    print(f"{ep:32} " + " | ".join(row))
