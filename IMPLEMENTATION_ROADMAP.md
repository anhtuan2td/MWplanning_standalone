# IMPLEMENTATION ROADMAP
## MW PRE-PLANNING LITE SYSTEM

---

# PHASE 1 — FOUNDATION

## Objective
Create runnable backend foundation.

## Tasks

### 1. Initialize repository
- backend/
- frontend/
- config/
- data/
- docker/

### 2. Setup FastAPI
- routing
- logging
- config loading

### 3. Setup PostgreSQL/PostGIS
- DB schema
- spatial extension

### 4. Create Docker Compose
Services:
- backend
- frontend
- postgres

### Deliverable
System starts successfully.

---

# PHASE 2 — DATA LAYER

## Objective
Load DEM and site inventory.

## Tasks

### 1. Site Importer
Input:
- CSV

Output:
- DB insertion

### 2. DEM Loader
- read GeoTIFF
- sample elevation

### 3. DEM Validator
- verify DEM coverage
- verify coordinate reading

### Deliverable
System can query:
- site coordinates
- terrain elevation

---

# PHASE 3 — TERRAIN ENGINE

## Objective
Generate terrain profile.

## Tasks

### 1. Terrain Sampling
- interpolate path
- sample DEM

### 2. Profile Generator
Output:
- distance
- terrain elevation

### 3. Earth Curvature
Add curvature compensation.

### Deliverable
Terrain profile works.

---

# PHASE 4 — RF ENGINE

## Objective
Implement LOS and Fresnel calculations.

## Tasks

### 1. LOS Engine
- LOS line
- obstruction detection

### 2. Fresnel Engine
- Fresnel radius
- clearance calculation

### 3. Tower Height Solver
- minimum tower height estimation

### Deliverable
RF calculations operational.

---

# PHASE 5 — CANDIDATE ENGINE

## Objective
Automatic candidate discovery.

## Tasks

### 1. Radius Scanner
- spatial query

### 2. Candidate Evaluation Loop
For each candidate:
- terrain
- LOS
- Fresnel

### 3. Rejection Logic
- failed links
- reason codes

### Deliverable
Automatic candidate evaluation operational.

---

# PHASE 6 — SCORING ENGINE

## Objective
Rank candidate links.

## Tasks

### 1. Scoring Model
- LOS
- Fresnel
- distance
- tower margin

### 2. Ranking Engine
- sort candidates

### 3. Risk Flags
- engineering warnings

### Deliverable
Best candidate selection operational.

---

# PHASE 7 — API LAYER

## Objective
Expose all functionality.

## Required APIs

- /health
- /sites/import
- /sites/search
- /terrain/profile
- /rf/check-link
- /plan/single-link

### Deliverable
Backend API complete.

---

# PHASE 8 — FRONTEND

## Objective
Create operational UI.

## Tasks

### 1. Input Form
- site coordinates
- radius
- band

### 2. Candidate Table
- ranking
- score
- status

### 3. Map View
- sites
- link lines

### 4. Terrain Chart
- terrain profile
- LOS line

### Deliverable
Usable web UI.

---

# PHASE 9 — EXPORT

## Objective
Export engineering results.

## Tasks

### 1. JSON Export

### 2. CSV Export

### 3. Optional PDF

### Deliverable
Export operational.

---

# PHASE 10 — OFFLINE VALIDATION

## Objective
Verify internal-network readiness.

## Checklist

- no Internet calls
- no telemetry
- all configs externalized
- DEM local
- DB local
- Docker portable

### Deliverable
Internal deployment ready.

---

# PHASE 11 — FUTURE EXTENSIONS

Potential future phases:
- AI orchestration
- NetMind integration
- Netflow integration
- multi-hop optimization
- rain fade
- interference analysis
- topology-aware planning