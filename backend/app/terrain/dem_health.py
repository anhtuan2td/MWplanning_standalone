from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings


HEALTH_OK = "OK"
HEALTH_SUSPECT = "SUSPECT"
HEALTH_BAD = "BAD"
HEALTH_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class DemTileHealth:
    tile: str
    status: str
    reason: str = ""
    path: str = ""
    checked_at: str = ""
    sample_count: int = 0
    valid_count: int = 0
    nodata_count: int = 0
    min_m: float | None = None
    max_m: float | None = None
    mean_m: float | None = None

    @property
    def is_bad(self) -> bool:
        return self.status == HEALTH_BAD

    @property
    def is_suspect(self) -> bool:
        return self.status in {HEALTH_SUSPECT, HEALTH_UNKNOWN}


def dem_health_directory() -> Path:
    return get_settings().dem_directory.parent / "dem_health"


def latest_health_report_path() -> Path:
    return dem_health_directory() / "latest.csv"


def _tile_from_path(path: Path) -> str:
    name = path.name
    for suffix in (".tiff", ".tif"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _is_invalid_value(value: object, nodata: float | None) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return True
    if not math.isfinite(number):
        return True
    if nodata is not None and number == nodata:
        return True
    return number < -500 or number > 9000


def _sample_points(dataset, grid_size: int) -> list[tuple[float, float]]:
    bounds = dataset.bounds
    points: list[tuple[float, float]] = []
    for row in range(grid_size):
        y_ratio = (row + 0.5) / grid_size
        lat = bounds.top - (bounds.top - bounds.bottom) * y_ratio
        for col in range(grid_size):
            x_ratio = (col + 0.5) / grid_size
            lon = bounds.left + (bounds.right - bounds.left) * x_ratio
            points.append((lon, lat))
    return points


def audit_dem_tile(path: Path, grid_size: int = 5) -> DemTileHealth:
    checked_at = datetime.now(timezone.utc).isoformat()
    tile = _tile_from_path(path)
    try:
        import rasterio
    except ImportError:
        return DemTileHealth(tile=tile, status=HEALTH_UNKNOWN, reason="RASTERIO_NOT_INSTALLED", path=str(path), checked_at=checked_at)

    try:
        with rasterio.open(path) as dataset:
            if dataset.width <= 0 or dataset.height <= 0:
                return DemTileHealth(tile=tile, status=HEALTH_BAD, reason="EMPTY_RASTER", path=str(path), checked_at=checked_at)
            if not dataset.bounds or dataset.bounds.left >= dataset.bounds.right or dataset.bounds.bottom >= dataset.bounds.top:
                return DemTileHealth(tile=tile, status=HEALTH_BAD, reason="INVALID_BOUNDS", path=str(path), checked_at=checked_at)

            nodata = dataset.nodata
            values: list[float] = []
            nodata_count = 0
            points = _sample_points(dataset, grid_size)
            for point in points:
                try:
                    raw_value = next(dataset.sample([point]))[0]
                except Exception:
                    nodata_count += 1
                    continue
                if _is_invalid_value(raw_value, nodata):
                    nodata_count += 1
                    continue
                values.append(float(raw_value))
    except Exception as exc:
        return DemTileHealth(tile=tile, status=HEALTH_BAD, reason=f"OPEN_OR_SAMPLE_ERROR:{exc.__class__.__name__}", path=str(path), checked_at=checked_at)

    sample_count = grid_size * grid_size
    if not values:
        return DemTileHealth(
            tile=tile,
            status=HEALTH_BAD,
            reason="NO_VALID_SAMPLES",
            path=str(path),
            checked_at=checked_at,
            sample_count=sample_count,
            valid_count=0,
            nodata_count=nodata_count,
        )

    min_m = min(values)
    max_m = max(values)
    mean_m = sum(values) / len(values)
    invalid_ratio = nodata_count / sample_count if sample_count else 1.0
    status = HEALTH_OK
    reasons: list[str] = []
    if invalid_ratio > 0.5:
        status = HEALTH_BAD
        reasons.append("TOO_MANY_INVALID_SAMPLES")
    elif invalid_ratio > 0:
        status = HEALTH_SUSPECT
        reasons.append("SOME_INVALID_SAMPLES")
    if len(values) >= 5 and max_m == min_m:
        status = HEALTH_SUSPECT if status == HEALTH_OK else status
        reasons.append("FLAT_SAMPLE_GRID")

    return DemTileHealth(
        tile=tile,
        status=status,
        reason="|".join(reasons) if reasons else "OK",
        path=str(path),
        checked_at=checked_at,
        sample_count=sample_count,
        valid_count=len(values),
        nodata_count=nodata_count,
        min_m=round(min_m, 2),
        max_m=round(max_m, 2),
        mean_m=round(mean_m, 2),
    )


def audit_dem_directory(dem_directory: Path | None = None, tiles: list[str] | None = None, grid_size: int = 5) -> list[DemTileHealth]:
    directory = dem_directory or get_settings().dem_directory
    selected = {tile.upper() for tile in tiles} if tiles else None
    paths = sorted(list(directory.glob("*.tif")) + list(directory.glob("*.tiff")))
    results: list[DemTileHealth] = []
    for path in paths:
        tile = _tile_from_path(path).upper()
        if selected is not None and tile not in selected:
            continue
        results.append(audit_dem_tile(path, grid_size=grid_size))
    if selected is not None:
        existing = {item.tile.upper() for item in results}
        for tile in sorted(selected - existing):
            results.append(DemTileHealth(tile=tile, status=HEALTH_BAD, reason="TILE_FILE_MISSING"))
    return results


def write_health_report(results: list[DemTileHealth], path: Path | None = None) -> Path:
    output_path = path or latest_health_report_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "tile",
        "status",
        "reason",
        "path",
        "checked_at",
        "sample_count",
        "valid_count",
        "nodata_count",
        "min_m",
        "max_m",
        "mean_m",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in sorted(results, key=lambda value: value.tile):
            writer.writerow({field: getattr(item, field) for field in fields})
    if output_path.name != "latest.csv":
        latest_path = latest_health_report_path()
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        with latest_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for item in sorted(results, key=lambda value: value.tile):
                writer.writerow({field: getattr(item, field) for field in fields})
    return output_path


def load_health_report(path: Path | None = None) -> dict[str, DemTileHealth]:
    report_path = path or latest_health_report_path()
    if not report_path.exists():
        return {}
    results: dict[str, DemTileHealth] = {}
    with report_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            tile = (row.get("tile") or "").strip()
            if not tile:
                continue
            results[tile] = DemTileHealth(
                tile=tile,
                status=(row.get("status") or HEALTH_UNKNOWN).strip().upper(),
                reason=row.get("reason") or "",
                path=row.get("path") or "",
                checked_at=row.get("checked_at") or "",
                sample_count=int(float(row.get("sample_count") or 0)),
                valid_count=int(float(row.get("valid_count") or 0)),
                nodata_count=int(float(row.get("nodata_count") or 0)),
                min_m=float(row["min_m"]) if row.get("min_m") else None,
                max_m=float(row["max_m"]) if row.get("max_m") else None,
                mean_m=float(row["mean_m"]) if row.get("mean_m") else None,
            )
    return results


def update_health_report(results: list[DemTileHealth], path: Path | None = None) -> Path:
    report_path = path or latest_health_report_path()
    merged = load_health_report(report_path)
    for item in results:
        merged[item.tile] = item
    return write_health_report(list(merged.values()), report_path)
