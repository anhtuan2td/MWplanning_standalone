# SYSTEM ARCHITECTURE
## MW PRE-PLANNING LITE SYSTEM

---

# 1. SYSTEM PURPOSE

Provide automatic microwave candidate screening
for new MW site deployment.

The system shall:
- scan nearby sites
- evaluate terrain
- evaluate LOS/Fresnel
- rank candidate links
- generate engineering-oriented outputs

---

# 2. HIGH-LEVEL ARCHITECTURE

```text
Frontend UI
    ↓
Backend API
    ↓
Planning Core
    ├── Candidate Scanner
    ├── Terrain Engine
    ├── LOS Engine
    ├── Fresnel Engine
    ├── Scoring Engine
    └── Report Generator
    ↓
Database + DEM Storage
```

---

# 3. FRONTEND

Technology:
- React
- TypeScript
- Leaflet

Responsibilities:
- user input
- map visualization
- terrain visualization
- result display
- export trigger

---

# 4. BACKEND API

Technology:
- FastAPI

Responsibilities:
- routing
- validation
- orchestration
- API responses

---

# 5. DATABASE LAYER

Technology:
- PostgreSQL
- PostGIS

Responsibilities:
- store site inventory
- spatial query
- coordinate indexing

---

# 6. DEM STORAGE

Format:
- GeoTIFF

Responsibilities:
- terrain elevation source

Storage:
```text
/data/dem/
```

---

# 7. CANDIDATE SCANNER

Responsibilities:
- search nearby sites
- calculate distance
- generate candidate list

Input:
```text
new site coordinates
```

Output:
```text
candidate site list
```

---

# 8. TERRAIN ENGINE

Responsibilities:
- sample terrain
- generate profile
- Earth curvature correction

Input:
```text
site A
site B
```

Output:
```text
terrain profile
```

---

# 9. LOS ENGINE

Responsibilities:
- LOS calculation
- obstruction detection
- clearance estimation

Output:
```text
PASS / FAIL
```

---

# 10. FRESNEL ENGINE

Responsibilities:
- Fresnel radius
- clearance calculation

Output:
```text
clearance percentage
```

---

# 11. SCORING ENGINE

Responsibilities:
- candidate evaluation
- ranking
- risk flags

Output:
```text
engineering score
```

---

# 12. REPORT GENERATOR

Responsibilities:
- JSON export
- CSV export
- future PDF export

---

# 13. MAIN EXECUTION FLOW

```text
User inputs new site
    ↓
Backend receives request
    ↓
Candidate scanner searches nearby sites
    ↓
For each candidate:
    ├── Terrain profile
    ├── LOS check
    ├── Fresnel check
    └── Scoring
    ↓
Ranking engine sorts candidates
    ↓
Backend returns best candidates
    ↓
Frontend displays results
```

---

# 14. INTERNAL NETWORK DEPLOYMENT

Deployment target:
- isolated enterprise network

Requirements:
- no Internet dependency
- local DEM
- local DB
- local Docker deployment

---

# 15. DOCKER ARCHITECTURE

```text
frontend container
backend container
postgres/postgis container
```

Communication:
```text
internal docker network
```

---

# 16. CONFIGURATION ARCHITECTURE

Configuration sources:
- .env
- planner_config.yaml

Must support:
- environment portability
- internal deployment
- future AI integration

---

# 17. FUTURE AI ARCHITECTURE

Future optional architecture:

```text
Frontend
    ↓
Backend
    ↓
AI Adapter
    ↓
NetMind / LLM
```

AI responsibilities:
- explain results
- summarize engineering output
- planner assistance

AI shall NOT:
- replace terrain engine
- replace RF calculations
- replace scoring engine

---

# 18. NON-FUNCTIONAL REQUIREMENTS

## Performance
- candidate scan < 10 sec for moderate radius

## Reliability
- recover from DEM read failure
- recover from invalid site data

## Maintainability
- modular architecture
- isolated engines

## Portability
- identical operation across environments

---

# 19. ENGINEERING BOUNDARY

This system is:
```text
pre-planning assistant
```

This system is NOT:
```text
final detailed RF planning platform
```