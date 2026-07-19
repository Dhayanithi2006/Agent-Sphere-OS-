import requests

print("=== BACKEND ===")
checks = [
    ("GET",  "/supervisor",              None),
    ("GET",  "/processes",               None),
    ("GET",  "/agents",                  None),
    ("GET",  "/api/showrunner/status",   None),
    ("POST", "/api/showrunner/generate", {"movie_goal":"Test","type":"Short Film","user":"User"}),
    ("POST", "/kernel/execute",          {"task":"Write hello world","workflow":"coding"}),
]
for method, path, body in checks:
    try:
        if method == "GET":
            r = requests.get("http://localhost:8000" + path, timeout=8)
        else:
            r = requests.post("http://localhost:8000" + path, json=body, timeout=8)
        status = "PASS" if r.status_code == 200 else "FAIL"
        print(f"  {status} [{r.status_code}] {method} {path}")
    except Exception as e:
        print(f"  FAIL [ERR] {method} {path}: {str(e)[:50]}")

print()
print("=== FRONTEND ===")
pages = ["/", "/dashboard", "/showrunner", "/processes", "/agents",
         "/memory", "/checkpoints", "/analytics", "/scheduler", "/recovery"]
for p in pages:
    try:
        r = requests.get("http://localhost:3000" + p, timeout=8)
        status = "PASS" if r.status_code == 200 else "FAIL"
        print(f"  {status} [{r.status_code}] {p}")
    except Exception as e:
        print(f"  FAIL [ERR] {p}: {str(e)[:40]}")
