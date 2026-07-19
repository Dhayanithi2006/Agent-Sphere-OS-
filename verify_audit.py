import requests
import sqlite3
import os

BASE = "http://127.0.0.1:8000"

# ── Phase 4: kernel/execute ──────────────────────────────────────────────────
print("=== PHASE 4: KERNEL EXECUTE ===")
try:
    r = requests.post(BASE + "/kernel/execute",
                      json={"task": "Write a Python function to add two numbers", "workflow": "coding"},
                      timeout=90)
    print("Status:", r.status_code)
    if r.status_code == 200:
        out = str(r.json().get("output", ""))[:150]
        print("Output:", out)
        print("RESULT: PASS")
    else:
        print("Body:", r.text[:200])
        print("RESULT: FAIL")
except Exception as e:
    print("ERR:", e)
    print("RESULT: FAIL")

# ── Phase 5: Process lifecycle ───────────────────────────────────────────────
print()
print("=== PHASE 5: PROCESS LIFECYCLE ===")
r = requests.get(BASE + "/processes", timeout=5)
procs = r.json()
print("Active processes:", len(procs))
for p in procs:
    pid = p.get("process_id")
    status = p.get("status")
    name = p.get("name", "")
    print("  PID=" + str(pid) + " status=" + str(status) + " name=" + str(name))

# ── Phase 6: Recovery endpoint ───────────────────────────────────────────────
print()
print("=== PHASE 6: RECOVERY ===")
r6 = requests.post(BASE + "/recovery?task_id=nonexistent_task_999", timeout=5)
print("Recovery on unknown task:", r6.status_code, "(expected 404, not 500)")
print("RESULT:", "PASS" if r6.status_code != 500 else "FAIL")

# ── Phase 7: Checkpoint DB ───────────────────────────────────────────────────
print()
print("=== PHASE 7: CHECKPOINT DB ===")
db_path = r"d:\Desktop\Hackathon\Agent-Sphere OS\checkpoints.sqlite"
size_mb = os.path.getsize(db_path) / (1024 * 1024)
conn = sqlite3.connect(db_path)
count = conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0]
row = conn.execute("SELECT AVG(LENGTH(state)), MAX(LENGTH(state)) FROM checkpoints").fetchone()
conn.close()
avg_kb = row[0] / 1024 if row[0] else 0
max_kb = row[1] / 1024 if row[1] else 0
print("DB size: " + str(round(size_mb, 1)) + " MB")
print("Row count: " + str(count) + " (max allowed: 500)")
print("Avg state size: " + str(round(avg_kb, 1)) + " KB")
print("Largest state: " + str(round(max_kb, 1)) + " KB")
print("Retention: " + ("OK" if count <= 500 else "OVER LIMIT"))

# ── Phase 9: Shared memory ───────────────────────────────────────────────────
print()
print("=== PHASE 9: SHARED MEMORY ===")
r_write = requests.post(BASE + "/memory",
                        json={"namespace": "_test", "key": "k1", "value": "hello_audit"},
                        timeout=5)
r_read = requests.get(BASE + "/memory/k1?namespace=_test", timeout=5)
val = r_read.json().get("value") if r_read.status_code == 200 else None
print("Write->Read: " + ("PASS" if val == "hello_audit" else "FAIL") + " (got: " + str(val) + ")")

# ── Phase 11: Full API matrix ────────────────────────────────────────────────
print()
print("=== PHASE 11: API ENDPOINT MATRIX ===")
endpoints = [
    ("GET", "/"),
    ("GET", "/status"),
    ("GET", "/agents"),
    ("GET", "/tasks"),
    ("GET", "/processes"),
    ("GET", "/memory"),
    ("GET", "/events"),
    ("GET", "/checkpoints"),
    ("GET", "/dependencies"),
    ("GET", "/diagnostics"),
    ("GET", "/supervisor"),
    ("GET", "/dashboard"),
    ("GET", "/stream?once=true"),
    ("GET", "/api/showrunner/status"),
    ("GET", "/api/marketplace"),
    ("GET", "/api/metrics"),
    ("GET", "/api/assets"),
    ("GET", "/api/benchmarks"),
    ("POST", "/memory"),
]
passed = 0
failed = 0
for method, path in endpoints:
    try:
        if method == "GET":
            resp = requests.get(BASE + path, timeout=10)
        else:
            resp = requests.post(BASE + path,
                                 json={"namespace": "test", "key": "x", "value": "1"},
                                 timeout=10)
        ok = resp.status_code < 400
        sym = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print("  " + sym + " [" + str(resp.status_code) + "] " + method + " " + path)
    except Exception as e:
        failed += 1
        print("  FAIL [ERR] " + method + " " + path + ": " + str(e)[:60])

print()
print("API RESULT: " + str(passed) + " PASSED / " + str(failed) + " FAILED")
