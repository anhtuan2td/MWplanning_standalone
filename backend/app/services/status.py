from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.site import Site
from app.schemas.status import SystemStatus
from app.services.mw_links import load_existing_links


TILE_REGION_HINTS = {
    "N10E107": {"Binh Thuan"},
    "N10E108": {"Binh Thuan"},
    "N11E107": {"Binh Thuan", "Lam Dong"},
    "N11E108": {"Binh Thuan", "Khanh Hoa", "Lam Dong"},
    "N11E109": {"Khanh Hoa"},
    "N12E107": {"Dak Lak", "Gia Lai", "Lam Dong"},
    "N12E108": {"Dak Lak", "Gia Lai", "Khanh Hoa", "Lam Dong"},
    "N12E109": {"Dak Lak", "Khanh Hoa"},
    "N13E107": {"Dak Lak", "Gia Lai"},
    "N13E108": {"Dak Lak", "Gia Lai"},
    "N13E109": {"Dak Lak", "Gia Lai"},
    "N14E107": {"Gia Lai"},
    "N14E108": {"Gia Lai"},
    "N15E105": {"Hue"},
    "N15E106": {"Hue", "Da Nang"},
    "N15E107": {"Da Nang"},
    "N15E108": {"Da Nang"},
    "N16E105": {"Quang Tri", "Hue"},
    "N16E106": {"Quang Tri", "Hue"},
    "N16E107": {"Quang Tri", "Hue"},
    "N16E108": {"Da Nang", "Hue"},
    "N17E105": {"Ha Tinh", "Quang Tri"},
    "N17E106": {"Quang Tri"},
    "N17E107": {"Quang Tri"},
    "N18E105": {"Ha Tinh", "Quang Tri"},
    "N18E106": {"Ha Tinh", "Quang Tri"},
}


def _tile_name(lat_floor: int, lon_floor: int) -> str:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return f"{ns}{abs(lat_floor):02d}{ew}{abs(lon_floor):03d}"


def _dem_tiles(dem_directory: Path) -> list[str]:
    return sorted(path.stem for path in dem_directory.glob("*.tif"))


def _dem_regions(tiles: list[str]) -> list[str]:
    regions: set[str] = set()
    for tile in tiles:
        regions.update(TILE_REGION_HINTS.get(tile, set()))
    return sorted(regions)


def _dem_unmapped_tiles(tiles: list[str]) -> list[str]:
    return sorted(tile for tile in tiles if tile not in TILE_REGION_HINTS)


def _worldcover_maps(worldcover_directory: Path) -> list[str]:
    return sorted(path.stem for path in worldcover_directory.glob("ESA_WorldCover_*_Map.tif*"))


def _worldcover_origin(map_name: str) -> tuple[int, int] | None:
    marker = "_v100_"
    if marker not in map_name:
        return None
    tile = map_name.split(marker, 1)[1].split("_Map", 1)[0]
    if len(tile) < 7:
        return None
    lat_sign = 1 if tile[0] == "N" else -1 if tile[0] == "S" else 0
    lon_sign = 1 if tile[3] == "E" else -1 if tile[3] == "W" else 0
    if not lat_sign or not lon_sign:
        return None
    try:
        return lat_sign * int(tile[1:3]), lon_sign * int(tile[4:7])
    except ValueError:
        return None


def _worldcover_regions(maps: list[str]) -> list[str]:
    regions: set[str] = set()
    for map_name in maps:
        origin = _worldcover_origin(map_name)
        if origin is None:
            continue
        lat_origin, lon_origin = origin
        for lat in range(lat_origin, lat_origin + 3):
            for lon in range(lon_origin, lon_origin + 3):
                regions.update(TILE_REGION_HINTS.get(_tile_name(lat, lon), set()))
    return sorted(regions)


def _worldcover_unmapped_maps(maps: list[str]) -> list[str]:
    unmapped: list[str] = []
    for map_name in maps:
        origin = _worldcover_origin(map_name)
        if origin is None:
            unmapped.append(map_name)
            continue
        lat_origin, lon_origin = origin
        if not any(
            _tile_name(lat, lon) in TILE_REGION_HINTS
            for lat in range(lat_origin, lat_origin + 3)
            for lon in range(lon_origin, lon_origin + 3)
        ):
            unmapped.append(map_name)
    return sorted(unmapped)


def get_system_status(db: Session) -> SystemStatus:
    total_sites = db.scalar(select(func.count()).select_from(Site)) or 0
    rows = db.execute(select(Site.status, func.count()).group_by(Site.status)).all()
    status_counts = {status or "unknown": int(count) for status, count in rows}
    settings = get_settings()
    tiles = _dem_tiles(settings.dem_directory)
    maps = _worldcover_maps(settings.worldcover_directory)
    return SystemStatus(
        total_sites=int(total_sites),
        total_mw_links=len(load_existing_links()),
        site_status_counts=status_counts,
        dem_tiles=tiles,
        dem_regions=_dem_regions(tiles),
        dem_unmapped_tiles=_dem_unmapped_tiles(tiles),
        worldcover_maps=maps,
        worldcover_regions=_worldcover_regions(maps),
        worldcover_unmapped_maps=_worldcover_unmapped_maps(maps),
    )
