import os, sys
from pathlib import Path
import urllib.request
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles # <-- Add this import
from pydantic import BaseModel
import engine

app = FastAPI(title="Vantage Grid")

# Mount the static directory so HTML can load images
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "static")), name="static")

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

def page(name):
    def view(request: Request):
        is_staff = request.cookies.get("staff_token") == "valid_session"
        if request.url.path.startswith("/staff") and not is_staff:
            return RedirectResponse(url="/login", status_code=303)
        return templates.TemplateResponse(request, name, {"active": request.url.path, "is_staff": is_staff})
    return view

for path, tpl in {"/": "home.html", "/civilian/map": "map.html", "/civilian/register": "register.html",
                  "/civilian/checkin": "checkin.html", "/staff/dashboard": "dashboard.html",
                  "/staff/rehearsal": "rehearsal.html", "/how": "how.html", "/about": "about.html",
                  "/privacy": "privacy.html", "/login": "login.html"}.items():
    app.add_api_route(path, page(tpl), response_class=HTMLResponse, include_in_schema=False)

CONTEXT = dict(zones={z: v[:2] for z, v in engine.ZONES.items()}, river=engine.RIVER, roads=engine.ROADS, depots=engine.DEPOTS, shelters=engine.SHELTERS)

@app.get("/api/context")
def context():
    return CONTEXT

@app.get("/api/state")
def state(level: int = 30, rate: float = .4, outage: float = 20, cellular: float = 0, boats: int = 3):
    return engine.run(level, rate, outage, cellular, boats)

@app.get("/api/rehearsal")
def rehearsal(level: int = 70, rate: float = 1.2, outage: float = 60, cellular: float = 0, boats: int = 3):
    return engine.rehearse(level, rate, outage, cellular, boats)

@app.get("/api/telemetry")
def telemetry():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=24.88&longitude=67.03&current_weather=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'VantageGrid-Triage/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            cw = data.get("current_weather", {})
            wind = cw.get("windspeed", 0)
            temp = cw.get("temperature", 0)
            calc_level = min(95, max(30, int(30 + (wind * 1.5))))
            return {"ok": True, "source": "Open-Meteo Live", "location": "Karachi", "temperature": temp, "windspeed": wind, "calculated_level": calc_level}
    except Exception as e:
        return {"ok": False, "error": str(e), "calculated_level": 45}

class LoginRequest(BaseModel):
    passcode: str

@app.post("/api/login")
def login(req: LoginRequest):
    if req.passcode == "REMA2026":
        response = JSONResponse({"ok": True})
        response.set_cookie(key="staff_token", value="valid_session", httponly=True, max_age=86400)
        return response
    return {"ok": False}

@app.get("/api/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("staff_token")
    return response

class Reg(BaseModel):
    name: str
    zone: str
    address: str = ""
    phone: str = ""
    people: int = 1
    floor: int = 0
    oxygen: bool = False
    mobility: bool = False
    elderly: bool = False
    alone: bool = False
    devices: str = ""

@app.post("/api/register")
def register(r: Reg):
    kind = "life" if r.oxygen else "elderly" if r.elderly or r.mobility else "healthy"
    lat, lng, terr, _ = engine.ZONES.get(r.zone, engine.ZONES["Lyari"])
    
    households = engine.get_households()
    hid = max([h["id"] for h in households], default=0) + 1
    
    new_h = dict(id=hid, name=r.name, zone=r.zone, address=r.address, phone=r.phone, lat=lat, lng=lng, terrain=terr, floor=r.floor,
                 people=r.people, kind=kind, alone=r.alone, registered=True, checked_in=True,
                 silent=False, safe=False, conf=70, bonus=0)
    engine.add_household(new_h)
    return {"id": hid}

class Check(BaseModel):
    id: int
    status: str
    bonus: int = 0

@app.post("/api/checkin")
def checkin(c: Check):
    households = engine.get_households()
    for h in households:
        if h["id"] == c.id:
            h["checked_in"], h["silent"], h["safe"] = True, False, c.status == "safe"
            h["bonus"] = c.bonus
            engine.update_household(h)
            return {"ok": True}
    return {"ok": False}

@app.get("/api/recover")
def recover(phone: str):
    clean_phone = "".join(filter(str.isalnum, phone))
    for h in engine.get_households():
        if h.get("phone") and "".join(filter(str.isalnum, h["phone"])) == clean_phone:
            masked_name = h["name"][:2] + "***" if len(h["name"]) > 2 else "***"
            return {"ok": True, "id": h["id"], "mask": masked_name}
    return {"ok": False}

@app.get("/api/households")
def households():
    return [dict(id=h["id"], name=h["name"], zone=h["zone"]) for h in engine.get_households()]

@app.get("/api/health")
def health():
    return {"ok": True, "households": len(engine.get_households())}