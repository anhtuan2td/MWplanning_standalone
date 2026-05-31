import os
from threading import Timer

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_planner_config
from app.database.session import database_ready, get_db
from app.schemas.planning import (
    LinkCheckRequest,
    LinkCheckResult,
    DemDownloadRequest,
    DemDownloadResult,
    GisDownloadResult,
    SingleLinkPlanRequest,
    SingleLinkPlanResult,
    TerrainProfile,
    TerrainProfileRequest,
    TerrainGridRequest,
    TerrainGridResult,
)
from app.schemas.site import ImportResult, SiteOut, SiteSearchResult
from app.schemas.status import SystemStatus
from app.services.planner import check_link, plan_single_link_cancellable
from app.services.mw_links import antenna_rule_table, import_existing_links_csv
from app.services.sites import import_sites_csv, list_sites, search_sites
from app.services.status import get_system_status
from app.terrain.downloader import download_dem_tiles
from app.terrain.grid import generate_grid
from app.terrain.profile import generate_profile


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": "ok" if database_ready() else "error"}


@router.get("/config")
def planner_config() -> dict:
    return get_planner_config()


@router.get("/calloff/rules")
def calloff_rules() -> dict[str, list[dict[str, float | str]]]:
    return {"band_antenna_rules": antenna_rule_table()}


@router.get("/system/status", response_model=SystemStatus)
def system_status(db: Session = Depends(get_db)) -> SystemStatus:
    return get_system_status(db)


@router.post("/system/shutdown")
def system_shutdown(request: Request) -> dict[str, str]:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="Shutdown is only allowed from localhost")

    Timer(0.5, lambda: os._exit(0)).start()
    return {"status": "shutting_down"}


@router.post("/sites/import", response_model=ImportResult)
async def import_sites(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ImportResult:
    return import_sites_csv(db, await file.read())


@router.post("/mw-links/import")
async def import_mw_links(file: UploadFile = File(...)) -> dict[str, int]:
    return import_existing_links_csv(await file.read())


@router.get("/sites", response_model=list[SiteOut])
def sites_list(
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[SiteOut]:
    return list_sites(db, limit=limit, offset=offset)


@router.get("/sites/search", response_model=list[SiteSearchResult])
def sites_search(
    lat: float = Query(...),
    lon: float = Query(...),
    radius_km: float = Query(30),
    db: Session = Depends(get_db),
) -> list[SiteSearchResult]:
    return search_sites(db, lat, lon, radius_km)


@router.post("/terrain/profile", response_model=TerrainProfile)
def terrain_profile(request: TerrainProfileRequest) -> TerrainProfile:
    return generate_profile(request.a, request.b, request.step_m)


@router.post("/terrain/grid", response_model=TerrainGridResult)
def terrain_grid(request: TerrainGridRequest) -> TerrainGridResult:
    return generate_grid(request)


@router.post("/dem/download", response_model=GisDownloadResult)
def dem_download(request: DemDownloadRequest) -> GisDownloadResult:
    from app.terrain.downloader import download_gis_tiles

    return download_gis_tiles(request.latitude, request.longitude, request.radius_km)


@router.post("/gis/download", response_model=GisDownloadResult)
def gis_download(request: DemDownloadRequest) -> GisDownloadResult:
    from app.terrain.downloader import download_gis_tiles

    return download_gis_tiles(request.latitude, request.longitude, request.radius_km)


@router.post("/rf/check-link", response_model=LinkCheckResult)
def rf_check_link(request: LinkCheckRequest) -> LinkCheckResult:
    return check_link(request)


@router.post("/plan/single-link", response_model=SingleLinkPlanResult)
async def single_link_plan(
    request_body: SingleLinkPlanRequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> SingleLinkPlanResult:
    return await plan_single_link_cancellable(db, request_body, http_request.is_disconnected)
