import os
import csv
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
    BatchPlanRequest, BatchPlanResult, BatchSiteResult, BatchCandidate,
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
from app.services.equipment import import_equipment_profiles, list_equipment_profiles
from app.terrain.downloader import download_central_region_gis_tiles, download_dem_tiles
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


@router.get("/equipment/profiles")
def equipment_profiles() -> list[dict[str, str | float]]:
    return list_equipment_profiles()


@router.post("/equipment/import")
async def equipment_import(file: UploadFile = File(...)) -> dict[str, int]:
    try:
        return import_equipment_profiles(await file.read())
    except (UnicodeDecodeError, ValueError, csv.Error) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.post("/gis/download/central-region", response_model=GisDownloadResult)
def gis_download_central_region() -> GisDownloadResult:
    return download_central_region_gis_tiles()


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


@router.post("/plan/batch", response_model=BatchPlanResult)
async def batch_plan(request_body: BatchPlanRequest, http_request: Request, db: Session = Depends(get_db)) -> BatchPlanResult:
    results = []
    for site in request_body.sites:
        if await http_request.is_disconnected():
            break
        try:
            plan = await plan_single_link_cancellable(db, site, http_request.is_disconnected)
            if plan.candidate_links:
                batch_links = plan.candidate_links
                note = None
            else:
                batch_links = sorted(plan.rejected_links, key=lambda item: (-item.link.score, item.link.distance_km))
                min_radius = max(1.0, site.min_radius_km or 0.0)
                max_radius = site.radius_km or "mặc định"
                note = (
                    f"Không có tuyến đạt sau khi quét {plan.summary.total_candidates} candidate "
                    f"trong dải bán kính {min_radius:g}-{max_radius} km; đang hiển thị top rejected."
                    if batch_links
                    else "Không tìm thấy candidate trong bán kính quét."
                )
            candidates = [
                BatchCandidate(
                    rank=item.rank or index,
                    site_code=item.candidate.site_code,
                    distance_km=item.link.distance_km,
                    band=item.link.band,
                    score=item.link.score,
                    status=item.link.status,
                    availability_percent=item.link.availability_percent,
                    rain_zone=item.link.rain_zone,
                    fade_margin_db=item.link.fade_margin_db,
                    equipment_profile=item.link.equipment_profile,
                    risk_flags=item.link.risk_flags + ([note] if note else []),
                    calloff=item.calloff,
                )
                for index, item in enumerate(batch_links[: request_body.top_n], 1)
            ]
            results.append(
                BatchSiteResult(
                    site_name=site.site_name,
                    candidates=candidates,
                    error=None if candidates else "Không tìm thấy candidate trong bán kính quét.",
                )
            )
        except Exception as exc:
            results.append(
                BatchSiteResult(
                    site_name=site.site_name,
                    candidates=[],
                    error=str(exc),
                )
            )
    return BatchPlanResult(results=results)
