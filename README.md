# Vantage-Grid-CODE-CONNECT-26-


## 1. Purpose of the Application

### The Problem

During rapid-onset urban disasters, such as severe flooding in dense coastal cities like Karachi, conventional emergency dispatch systems fail to scale. Rescue requests flood in simultaneously, overwhelming existing response units. Traditional models rely on "first-come, first-served" queues or generic map tools that show *where* the hazard is, but fail to identify *who* is most vulnerable, how long they can wait, or where rescue crews will arrive too late. This results in units being dispatched to stable, multi-story buildings while individuals reliant on oxygen or with limited mobility are trapped on lower ground.

### The Solution

Vantage Grid replaces traditional queuing with a **predictive triage decision engine**. Instead of logging calls in the order they are received, the system assigns every household a dynamic "Survival Clock." By continually ingesting real-time meteorological telemetry, tracking infrastructure failures (power/cellular grids), and monitoring vehicle capacities, the engine calculates active resource decay curves. It prioritizes dispatches based on a mathematical index of physiological vulnerability versus time urgency, highlighting critical "Rescue Gaps" so command staff can pre-position assets before clocks expire.

### Algorithmic Architecture (Formulas)

The engine evaluates physical and demographic constraints to rank rescue priority in real time:

* **Survival Clock (Tc):** The base safe duration a household can endure, evaluating flood depth, medical dependency, thermal limits, and supplies. Action steps confirmed by residents inject mitigation bonus minutes (B):
`Tc = max(5, min(T_flood, T_med, T_therm, T_sup, 2880)) + B`
* **Uncertainty & Comms Failure (Tc_eff):** Verified households receive high confidence (k = 1.0). Unknowns get shorter clocks (k = 0.5) for early welfare checks. Total cellular blackouts drop k to worst-case scenarios:
`Tc_eff = Tc * (0.6 + 0.4 * k)`
* **Severity (S) & Probability of Need (P):** Severity scales from 2 to 5 based on medical/age factors. Probability reacts to user telemetry (silence vs. safe check-ins):
`P = clamp(0.4 + 0.5 * (C/100) + P_silent - P_safe, 0.02, 1.0)`
* **Priority Index:** Balances vulnerability against time:
`Priority = (P * S * 60) / max(Tc_eff, 10)`
* **Logistics & Rescue Gap:** ETA calculates vehicle transit, passenger capacity caps, and forced detours to relief shelters. A negative gap indicates a catastrophic delay:
`ETA = T_free + T_detour + (Distance / V_unit * 60) + T_pickup`
`Gap = Tc_eff - ETA`

### Adaptability to Other Disasters

Because the engine is fundamentally a **resource decay and spatial routing algorithm**, it is hazard-agnostic. By altering the limit variables in the `clock()` function within `engine.py`, the system seamlessly pivots to other crises:

* **Wildfires:** Replace flood logic with fireline progression calculated via live wind direction and terrain slope. Tie the medical clock to live Air Quality Index (AQI) APIs to rapidly escalate priority for asthma/oxygen patients as smoke density increases.
* **Hurricanes:** Substitute flood math for Storm Surge matrices and ground aerial assets automatically when API windspeeds exceed flight safety thresholds.
* **Winter Storms / Grid Failures:** The thermal limit becomes the primary driver, assessing how quickly specific housing materials drop to lethal temperatures based on live external API data and power outage percentages.

---

## 2. Description of Application

### Civilian Interfaces (Zero-Friction Access)

* **Home Page (`/`):** An open, low-latency landing pad designed for extreme stress environments. Directs civilians immediately to registration or check-in and features a live telemetry demo to build system trust.
* **Registration (`/civilian/register`):** A streamlined, dynamic flow capturing geographical data, floor level, demographic counts, and critical medical markers (oxygen, mobility). Generates a secure Household ID and enforces privacy consent.
* **Check-In (`/civilian/checkin`):** An ID-gated portal where residents update their status ("Safe" or "Need Help"). It features context-aware mitigation steps (e.g., "Move to highest floor", "Connect backup power") that, when checked, mathematically buy the user more time and update the command center's ETA calculations.
* **Public Crisis Map (`/civilian/map`):** A public-facing viewport showing regional flood extents, active shelters, and deployed rescue units. Excludes all private civilian data to protect identities.

### Command Center (High-Security Staff Access)

* **Operator Gateway (`/login`):** Authentication wall protecting sensitive dispatch and telemetry routes.
* **Live Dashboard (`/staff/dashboard`):** The primary operator hub. Features:
* *Priority Queue:* Real-time, auto-sorting list of households flagged by Critical/Urgent statuses, Rescue Gaps, and Comms Blackout indicators.
* *Map Canvas:* Visual overlay of triage data, routing lines, and safe zones.
* *Dispatch & Planning Pane:* Includes Fleet capacity tracking, systemic alerts, coverage equity algorithms, and Manual Override protocols.
* *Data Source Toggle:* Allows operators to switch between manual slider inputs and Live API Meteorological ingestion.


* **Rehearsal Planner (`/staff/rehearsal`):** A predictive sandbox. Operators modify simulated constraints (flood rise rate, power grids, cellular blackouts, fleet size) to project future Rescue Gaps and determine optimal pre-positioning of assets before a storm makes landfall.
* **Systemic Pages (`/how`, `/about`, `/privacy`):** Documentation detailing algorithm mechanics, the operating authority (REMA), and strict 72-hour ephemeral data retention policies.

---

## 3. Tech Stack & Dependencies

**Backend Architecture:**

* **Python 3:** Core logic and algorithm processing.
* **FastAPI:** High-performance async web framework for API routing and backend logic.
* **Uvicorn:** ASGI web server implementation.
* **Pydantic:** Strict payload validation and data parsing.
* **SQLite (via `tempfile`):** Ephemeral database management ensuring state persists across serverless instances without requiring external database provisioning.

**Frontend Layer:**

* **HTML5 & Jinja2:** Server-side templating for dynamic view rendering.
* **Tailwind CSS:** Utility-first styling delivered via CDN, customized with a high-contrast, low-anxiety clinical color palette (Slate, Teal, Blue, Orange).
* **Vanilla JavaScript:** Lightweight DOM manipulation, dynamic form generation, and async API polling (zero heavy frameworks like React/Vue to maintain absolute minimal load times).

**Geospatial & Integrations:**

* **Leaflet.js:** Open-source interactive mapping library.
* **Esri Canvas Basemaps:** High-contrast light gray cartography tiles utilized for clinical data visualization.
* **Open-Meteo API:** Third-party, open-source weather API used for live ingestion of windspeed and temperature to auto-calibrate crisis levels.

---

## 4. Project Structure

```text
vantage-grid/
├── api/
│   ├── engine.py          # Core triage algorithms, routing math, and SQLite setup
│   └── index.py           # FastAPI application, route definitions, and auth logic
├── static/
│   ├── crimson_nova.jpg   # Developer badge asset
│   └── logo.png           # Vantage Grid 3D branding asset
├── templates/
│   ├── about.html         # System and operator information
│   ├── base.html          # Global layout, navigation, and footer
│   ├── checkin.html       # Secure civilian status update portal
│   ├── dashboard.html     # Live staff command center and priority queue
│   ├── home.html          # Public landing page
│   ├── how.html           # Technical explanation of the triage algorithm
│   ├── login.html         # Secure operator authentication gateway
│   ├── map.html           # Public-facing crisis map and telemetry
│   ├── privacy.html       # Data protection and retention policies
│   ├── register.html      # Civilian household registration flow
│   └── rehearsal.html     # Predictive simulation and staging sandbox
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
├── requirements.txt       # Python package dependencies
├── smoke_test.py          # Automated endpoint integration tests
└── vercel.json            # Serverless deployment configuration

```

---

## 5. Local Deployment Instructions

To run Vantage Grid on your local machine for development or demonstration:

1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/vantage-grid.git
cd vantage-grid

```


2. **Initialize a Virtual Environment**
```bash
python -m venv .venv

```


3. **Activate the Environment**
* On Windows: `.venv\Scripts\activate`
* On macOS/Linux: `source .venv/bin/activate`


4. **Install Dependencies**
```bash
pip install -r requirements.txt

```


5. **Run the Server**
```bash
uvicorn api.index:app --reload

```


6. **Access the Application**
Open your browser and navigate to `[http://127.0.0.1:8000](http://127.0.0.1:8000)`.

---

## 6. Online Access & Usage

The application is configured out-of-the-box for serverless deployment on platforms like Vercel (via the included `vercel.json` build configuration).

**To use the live application:**

1. Navigate to your deployed URL (e.g., `[https://vantage-grid-systems.vercel.app](https://vantage-grid-systems.vercel.app)` or your custom domain).
2. **Civilian Flow:** Use the public links to view the crisis map or register a test household. Note the generated Household ID to test the Check-in flow.
3. **Command Center Flow:**
* Click "Staff Login" in the top navigation bar.
* Enter the Beta Operator Passcode: **`REMA2026`**
* You will be redirected to the Live Dashboard where you can monitor registered households, test the Live API weather toggle, and run simulated scenarios in the Rehearsal Planner.
