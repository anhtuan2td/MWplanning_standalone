from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_planner_config, get_settings
from app.schemas.planning import SingleLinkPlanRequest
from app.terrain.dem_health import (
    HEALTH_BAD,
    HEALTH_OK,
    HEALTH_SUSPECT,
    audit_dem_directory,
    load_health_report,
    update_health_report,
)
from app.terrain.downloader import (
    _worldcover_tiles_for_radius,
    download_dem_tile_names,
    download_worldcover_tile_names,
    tiles_for_radius,
)


@dataclass(frozen=True)
class GisPreflightResult:
    dem_tiles: list[str]
    worldcover_tiles: list[str]
    missing_dem_tiles: list[str]
    missing_worldcover_tiles: list[str]
    bad_dem_tiles: list[str] = field(default_factory=list)
    suspect_dem_tiles: list[str] = field(default_factory=list)
    unknown_dem_tiles: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            not self.missing_dem_tiles
            and not self.missing_worldcover_tiles
            and not self.bad_dem_tiles
            and not self.suspect_dem_tiles
            and not self.unknown_dem_tiles
        )

    @property
    def status(self) -> str:
        if self.ok:
            if self.worldcover_tiles:
                return "DEM+WORLDCOVER_OK"
            return "DEM_OK"
        if self.missing_dem_tiles or self.missing_worldcover_tiles:
            return "GIS_MISSING"
        if self.bad_dem_tiles:
            return "GIS_BAD"
        if self.suspect_dem_tiles or self.unknown_dem_tiles:
            return "GIS_SUSPECT"
        return "GIS_MISSING"

    @property
    def blocks_planning(self) -> bool:
        return self.status in {"GIS_MISSING", "GIS_BAD"}

    @property
    def error_message(self) -> str:
        parts: list[str] = []
        if self.missing_dem_tiles:
            parts.append(f"Thieu DEM: {', '.join(self.missing_dem_tiles)}")
        if self.missing_worldcover_tiles:
            parts.append(f"Thieu WorldCover: {', '.join(self.missing_worldcover_tiles)}")
        if self.bad_dem_tiles:
            parts.append(f"DEM loi: {', '.join(self.bad_dem_tiles)}")
        if self.suspect_dem_tiles:
            parts.append(f"DEM nghi ngo: {', '.join(self.suspect_dem_tiles)}")
        if self.unknown_dem_tiles:
            parts.append(f"DEM chua audit: {', '.join(self.unknown_dem_tiles)}")
        return "; ".join(parts)

    @property
    def warning_flags(self) -> list[str]:
        flags: list[str] = []
        if self.suspect_dem_tiles:
            flags.append(f"DEM_SUSPECT_TILE:{'|'.join(self.suspect_dem_tiles)}")
        if self.unknown_dem_tiles:
            flags.append(f"DEM_HEALTH_UNKNOWN:{'|'.join(self.unknown_dem_tiles)}")
        return flags


def _existing_dem_tiles(dem_directory: Path) -> set[str]:
    if not dem_directory.exists():
        return set()
    return {path.name.removesuffix(".tif").removesuffix(".tiff") for path in dem_directory.glob("*.tif*")}


def _existing_worldcover_tiles(worldcover_directory: Path) -> set[str]:
    if not worldcover_directory.exists():
        return set()
    return {path.name for path in worldcover_directory.glob("*.tif*")}


def check_batch_gis_coverage(sites: list[SingleLinkPlanRequest]) -> dict[str, GisPreflightResult]:
    """Fast GIS preflight for batch planning.

    Full DEM raster audit is intentionally a separate operation. Batch planning
    only checks required tile names against the latest health report so the
    request stays fast and avoids repeated raster scans.
    """

    settings = get_settings()
    config = get_planner_config()
    default_radius = float(config.get("candidate_radius_km", 30))
    require_worldcover = bool(settings.worldcover_apply_height_offsets)

    existing_dem = _existing_dem_tiles(settings.dem_directory)
    existing_worldcover = _existing_worldcover_tiles(settings.worldcover_directory)
    health_report = load_health_report()

    results: dict[str, GisPreflightResult] = {}
    for index, site in enumerate(sites):
        radius = site.radius_km or default_radius
        dem_tiles = sorted(set(tiles_for_radius(site.latitude, site.longitude, radius)))
        worldcover_tiles = (
            sorted(set(_worldcover_tiles_for_radius(site.latitude, site.longitude, radius)))
            if require_worldcover
            else []
        )
        missing_dem_tiles = [tile for tile in dem_tiles if tile not in existing_dem]
        bad_dem_tiles: list[str] = []
        suspect_dem_tiles: list[str] = []
        unknown_dem_tiles: list[str] = []
        for tile in [tile for tile in dem_tiles if tile in existing_dem]:
            health = health_report.get(tile)
            if health is None:
                unknown_dem_tiles.append(tile)
            elif health.status == HEALTH_BAD:
                bad_dem_tiles.append(tile)
            elif health.status == HEALTH_SUSPECT:
                suspect_dem_tiles.append(tile)
            elif health.status != HEALTH_OK:
                unknown_dem_tiles.append(tile)

        results[f"{index}:{site.site_name}"] = GisPreflightResult(
            dem_tiles=dem_tiles,
            worldcover_tiles=worldcover_tiles,
            missing_dem_tiles=missing_dem_tiles,
            missing_worldcover_tiles=[tile for tile in worldcover_tiles if tile not in existing_worldcover],
            bad_dem_tiles=bad_dem_tiles,
            suspect_dem_tiles=suspect_dem_tiles,
            unknown_dem_tiles=unknown_dem_tiles,
        )
    return results


def repair_gis_coverage(site: SingleLinkPlanRequest) -> GisPreflightResult:
    """Download missing/BAD GIS inputs for one site and re-check coverage.

    BAD DEM tiles are force-downloaded because the existing file is not trusted.
    SUSPECT/UNKNOWN tiles are reported as warnings and are not automatically
    replaced; they may still be valid but need operator review.
    """

    first = check_batch_gis_coverage([site])[f"0:{site.site_name}"]
    dem_to_download = sorted(set(first.missing_dem_tiles + first.bad_dem_tiles))
    if dem_to_download:
        download_dem_tile_names(dem_to_download, force_existing=True)
        audited = audit_dem_directory(tiles=first.dem_tiles)
        update_health_report(audited)
    if first.missing_worldcover_tiles:
        download_worldcover_tile_names(first.missing_worldcover_tiles)
    return check_batch_gis_coverage([site])[f"0:{site.site_name}"]
