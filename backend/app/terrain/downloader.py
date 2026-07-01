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
from app.schemas.planning import DemDownloadResult, GisDownloadResult, WorldCoverDownloadResult
from app.terrain.dem import DemSampler


SKADI_BASE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi"


def _tile_name(lat_floor: int, lon_floor: int) -> str:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return f"{ns}{abs(lat_floor):02d}{ew}{abs(lon_floor):03d}"


def _copernicus_tile_key(tile: str) -> str:
    lat_prefix = tile[0]
    lon_prefix = tile[3]
    lat = tile[1:3]
    lon = tile[4:7]
    folder = f"Copernicus_DSM_COG_10_{lat_prefix}{lat}_00_{lon_prefix}{lon}_00_DEM"
    return f"{folder}/{folder}.tif"


def _worldcover_tile_name(lat_floor: int, lon_floor: int) -> str:
    lat_origin = math.floor(lat_floor / 3) * 3
    lon_origin = math.floor(lon_floor / 3) * 3
    ns = "N" if lat_origin >= 0 else "S"
    ew = "E" if lon_origin >= 0 else "W"
    return f"ESA_WorldCover_10m_2020_v100_{ns}{abs(lat_origin):02d}{ew}{abs(lon_origin):03d}_Map.tif"


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


def _copernicus_tile_url(tile: str) -> str:
    base_url = get_settings().copernicus_dem_base_url.rstrip("/")
    return f"{base_url}/{_copernicus_tile_key(tile)}"


def _skadi_tile_url(tile: str) -> str:
    lat_prefix = tile[:3]
    return f"{SKADI_BASE_URL}/{lat_prefix}/{tile}.hgt.gz"


def _worldcover_tile_url(tile: str) -> str:
    base_url = get_settings().worldcover_base_url.rstrip("/")
    return f"{base_url}/{tile}"


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
        if tif_path.exists():
            existing.append(tile)
            continue
        try:
            if get_settings().dem_source == "copernicus":
                try:
                    urlretrieve(_copernicus_tile_url(tile), tif_path)
                except Exception:
                    gz_path = dem_directory / f"{tile}.hgt.gz"
                    if not gz_path.exists():
                        urlretrieve(_skadi_tile_url(tile), gz_path)
                    _convert_hgt_gz_to_tif(gz_path, tif_path)
            else:
                gz_path = dem_directory / f"{tile}.hgt.gz"
                if not gz_path.exists():
                    urlretrieve(_skadi_tile_url(tile), gz_path)
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


def download_dem_tile_names(requested: list[str], force_existing: bool = False) -> DemDownloadResult:
    dem_directory = get_settings().dem_directory
    dem_directory.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    existing: list[str] = []
    failed: list[str] = []

    for tile in sorted(set(requested)):
        tif_path = dem_directory / f"{tile}.tif"
        if tif_path.exists():
            if not force_existing:
                existing.append(tile)
                continue
            try:
                tif_path.unlink()
            except OSError:
                failed.append(tile)
                continue
        gz_path = dem_directory / f"{tile}.hgt.gz"
        if force_existing and gz_path.exists():
            try:
                gz_path.unlink()
            except OSError:
                failed.append(tile)
                continue
        try:
            if get_settings().dem_source == "copernicus":
                try:
                    urlretrieve(_copernicus_tile_url(tile), tif_path)
                except Exception:
                    gz_path = dem_directory / f"{tile}.hgt.gz"
                    if not gz_path.exists():
                        urlretrieve(_skadi_tile_url(tile), gz_path)
                    _convert_hgt_gz_to_tif(gz_path, tif_path)
            else:
                gz_path = dem_directory / f"{tile}.hgt.gz"
                if not gz_path.exists():
                    urlretrieve(_skadi_tile_url(tile), gz_path)
                _convert_hgt_gz_to_tif(gz_path, tif_path)
            downloaded.append(tile)
        except (HTTPError, URLError, OSError, rasterio.errors.RasterioError):
            failed.append(tile)

    DemSampler.clear_cache()

    return DemDownloadResult(
        requested_tiles=sorted(set(requested)),
        downloaded_tiles=downloaded,
        existing_tiles=existing,
        failed_tiles=failed,
    )


def _worldcover_tiles_for_radius(latitude: float, longitude: float, radius_km: float) -> list[str]:
    lat_delta = radius_km / 111.0
    lon_scale = max(math.cos(math.radians(latitude)), 0.1)
    lon_delta = radius_km / (111.0 * lon_scale)
    min_lat = math.floor(latitude - lat_delta)
    max_lat = math.floor(latitude + lat_delta)
    min_lon = math.floor(longitude - lon_delta)
    max_lon = math.floor(longitude + lon_delta)
    return sorted({
        _worldcover_tile_name(lat, lon)
        for lat in range(min_lat, max_lat + 1)
        for lon in range(min_lon, max_lon + 1)
    })


def download_worldcover_tiles(latitude: float, longitude: float, radius_km: float) -> WorldCoverDownloadResult:
    worldcover_directory = get_settings().worldcover_directory
    worldcover_directory.mkdir(parents=True, exist_ok=True)
    requested = _worldcover_tiles_for_radius(latitude, longitude, radius_km)
    downloaded: list[str] = []
    existing: list[str] = []
    failed: list[str] = []

    for tile in requested:
        tile_path = worldcover_directory / tile
        if tile_path.exists():
            existing.append(tile)
            continue
        try:
            urlretrieve(_worldcover_tile_url(tile), tile_path)
            downloaded.append(tile)
        except (HTTPError, URLError, OSError):
            failed.append(tile)

    DemSampler.clear_cache()

    result = WorldCoverDownloadResult(
        requested_tiles=requested,
        downloaded_tiles=downloaded,
        existing_tiles=existing,
        failed_tiles=failed,
    )
    return result


def download_worldcover_tile_names(requested: list[str]) -> WorldCoverDownloadResult:
    worldcover_directory = get_settings().worldcover_directory
    worldcover_directory.mkdir(parents=True, exist_ok=True)
    downloaded: list[str] = []
    existing: list[str] = []
    failed: list[str] = []

    for tile in sorted(set(requested)):
        tile_path = worldcover_directory / tile
        if tile_path.exists():
            existing.append(tile)
            continue
        try:
            urlretrieve(_worldcover_tile_url(tile), tile_path)
            downloaded.append(tile)
        except (HTTPError, URLError, OSError):
            failed.append(tile)

    DemSampler.clear_cache()

    return WorldCoverDownloadResult(
        requested_tiles=sorted(set(requested)),
        downloaded_tiles=downloaded,
        existing_tiles=existing,
        failed_tiles=failed,
    )


def download_gis_tiles(latitude: float, longitude: float, radius_km: float) -> GisDownloadResult:
    dem_result = download_dem_tiles(latitude, longitude, radius_km)
    worldcover_result = download_worldcover_tiles(latitude, longitude, radius_km)
    return GisDownloadResult(dem=dem_result, worldcover=worldcover_result)


def central_region_gis_tiles() -> tuple[list[str], list[str]]:
    # Broad operational region: Quang Tri/Quang Binh down to Binh Thuan,
    # Dak Nong and Lam Dong. Kept as tile floors to avoid expensive geometry.
    min_lat, max_lat = 10, 18
    min_lon, max_lon = 105, 109
    dem_tiles = [
        _tile_name(lat, lon)
        for lat in range(min_lat, max_lat + 1)
        for lon in range(min_lon, max_lon + 1)
    ]
    worldcover_tiles = sorted({
        _worldcover_tile_name(lat, lon)
        for lat in range(min_lat, max_lat + 1)
        for lon in range(min_lon, max_lon + 1)
    })
    return dem_tiles, worldcover_tiles


def download_central_region_gis_tiles() -> GisDownloadResult:
    dem_tiles, worldcover_tiles = central_region_gis_tiles()
    dem_result = download_dem_tile_names(dem_tiles)
    worldcover_result = download_worldcover_tile_names(worldcover_tiles)
    return GisDownloadResult(dem=dem_result, worldcover=worldcover_result)
