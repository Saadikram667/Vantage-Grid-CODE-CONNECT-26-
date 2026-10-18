"""Run after `pip install -r requirements.txt httpx`:  python smoke_test.py"""
from fastapi.testclient import TestClient
from api.index import app
c = TestClient(app)
for p in ["/", "/how", "/civilian/map", "/civilian/register", "/civilian/checkin", "/staff/dashboard", "/staff/rehearsal",
          "/api/context", "/api/state?level=80", "/api/rehearsal?level=70", "/api/households", "/api/health"]:
    r = c.get(p); assert r.status_code == 200, (p, r.status_code); print("ok", p)
rid = c.post("/api/register", json={"name": "Test", "zone": "Riverbend", "floor": 1, "oxygen": True}).json()["id"]
assert c.post("/api/checkin", json={"id": rid, "status": "safe"}).json()["ok"]
print("all good")
