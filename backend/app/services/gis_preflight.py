from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_planner_config, get_settings
from app.schemas.planning import SingleLinkPlanRequest
from app.terrain.downloader import _worldcover_tiles_for_radius, tiles_for_radius


@dataclass(frozen=True)
class GisPreflightResult:
    dem_tiles: list[str]
    worldcover_tiles: list[str]
    missing_dem_tiles: list[str]
    missing_worldcover_tiles: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_dem_tiles and not self.missing_worldcover_tiles

    @property
    def status(self) -> str:
        if self.ok:
            if self.worldcover_tiles:
                return "DEM+WORLDCOVER_OK"
            return "DEM_OK"
        return "GIS_MISSING"

    @property
    def error_message(self) -> str:
        parts: list[str] = []
        if self.missing_dem_tiles:
            parts.append(f"Thiếu DEM: {', '.join(self.missing_dem_tiles)}")
        if self.missing_worldcover_tiles:
            parts.append(f"Thiếu WorldCover: {', '.join(self.missing_worldcover_tiles)}")
        return "; ".join(parts)


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

    The planner samples terrain along links to candidates within the search radius.
    Checking the full search window per input site is a small over-estimate, but it
    avoids opening raster files and prevents slow per-link fallback surprises.
    """

    settings = get_settings()
    config = get_planner_config()
    default_radius = float(config.get("candidate_radius_km", 30))
    require_worldcover = bool(settings.worldcover_apply_height_offsets)

    existing_dem = _existing_dem_tiles(settings.dem_directory)
    existing_worldcover = _existing_worldcover_tiles(settings.worldcover_directory)

    results: dict[str, GisPreflightResult] = {}
    for index, site in enumerate(sites):
        radius = site.radius_km or default_radius
        dem_tiles = sorted(set(tiles_for_radius(site.latitude, site.longitude, radius)))
        worldcover_tiles = (
            sorted(set(_worldcover_tiles_for_radius(site.latitude, site.longitude, radius)))
            if require_worldcover
            else []
        )
        results[f"{index}:{site.site_name}"] = GisPreflightResult(
            dem_tiles=dem_tiles,
            worldcover_tiles=worldcover_tiles,
            missing_dem_tiles=[tile for tile in dem_tiles if tile not in existing_dem],
            missing_worldcover_tiles=[tile for tile in worldcover_tiles if tile not in existing_worldcover],
        )
    return results
