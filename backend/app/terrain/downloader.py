from __future__ import annotations

import gzip
import math
import shutil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

import rasterio
from rasterio.shutil import copy as rio_copy

from app.core.config import get_settings
from app.schemas.planning import DemDownloadResult
from app.terrain.dem import DemSampler


SKADI_BASE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi"


def _tile_name(lat_floor: int, lon_floor: int) -> str:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return f"{ns}{abs(lat_floor):02d}{ew}{abs(lon_floor):03d}"


def tiles_for_radius(latitude: float, longitude: float, radius_km: float) -> list[str]:
    lat_delta = radius_km / 111.0
    lon_scale = max(math.cos(math.radians(latitude)), 0.1)
    lon_delta = radius_km / (111.0 * lon_scale)
    min_lat = math.floor(latitude - lat_delta)
    max_lat = math.floor(latitude + lat_delta)
    min_lon = math.floor(longitude - lon_delta)
    max_lon = math.floor(longitude + lon_delta)
    return [
        _tile_name(lat, lon)
        for lat in range(min_lat, max_lat + 1)
        for lon in range(min_lon, max_lon + 1)
    ]


def _tile_url(tile: str) -> str:
    lat_prefix = tile[:3]
    return f"{SKADI_BASE_URL}/{lat_prefix}/{tile}.hgt.gz"


def _convert_hgt_gz_to_tif(gz_path: Path, tif_path: Path) -> None:
    hgt_path = gz_path.with_suffix("")
    try:
        with gzip.open(gz_path, "rb") as src, hgt_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        with rasterio.open(hgt_path) as dataset:
            rio_copy(dataset, tif_path, driver="GTiff", compress="deflate", predictor=2)
    finally:
        if hgt_path.exists():
            hgt_path.unlink()


def download_dem_tiles(latitude: float, longitude: float, radius_km: float) -> DemDownloadResult:
    dem_directory = get_settings().dem_directory
    dem_directory.mkdir(parents=True, exist_ok=True)
    requested = tiles_for_radius(latitude, longitude, radius_km)
    downloaded: list[str] = []
    existing: list[str] = []
    failed: list[str] = []

    for tile in requested:
        tif_path = dem_directory / f"{tile}.tif"
        gz_path = dem_directory / f"{tile}.hgt.gz"
        if tif_path.exists():
            existing.append(tile)
            continue
        try:
            if not gz_path.exists():
                urlretrieve(_tile_url(tile), gz_path)
            _convert_hgt_gz_to_tif(gz_path, tif_path)
            downloaded.append(tile)
        except (HTTPError, URLError, OSError, rasterio.errors.RasterioError):
            failed.append(tile)

    DemSampler.clear_cache()

    return DemDownloadResult(
        requested_tiles=requested,
        downloaded_tiles=downloaded,
        existing_tiles=existing,
        failed_tiles=failed,
    )
