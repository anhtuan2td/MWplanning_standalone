# MW PRE-PLANNING LITE SYSTEM
## MASTER BUILD SPECIFICATION
Version: 1.0
Mode: NO-AI / OFFLINE-FIRST / INTERNAL-NETWORK READY

---

# 1. PRODUCT OVERVIEW

Build a lightweight microwave pre-planning system that:

- receives a new site location
- scans existing microwave sites within a configurable radius
- evaluates terrain and LOS feasibility
- calculates Fresnel clearance
- ranks candidate microwave links
- recommends the best candidate links
- generates engineering-oriented outputs

This is NOT a detailed microwave path design tool like Pathloss or MLinkPlanner.

This system is an:
- automatic MW candidate screening engine
- MW pre-planning assistant
- internal network-aware route recommendation system

The system must work:
- without Internet
- without external AI
- fully offline
- fully portable into internal enterprise network

---

# 2. CORE PRINCIPLES

## 2.1 Offline-first

All resources must be local:

- DEM/SRTM terrain data
- site inventory
- configuration
- database

No Internet dependency allowed.

---

## 2.2 Environment portability

System must run identically:
- on public Internet environment
- inside isolated internal network

No hardcoded:
- IP
- domain
- paths
- API endpoints

Everything configurable via:
- .env
- YAML

---

## 2.3 AI-independent architecture

System must NOT require:
- OpenAI
- NetMind
- cloud AI
- external API

Future AI integration must remain optional.

---

# 3. SYSTEM SCOPE

The system shall support:

## Supported
- single-hop MW pre-planning
- candidate discovery
- terrain profile generation
- LOS checking
- Fresnel checking
- candidate ranking
- engineering scoring
- map visualization
- terrain profile visualization
- export results

## Not supported in v1
- multi-hop optimization
- detailed RF propagation
- rain attenuation simulation
- automatic frequency planning
- interference analysis
- full carrier-grade path engineering

---

# 4. HIGH-LEVEL ARCHITECTURE

```text
Frontend UI
    ↓
Backend API
    ↓
Planning Engine
    ├── Site Scanner
    ├── Terrain Engine
    ├── LOS Engine
    ├── Fresnel Engine
    ├── Scoring Engine
    └── Report Generator
    ↓
Database + DEM Storage
```

---

# 5. TECHNOLOGY STACK

## Backend
- Python 3.12+
- FastAPI

## Terrain/GIS
- GDAL
- Rasterio
- PyProj
- Shapely
- GeoPandas

## Database
- PostgreSQL
- PostGIS

## Frontend
- React
- TypeScript
- Leaflet

## Deployment
- Docker
- Docker Compose

---

# 6. PROJECT STRUCTURE

```text
mw-planner-lite/
│
├── backend/
│   ├── api/
│   ├── core/
│   ├── terrain/
│   ├── rf/
│   ├── scoring/
│   ├── database/
│   ├── services/
│   ├── models/
│   └── utils/
│
├── frontend/
│
├── config/
│   ├── planner_config.yaml
│   └── logging.yaml
│
├── data/
│   ├── dem/
│   └── sites/
│
├── scripts/
│   ├── import_sites.py
│   ├── validate_dem.py
│   ├── smoke_test.py
│   └── initialize_db.py
│
├── docker/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── requirements.txt
```

---

# 7. DATABASE DESIGN

## 7.1 Site Inventory Table

Table: sites

Fields:

| Field | Type |
|---|---|
| id | UUID |
| site_code | VARCHAR |
| site_name | VARCHAR |
| latitude | DOUBLE |
| longitude | DOUBLE |
| ground_elevation_m | DOUBLE |
| tower_height_m | DOUBLE |
| available_height_m | DOUBLE |
| status | VARCHAR |
| created_at | TIMESTAMP |

Create spatial index.

---

# 8. DEM / TERRAIN REQUIREMENTS

## DEM Source
Supported:
- SRTM 30m
- Copernicus DEM

Format:
- GeoTIFF

Storage:
```text
/data/dem/
```

---

# 9. CORE ENGINE MODULES

# 9.1 Candidate Scanner

Input:
- new site coordinates
- radius_km

Process:
- spatial search
- filter existing sites inside radius

Output:
- candidate site list
- distance
- bearing

---

# 9.2 Terrain Engine

Responsibilities:
- read DEM
- sample terrain elevation
- generate terrain profile
- support configurable sample interval

Output:
```json
{
  "distance_m": [],
  "terrain_elevation_m": []
}
```

---

# 9.3 LOS Engine

Responsibilities:
- calculate line-of-sight
- detect obstruction points
- minimum clearance detection

Output:
```json
{
  "los_pass": true,
  "worst_clearance_m": 4.2,
  "worst_point_km": 6.1
}
```

---

# 9.4 Fresnel Engine

Responsibilities:
- calculate Fresnel zone
- determine minimum Fresnel clearance
- configurable frequency band

Supported bands:
- 6 GHz
- 11 GHz
- 18 GHz
- 23 GHz

Output:
```json
{
  "fresnel_clearance_percent": 72,
  "minimum_clearance_m": 3.4
}
```

---

# 9.5 Scoring Engine

Responsibilities:
- evaluate candidate quality
- generate ranking score
- generate engineering risk flags

Scoring categories:
- LOS quality
- Fresnel clearance
- distance suitability
- tower margin
- engineering risk

Output:
```json
{
  "score": 86,
  "rank": 1,
  "risk_flags": []
}
```

---

# 10. CONFIGURATION SYSTEM

File:
```text
/config/planner_config.yaml
```

Example:

```yaml
candidate_radius_km: 30

bands:
  6GHz:
    max_distance_km: 45
    min_fresnel_clearance_percent: 60

  11GHz:
    max_distance_km: 35
    min_fresnel_clearance_percent: 60

  18GHz:
    max_distance_km: 18
    min_fresnel_clearance_percent: 60

  23GHz:
    max_distance_km: 10
    min_fresnel_clearance_percent: 60

sampling:
  terrain_step_m: 30

scoring:
  los_weight: 40
  fresnel_weight: 30
  distance_weight: 15
  tower_margin_weight: 15
```

---

# 11. API SPECIFICATION

# 11.1 Health Check

GET:
```text
/health
```

---

# 11.2 Import Sites

POST:
```text
/sites/import
```

Input:
- CSV file

---

# 11.3 Search Sites

GET:
```text
/sites/search
```

Parameters:
- lat
- lon
- radius_km

---

# 11.4 Terrain Profile

POST:
```text
/terrain/profile
```

---

# 11.5 RF Link Check

POST:
```text
/rf/check-link
```

---

# 11.6 Single Link Planning

POST:
```text
/plan/single-link
```

Input:
```json
{
  "site_name": "NEW_SITE",
  "latitude": 16.032,
  "longitude": 108.221,
  "tower_height_m": 30,
  "radius_km": 30,
  "band": "18GHz"
}
```

Output:
```json
{
  "best_candidate": {},
  "candidate_links": [],
  "rejected_links": [],
  "summary": {}
}
```

---

# 12. FRONTEND REQUIREMENTS

## 12.1 Main Features

### Input Panel
- new site coordinates
- tower height
- radius
- frequency band

### Candidate Table
Columns:
- candidate site
- distance
- LOS
- Fresnel %
- score
- status

### Map View
- display sites
- display link lines
- display selected route

### Terrain Profile View
- terrain profile chart
- LOS line
- obstruction markers

---

# 13. EXPORT FEATURES

Support:
- JSON export
- CSV export

Optional:
- PDF report

---

# 14. LOGGING REQUIREMENTS

Must support:
- file logging
- rotating logs
- configurable log level

No cloud telemetry.

---

# 15. SECURITY REQUIREMENTS

Must support:
- offline deployment
- internal-network-only deployment
- no external callback
- no analytics SDK
- no telemetry

---

# 16. DOCKER REQUIREMENTS

Create:
- backend container
- frontend container
- postgres/postgis container

Use:
```text
docker-compose up
```

to start entire system.

---

# 17. REQUIRED SCRIPTS

## import_sites.py
Import site inventory CSV.

## validate_dem.py
Validate DEM loading.

## smoke_test.py
Verify:
- DB connection
- DEM loading
- API health
- sample LOS calculation

## initialize_db.py
Initialize DB schema.

---

# 18. TESTING REQUIREMENTS

Must include:
- unit tests
- API tests
- terrain engine tests
- LOS tests
- Fresnel tests

---

# 19. MVP MILESTONES

# Milestone 1
- project structure
- DB
- DEM loading

# Milestone 2
- terrain profile
- LOS checking

# Milestone 3
- Fresnel calculation
- candidate scanning

# Milestone 4
- scoring engine
- ranking engine

# Milestone 5
- frontend UI

# Milestone 6
- Docker packaging
- offline deployment validation

---

# 20. FUTURE EXTENSIONS

Potential future features:
- multi-hop planning
- AI orchestration
- NetMind integration
- Netflow integration
- rain fade modeling
- advanced RF planning
- topology-aware optimization
- automatic route recommendation
- internal engineering workflow integration

---

# 21. IMPORTANT IMPLEMENTATION RULES

## DO
- keep modules isolated
- keep configs externalized
- support offline execution
- support internal-network deployment
- prioritize maintainability

## DO NOT
- hardcode paths
- hardcode API endpoints
- depend on Internet
- depend on cloud AI
- couple frontend tightly to backend

---

# 22. FINAL OBJECTIVE

The final system shall:

- receive a new site
- automatically scan nearby sites
- evaluate engineering feasibility
- rank candidate microwave links
- generate engineering-oriented outputs
- run completely offline
- be deployable inside isolated enterprise networks
- be AI-ready in future without architecture rewrite