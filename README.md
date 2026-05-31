# MW Pre-planning Lite

Offline-first microwave candidate screening system for single-hop pre-planning.

## Run with Docker

```bash
docker compose up --build
```

Services:

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:5173`
- PostgreSQL/PostGIS: `localhost:5432`

The frontend uses OpenStreetMap tiles by default for the basemap. Override `VITE_MAP_TILE_URL` to use an internal tile server later.

After the first successful build, normal source edits are mounted into the containers. Restart only the affected service when needed:

```bash
docker compose restart backend
docker compose restart frontend
```

## Import Site CSV

Open the frontend and use **Import site CSV**, or call:

```bash
curl -F "file=@data/sites/sample_sites.csv" http://localhost:8000/sites/import
```

Supported CSV columns:

```text
site_code,site_name,latitude,longitude,tower_height_m,available_height_m,status,owner,region,overload,VH
```

Minimum required columns are `site_code`, `latitude`, and `longitude`. Elevation is not required; it is sampled from local DEM when available and falls back to `0` when no DEM covers that coordinate. Extra columns after the required fields are accepted and ignored, so future site metadata will not break import.

Aliases such as `lat`, `lon`, `tower_height`, and `available_height` are also accepted. Optional elevation columns such as `ground_elevation_m` or `elevation` are still accepted if you decide to provide them later.

## User Guide

See [docs/USER_GUIDE.md](docs/USER_GUIDE.md) for the end-to-end workflow: open the web UI, import site/MW CSV files, enter a new site, download DEM, run scan, select a route, inspect terrain, and export calloff.

## DEM Data

Place local GeoTIFF DEM files in:

```text
data/dem/
```

If no DEM is present, the engine falls back to endpoint elevation interpolation so the system remains runnable for functional testing.

The frontend also has a **Download DEM** button. It uses the current latitude, longitude, and radius to ask the backend to calculate required 1x1 degree SRTM/Skadi tiles, skip files already present in `data/dem/`, download missing `.hgt.gz` files, and convert them to GeoTIFF. This requires Internet access and is optional; for internal/offline deployment, copy prepared GeoTIFF files into `data/dem/` instead.

## Main APIs

- `GET /health`
- `GET /sites`
- `POST /sites/import`
- `GET /sites/search?lat=16.032&lon=108.221&radius_km=30`
- `POST /terrain/profile`
- `POST /dem/download`
- `POST /rf/check-link`
- `POST /plan/single-link`

## Local Backend Commands

From the repository root after installing `requirements.txt`:

```bash
pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload
pytest
```

For scripts, set `PYTHONPATH=backend` or run them from a container.

## Build standalone Windows EXE

This project can be packaged as a single Windows executable using PyInstaller.

Prerequisites:
- Python 3.11+ installed and available on `PATH`
- Node.js and `npm` installed to build the frontend

From the repository root:

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

If `npm` is not available, you must first build the frontend manually in `frontend/`:

```bash
cd frontend
npm install
npm run build
```

Then rerun the build script.

Packaging helpers have been moved to `packaging/` to keep build scripts and specs centralized.
You can run the existing root `build_exe.ps1` (keeps backward compatibility) or call the central script directly:

```powershell
# run from repo root (for backward compatibility)
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1

# or run the centralized helper
powershell -ExecutionPolicy Bypass -File .\packaging\build_exe.ps1
```

See [packaging/README.md](packaging/README.md) for details and troubleshooting tips.

## Run for development

Recommended - run with Postgres (docker) for a close-to-production dev environment:

```powershell
# from repo root
docker compose up -d postgres
python -m pip install -r requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend dev server:

```powershell
cd frontend
npm install
npm run dev
```

Alternatively run without Postgres using local SQLite:

```powershell
$env:MW_DATABASE_URL = "sqlite:///$(pwd)\data\mwplanner.db"
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Notes:
- Use `MW_DATABASE_URL` to override the database connection string for both dev and CI.
- The project is configured to use SQLite when running as a frozen EXE and defaults to Postgres for normal development.
