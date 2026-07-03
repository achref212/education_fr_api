"""
End-to-end API test — runs its own server subprocess.

Steps:
  1. Admin login
  2. Admin creates school  → chaabaniachref212@gmail.com
  3. School login
  4. School creates prof   → chaabaniachref00@gmail.com
  5. Prof login
  6. Student registers     → achref.chaabani@esprit.tn
  7. Extract activation code from server stdout → activate account
  8. Student login + /auth/me
"""

import re
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
VENV = str(Path(__file__).parent / ".venv/bin/python3")
ADMIN_PASS = "Admin1234!"
SCHOOL_EMAIL = "chaabaniachref212@gmail.com"
PROF_EMAIL = "chaabaniachref00@gmail.com"
STUDENT_EMAIL = "achref.chaabani@esprit.tn"
STUDENT_PASS = "Test1234!"

SEP = "─" * 60


def step(label: str) -> None:
    print(f"\n{'='*3} {label}")


def ok(resp: requests.Response, label: str) -> dict:
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    if resp.status_code >= 400:
        print(f"  ✗ [{resp.status_code}] {label}")
        print(f"  {data}")
        sys.exit(1)
    print(f"  ✓ [{resp.status_code}] {label}")
    return data


# ── Kill any leftover server on port 8000 ─────────────────────────────────────
subprocess.run(
    ["bash", "-c", "lsof -ti tcp:8000 | xargs kill -9 2>/dev/null; true"],
    capture_output=True,
)
time.sleep(1)

# ── Start server ──────────────────────────────────────────────────────────────
step("Starting API server")
env = {**__import__("os").environ, "PYTHONUNBUFFERED": "1"}
server = subprocess.Popen(
    [VENV, "-m", "uvicorn", "app.main:app", "--port", "8000"],
    cwd=Path(__file__).parent,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
    env=env,
)

server_lines: list[str] = []

def collect(timeout: float = 6.0, stop_on: str = "") -> None:
    """Drain server stdout for `timeout` seconds."""
    import select
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            readable, _, _ = select.select([server.stdout], [], [], 0.05)
            if readable:
                line = server.stdout.readline()
                if line:
                    server_lines.append(line.rstrip())
                    if stop_on and stop_on.lower() in line.lower():
                        return
        except Exception:
            time.sleep(0.05)

collect(8, stop_on="startup complete")
print(f"  server_lines collected: {len(server_lines)}")

# Quick health check
try:
    h = requests.get(f"{BASE}/health", timeout=5)
    print(f"  /health → {h.status_code}")
except Exception as e:
    print(f"  /health failed: {e}")
    server.terminate()
    sys.exit(1)


# ── 1. Admin login ────────────────────────────────────────────────────────────
step("1 · Admin login")
resp = requests.post(f"{BASE}/auth/login",
                     json={"email": "admin@test.com", "password": ADMIN_PASS})
d = ok(resp, "admin login")
admin_token = d.get("accessToken") or d.get("access_token", "")
print(f"  role={d.get('role')}  token={bool(admin_token)}")
print(f"  keys={list(d.keys())}")
ADM = {"Authorization": f"Bearer {admin_token}"}


# ── 2. Admin creates school ───────────────────────────────────────────────────
step("2 · Admin creates school")
resp = requests.post(f"{BASE}/admin/schools",
    json={
        "name": "École Sana",
        "email": SCHOOL_EMAIL,
        "address": "12 Rue de la Liberté",
        "city": "Tunis",
        "postalCode": "1000",
        "phone": "+21671000001",
        "directorName": "Achref Chaabani",
    },
    headers=ADM,
)
sd = ok(resp, "create school")
school_id = (sd.get("school") or {}).get("id") or sd.get("id")
school_pass = sd.get("plainPassword", "")
print(f"  school_id  = {school_id}")
print(f"  plain_pass = {school_pass!r}")


# ── 3. School login ───────────────────────────────────────────────────────────
step("3 · School login")
resp = requests.post(f"{BASE}/auth/login",
                     json={"email": SCHOOL_EMAIL, "password": school_pass})
sl = ok(resp, "school login")
school_token = sl.get("accessToken") or sl.get("access_token", "")
print(f"  role={sl.get('role')}  token={bool(school_token)}")
SCH = {"Authorization": f"Bearer {school_token}"}


# ── 4. School creates professor ───────────────────────────────────────────────
step("4 · School creates professor")
resp = requests.post(f"{BASE}/school/professors",
    json={
        "email": PROF_EMAIL,
        "firstName": "Achref",
        "lastName": "Chaabani",
        "level": "advanced",
    },
    headers=SCH,
)
pd = ok(resp, "create professor")
prof_pass = pd.get("plainPassword", "")
print(f"  prof_email = {PROF_EMAIL}")
print(f"  plain_pass = {prof_pass!r}")


# ── 5. Prof login ─────────────────────────────────────────────────────────────
step("5 · Prof login")
resp = requests.post(f"{BASE}/auth/login",
                     json={"email": PROF_EMAIL, "password": prof_pass})
pl = ok(resp, "prof login")
prof_token = pl.get("accessToken") or pl.get("access_token", "")
print(f"  role={pl.get('role')}  token={bool(prof_token)}")


# ── 6. Student registers ──────────────────────────────────────────────────────
step("6 · Student self-registers")
collect(1)  # drain any leftover logs before the register call
prev_lines = len(server_lines)

resp = requests.post(f"{BASE}/auth/register",
    json={
        "email": STUDENT_EMAIL,
        "password": STUDENT_PASS,
        "firstName": "Achref",
        "lastName": "Chaabani",
        "level": "5eme",
        "classLevel": "5ème année",
        "schoolId": school_id,
        "phone": "+21698000001",
        "dateOfBirth": "2010-03-15",
    },
)
rd = ok(resp, "register student")
state_token = rd.get("registrationStateToken") or rd.get("registration_state_token", "")
print(f"  state_token = {bool(state_token)}")

# Collect server output that contains the activation code (console email sender)
# The logger.warning line appears after the HTTP response is returned, so wait a bit
collect(5, stop_on="activation code")
new_lines = server_lines[prev_lines:]
code_match = None
for line in new_lines:
    m = re.search(r"Activation code.*?:\s*([0-9]{6})", line, re.IGNORECASE)
    if not m:
        m = re.search(r"\b([0-9]{6})\b", line)
    if m:
        code_match = m.group(1)
        break

if code_match:
    print(f"  activation_code found in server log = {code_match}")
else:
    print("  ⚠  No activation code found in server log.")
    print("  Server output (last 20 lines):")
    for l in server_lines[-20:]:
        print(f"    {l}")
    server.terminate()
    sys.exit(0)


# ── 7. Verify / activate student ─────────────────────────────────────────────
step("7 · Activate student account")
resp = requests.post(f"{BASE}/auth/verify-registration",
    json={
        "email": STUDENT_EMAIL,
        "code": code_match,
        "registration_state_token": state_token,
    },
)
vd = ok(resp, "activate student")
student_token = vd.get("accessToken") or vd.get("access_token", "")
print(f"  token={bool(student_token)}")


# ── 8. Student login ──────────────────────────────────────────────────────────
step("8 · Student login")
resp = requests.post(f"{BASE}/auth/login",
                     json={"email": STUDENT_EMAIL, "password": STUDENT_PASS})
stu_login = ok(resp, "student login")
print(f"  role={stu_login.get('role')}")


# ── 9. Student /auth/me ───────────────────────────────────────────────────────
step("9 · Student profile (/auth/me)")
resp = requests.get(f"{BASE}/auth/me",
                    headers={"Authorization": f"Bearer {student_token}"})
me = ok(resp, "/auth/me")
print(f"  firstName    = {me.get('firstName')}")
print(f"  lastName     = {me.get('lastName')}")
print(f"  email        = {me.get('email')}")
print(f"  phone        = {me.get('phone')}")
print(f"  dateOfBirth  = {me.get('dateOfBirth')}")
print(f"  classLevel   = {me.get('classLevel')}")
print(f"  schoolId     = {me.get('schoolId')}")
print(f"  role         = {me.get('role')}")

print(f"\n{SEP}")
print("All steps completed successfully ✓")
print(SEP)

server.terminate()
