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
    "N14E107": {"Gia Lai"},
    "N14E108": {"Gia Lai"},
    "N15E107": {"Da Nang"},
    "N15E108": {"Da Nang"},
    "N16E107": {"Da Nang", "Hue"},
    "N16E108": {"Da Nang", "Hue"},
}


def _dem_tiles(dem_directory: Path) -> list[str]:
    return sorted(path.stem for path in dem_directory.glob("*.tif"))


def _dem_regions(tiles: list[str]) -> list[str]:
    regions: set[str] = set()
    for tile in tiles:
        regions.update(TILE_REGION_HINTS.get(tile, set()))
    return sorted(regions)


def _dem_unmapped_tiles(tiles: list[str]) -> list[str]:
    return sorted(tile for tile in tiles if tile not in TILE_REGION_HINTS)


def get_system_status(db: Session) -> SystemStatus:
    total_sites = db.scalar(select(func.count()).select_from(Site)) or 0
    rows = db.execute(select(Site.status, func.count()).group_by(Site.status)).all()
    status_counts = {status or "unknown": int(count) for status, count in rows}
    tiles = _dem_tiles(get_settings().dem_directory)
    return SystemStatus(
        total_sites=int(total_sites),
        total_mw_links=len(load_existing_links()),
        site_status_counts=status_counts,
        dem_tiles=tiles,
        dem_regions=_dem_regions(tiles),
        dem_unmapped_tiles=_dem_unmapped_tiles(tiles),
    )
