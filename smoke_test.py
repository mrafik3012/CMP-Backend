"""
API smoke test — run while backend is running on localhost:8000
Usage: python smoke_test.py
"""
import requests

BASE = "http://localhost:8000/api/v1"
results = []

def test(label, fn, expect=200):
    try:
        r = fn()
        ok = r.status_code == expect
        results.append((label, ok, r.status_code))
        print(f"  {'✅' if ok else '❌'} {label} → {r.status_code} (expected {expect})")
        return r
    except Exception as e:
        results.append((label, False, str(e)))
        print(f"  ❌ {label} → {e}")
        return None

def login(email, password):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

def H(token):
    return {"Authorization": f"Bearer {token}"}

# ─────────────────────────────────────────
print("\n🔐 AUTH — Admin Login")
admin_token = login("admin@example.com", "Admin123!")
print(f"  Token: {admin_token[:30]}..." if admin_token else "  ❌ Login failed")
ah = H(admin_token) if admin_token else {}

print("\n👤 USERS")
test("GET /auth/me", lambda: requests.get(f"{BASE}/auth/me", headers=ah))
test("GET /users",   lambda: requests.get(f"{BASE}/users", headers=ah))

print("\n🏗️  PROJECTS")
r2 = test("GET /projects", lambda: requests.get(f"{BASE}/projects", headers=ah))
pid = None
if r2 and r2.status_code == 200 and r2.json():
    pid = r2.json()[0]["id"]
    print(f"  Using project ID: {pid}")

if pid:
    print("\n📋 PROJECT DETAIL")
    test(f"GET /projects/{pid}",              lambda: requests.get(f"{BASE}/projects/{pid}", headers=ah))
    test(f"GET /projects/{pid}/tasks",        lambda: requests.get(f"{BASE}/projects/{pid}/tasks", headers=ah))
    test(f"GET /projects/{pid}/budget",       lambda: requests.get(f"{BASE}/projects/{pid}/budget", headers=ah))
    test(f"GET /projects/{pid}/change-orders",lambda: requests.get(f"{BASE}/projects/{pid}/change-orders", headers=ah))
    test(f"GET /projects/{pid}/logs",         lambda: requests.get(f"{BASE}/projects/{pid}/logs", headers=ah))
    test(f"GET /projects/{pid}/rfis",         lambda: requests.get(f"{BASE}/projects/{pid}/rfis", headers=ah))
    test(f"GET /projects/{pid}/punch-list",   lambda: requests.get(f"{BASE}/projects/{pid}/punch-list", headers=ah))
    test(f"GET /projects/{pid}/checklists",   lambda: requests.get(f"{BASE}/projects/{pid}/checklists", headers=ah))
    test(f"GET /projects/{pid}/documents",    lambda: requests.get(f"{BASE}/projects/{pid}/documents", headers=ah))

print("\n🔧 RESOURCES")
test("GET /resources/workers",   lambda: requests.get(f"{BASE}/resources/workers", headers=ah))
test("GET /resources/equipment", lambda: requests.get(f"{BASE}/resources/equipment", headers=ah))

print("\n🔔 NOTIFICATIONS")
test("GET /notifications", lambda: requests.get(f"{BASE}/notifications", headers=ah))

print("\n📊 REPORTS")
test("GET /audit-log", lambda: requests.get(f"{BASE}/audit-log", headers=ah))

# ─────────────────────────────────────────
print("\n\n👷 ROLE-BASED ACCESS TESTS")

roles = [
    ("Project Manager", "pm@infraura.com",       "Test@1234"),
    ("Site Engineer",   "engineer@infraura.com",  "Test@1234"),
    ("Viewer",          "viewer@infraura.com",    "Test@1234"),
]

for role_name, email, pwd in roles:
    print(f"\n  🔑 {role_name} ({email})")
    tok = login(email, pwd)
    if not tok:
        print(f"    ❌ Login failed — check password for {email}")
        continue
    rh = H(tok)
    # All roles should read projects
    test(f"  [{role_name}] GET /projects",      lambda rh=rh: requests.get(f"{BASE}/projects", headers=rh))
    test(f"  [{role_name}] GET /auth/me",        lambda rh=rh: requests.get(f"{BASE}/auth/me", headers=rh))
    # Only Admin should access /users — others expect 403
    expected = 200 if "Admin" in role_name else 403
    test(f"  [{role_name}] GET /users",          lambda rh=rh: requests.get(f"{BASE}/users", headers=rh), expect=expected)
    # Only Admin should access audit-log — others expect 403
    test(f"  [{role_name}] GET /audit-log",      lambda rh=rh: requests.get(f"{BASE}/audit-log", headers=rh), expect=expected)

# ─────────────────────────────────────────
print("\n\n🧪 EDGE CASE TESTS")

print("\n  🔒 No token (expect 401)")
test("GET /projects (no token)",  lambda: requests.get(f"{BASE}/projects"), expect=401)
test("GET /users (no token)",     lambda: requests.get(f"{BASE}/users"), expect=401)

print("\n  🚫 Invalid token (expect 401)")
bad = H("invalidtoken123")
test("GET /projects (bad token)", lambda: requests.get(f"{BASE}/projects", headers=bad), expect=401)

print("\n  🔍 Non-existent resources (expect 404)")
test("GET /projects/99999",       lambda: requests.get(f"{BASE}/projects/99999", headers=ah), expect=404)
test("GET /projects/99999/tasks", lambda: requests.get(f"{BASE}/projects/99999/tasks", headers=ah), expect=404)

print("\n  🚫 Invalid login credentials (expect 401)")
test("POST /auth/login (wrong pw)", lambda: requests.post(f"{BASE}/auth/login",
    json={"email": "admin@example.com", "password": "wrongpassword"}), expect=401)
test("POST /auth/login (no user)",  lambda: requests.post(f"{BASE}/auth/login",
    json={"email": "ghost@example.com", "password": "whatever"}), expect=401)

# ─────────────────────────────────────────
print("\n" + "="*50)
passed = sum(1 for _, ok, _ in results if ok)
total  = len(results)
print(f"  Result: {passed}/{total} passed")
if passed == total:
    print("  🎉 All tests passed!")
else:
    print("  ⚠️  Failed tests:")
    for label, ok, code in results:
        if not ok:
            print(f"     ❌ {label} → {code}")