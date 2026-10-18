"""Last Hour priority engine: survival clock, uncertainty, severity, priority, rescue gap."""
import math, random, sqlite3, json, os, tempfile

# Authentic Karachi Topology
ZONES = {  
    "Lyari": (24.878, 67.010, 1.0, 1.00),          
    "Saddar": (24.855, 67.020, 1.5, 0.97),         
    "Liaquatabad": (24.900, 67.040, 3.0, 0.80),    
    "Gulshan-e-Iqbal": (24.915, 67.090, 9.0, 0.50) 
}

RIVER = [[24.960, 67.080], [24.910, 67.045], [24.880, 67.015], [24.850, 66.980]]
ROADS = [[[24.88,67.0],[24.895,67.03],[24.91,67.06]],[[24.88,67.0],[24.85,67.04]],[[24.895,67.03],[24.85,67.04]],[[24.86,66.98],[24.88,67.0],[24.9,67.02]],[[24.85,67.04],[24.84,67.07]]]

DEPOTS = {
    "A": (24.840, 66.980), 
    "B": (24.820, 67.040), 
    "C": (24.905, 67.165), 
    "D": (24.940, 67.180), 
    "H": (24.892, 67.074)  
}

SHELTERS = [
    ("Civil Hospital Relief", 24.860, 67.005), 
    ("Expo Centre (Safe Zone)", 24.893, 67.075), 
    ("National Stadium", 24.890, 67.080)
]

NAMES = ["Khan", "Baloch", "Syed", "Memon", "Sheikh", "Qureshi", "Rind", "Abbasi", "Ansari", "Bhatti",
         "Siddiqui", "Zardari", "Jokhio", "Kazi", "Soomro", "Chaudhry", "Raza", "Hussain", "Tariq", "Shah"]

DB_PATH = os.path.join(tempfile.gettempdir(), "households.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("CREATE TABLE IF NOT EXISTS households (id INTEGER PRIMARY KEY, data JSON)")
        if db.execute("SELECT COUNT(*) FROM households").fetchone()[0] == 0:
            rnd = random.Random(7)
            for i in range(30):
                z = list(ZONES)[i % 4] if i < 28 else "Lyari"
                lat, lng, terr, _ = ZONES[z]
                kind = "life" if i in (1, 9) else "elderly" if i % 7 == 2 else "chronic" if i % 5 == 3 else "healthy"
                h = dict(
                    id=i + 1, name=f"{NAMES[i % 20]} household", zone=z,
                    lat=lat + rnd.uniform(-.012, .012), lng=lng + rnd.uniform(-.012, .012),
                    terrain=terr + rnd.uniform(-.4, .6), floor=0 if rnd.random() < .7 else 1,
                    people=rnd.randint(1, 4), kind=kind, alone=rnd.random() < .25,
                    registered=i % 5 != 4 and i % 3 != 2 or i < 18, checked_in=rnd.random() < .5,
                    silent=rnd.random() < .2, safe=False, conf=rnd.randint(40, 95), bonus=0)
                if i >= 18:
                    h["registered"], h["checked_in"] = False, False
                db.execute("INSERT INTO households (id, data) VALUES (?, ?)", (h["id"], json.dumps(h)))

init_db()

def get_households():
    with get_db() as db:
        return [json.loads(r["data"]) for r in db.execute("SELECT data FROM households")]

def update_household(h):
    with get_db() as db:
        db.execute("UPDATE households SET data = ? WHERE id = ?", (json.dumps(h), h["id"]))

def add_household(h):
    with get_db() as db:
        db.execute("INSERT INTO households (id, data) VALUES (?, ?)", (h["id"], json.dumps(h)))

def zone_crisis(crisis):
    return {z: round(min(100, crisis * v[3])) for z, v in ZONES.items()}

def stage(c):
    return "Prepare" if c < 40 else "Watch" if c < 60 else "Warn" if c < 80 else "Dispatch"

def km(a, b):
    return math.hypot(a[0] - b[0], (a[1] - b[1]) * .91) * 111

def clock(h, crisis, rate, outage, cellular):
    zc = zone_crisis(crisis).get(h["zone"], zone_crisis(crisis)["Lyari"])
    water = -3.5 + 8.0 * zc / 100
    elev = h["terrain"] + .3 + 3.0 * h["floor"]
    rate = max(rate, .05)
    t_flood = max(8, (elev - water) / rate * 60)
    base = {"life": 240, "elderly": 900, "chronic": 1200, "healthy": 2880}[h["kind"]]
    t_med = base * (1 - outage / 350)
    t_therm = 1440 * (1 - outage / 120)
    t_sup = 2880 if h["registered"] else 1440
    
    base_tc = max(5, min(t_flood, t_med, t_therm, t_sup, 2880))
    tc = base_tc + h.get("bonus", 0)
    
    k = 1.0 if h["registered"] and h["checked_in"] else .8 if h["registered"] else .5
    
    # Feature 1: Cellular Outage Logic
    comms_lost = cellular >= 80
    if comms_lost:
        k = 0.5  # System loses contact, uncertainty drops to worst-case
        
    tc_eff = tc * (.6 + .4 * k)
    sev = {"life": 5, "elderly": 4, "chronic": 3, "healthy": 2}[h["kind"]]
    sev = min(5.0, sev + (.5 if h["alone"] else 0))
    p = .4 + .5 * h["conf"] / 100 if h["registered"] else .5
    p += .15 if h["silent"] or comms_lost else 0
    p -= .40 if h["safe"] else 0
    p = max(.02, min(1.0, p))
    pr = p * sev * 60 / max(tc_eff, 10)
    drivers = {"Floodwater": t_flood, "Medical": t_med, "Cold/heat": t_therm, "Supplies": t_sup}
    return dict(tc=round(tc, 1), tc_eff=round(tc_eff, 1), k=k, severity=sev, p=round(p, 2), priority=round(pr, 2),
                driver=min(drivers, key=drivers.get), flooded=water > h["terrain"] + .3, comms_lost=comms_lost,
                depth=round(max(0, water - h["terrain"]), 2), t_flood=round(t_flood), t_med=round(t_med))

def make_units(boats):
    # Feature 3: Added rigid capacities to units
    pts = list(DEPOTS.values())
    us = [dict(id=f"Boat {i+1}", type="boat", pos=pts[i % 4], speed=18, free=0, cap=6, pax=0) for i in range(boats)]
    us += [dict(id=f"Truck {i+1}", type="vehicle", pos=pts[(i + 1) % 4], speed=40, free=0, cap=15, pax=0) for i in range(2)]
    us.append(dict(id="Air 1", type="air", pos=DEPOTS["H"], speed=150, free=0, cap=2, pax=0))
    return us

def run(crisis=30, rate=.4, outage=20, cellular=0, boats=3, placements=None):
    households = get_households()
    rows = sorted(({**h, **clock(h, crisis, rate, outage, cellular)} for h in households), key=lambda r: -r["priority"])
    units = make_units(boats)
    
    for u in units:
        if placements and u["id"] in placements:
            u["pos"] = placements[u["id"]]
            
    for r in rows:
        r["eta"] = r["unit"] = None
        if r["safe"]:
            r["gap"] = r["tc_eff"]
            continue
        best = None
        for u in units:
            if u["type"] == "vehicle" and r["depth"] > .4: continue
            if u["type"] == "air" and r["severity"] < 4: continue
            
            drop_time = 0
            start_pos = u["pos"]
            
            # Feature 3: Capacity routing detours
            if u["pax"] + r["people"] > u["cap"]:
                s = min(SHELTERS, key=lambda x: km(u["pos"], (x[1], x[2])))
                drop_time = (km(u["pos"], (s[1], s[2])) / u["speed"]) * 60 + 10 
                start_pos = (s[1], s[2])
                
            d = km(start_pos, (r["lat"], r["lng"]))
            eta = u["free"] + drop_time + (d / u["speed"]) * 60 + 10
            
            if best is None or eta < best[0]: 
                best = (eta, u, d, drop_time, start_pos)
                
        if best:
            eta, u, d, drop_time, start_pos = best
            r["eta"], r["unit"] = round(eta), u["id"]
            u["free"] = eta + (d / u["speed"]) * 60 + 10
            
            if drop_time > 0:
                u["pax"] = r["people"]
            else:
                u["pax"] += r["people"]
                
            u["pos"] = (r["lat"], r["lng"])
            
        r["gap"] = round(r["tc_eff"] - (r["eta"] if r["eta"] is not None else 9999))
        
    live = [r for r in rows if not r["safe"]]
    zc = zone_crisis(crisis)
    
    start = make_units(boats)
    for u in start:
        if placements and u["id"] in placements: u["pos"] = placements[u["id"]]
        match = next((x for x in units if x["id"] == u["id"]), None)
        if match: u["cap"] = match["cap"]

    return dict(rows=rows, crisis=crisis, zones=zc, stage=stage(max(zc.values())),
                gap_households=sum(1 for r in live if r["gap"] < 0), gap_people=sum(r["people"] for r in live if r["gap"] < 0),
                units=[dict(id=u["id"], type=u["type"], lat=u["pos"][0], lng=u["pos"][1], cap=u.get("cap",0)) for u in start], notes=[])

def rehearse(crisis=70, rate=1.2, outage=60, cellular=0, boats=3):
    before = run(crisis, rate, outage, cellular, boats)
    spots = {**{z: v[:2] for z, v in ZONES.items()}, **{f"depot {k}": v for k, v in DEPOTS.items()}}
    movers = [u["id"] for u in make_units(boats) if u["type"] != "air"]
    place = {u["id"]: u["pos"] for u in make_units(boats)}
    score = lambda d: (d["gap_households"], d["gap_people"])
    best = before
    for _ in range(2):
        for uid in movers:
            for name, pos in spots.items():
                trial = {**place, uid: pos}
                d = run(crisis, rate, outage, cellular, boats, trial)
                if score(d) < score(best):
                    best, place = d, trial
    after = best
    after["before_gap"] = before["gap_households"]
    after["recovered"] = max(0, before["gap_households"] - after["gap_households"])
    moved = {}
    for uid in movers:
        if place[uid] != dict((u["id"], u["pos"]) for u in make_units(boats))[uid]:
            zone = min(ZONES, key=lambda z: km(ZONES[z][:2], place[uid]))
            moved.setdefault(zone, []).append(uid)
    for z, ids in moved.items():
        n = sum(r["people"] for r in before["rows"] if r["zone"] == z and r["gap"] < 0)
        after["notes"].append(f"Stage {', '.join(ids)} near {z}" + (f", where {n} people are in a gap without it." if n else "."))
    if after["gap_households"]:
        after["notes"].append("Red rings on the map are households still in a gap after pre-positioning. Add boats or advise early evacuation there.")
    elif not after["notes"]:
        after["notes"].append("No gaps at this level. Keep crews at their depots.")
    return after