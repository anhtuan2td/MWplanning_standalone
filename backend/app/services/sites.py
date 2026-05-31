import csv
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.site import Site
from app.schemas.site import ImportResult, SiteSearchResult
from app.services.geo import bearing_deg, haversine_km
from app.terrain.dem import DemSampler


CSV_ALIASES = {
    "site_code": ["site_code", "code", "siteid", "site_id"],
    "site_name": ["site_name", "name", "sitename"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
    "ground_elevation_m": ["ground_elevation_m", "ground_elevation", "elevation", "elevation_m"],
    "tower_height_m": ["tower_height_m", "tower_height", "tower_m"],
    "available_height_m": ["available_height_m", "available_height", "available_m"],
    "overload": ["overload", "is_overload", "overloaded"],
    "diverse_routing": ["vh", "diverse_routing", "diverse", "diverse_route"],
    "status": ["status"],
}


def _decode_csv(content: bytes) -> str:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "cp1252", "latin1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise ValueError("Unsupported CSV encoding. Tried utf-8-sig, utf-8, cp1258, cp1252, latin1.")


def _value(row: dict[str, str], field: str, default: str = "") -> str:
    lower_row = {k.lower().strip(): v for k, v in row.items()}
    for name in CSV_ALIASES[field]:
        if name in lower_row and lower_row[name] != "":
            return lower_row[name].strip()
    return default


def _float(row: dict[str, str], field: str, default: float = 0.0) -> float:
    value = _value(row, field, "")
    return float(value) if value != "" else default


def _bool(row: dict[str, str], field: str, default: bool = False) -> bool:
    value = _value(row, field, "").lower()
    if value == "":
        return default
    return value in {"1", "true", "yes", "y", "x", "overload", "diverse"}


def _int_flag(row: dict[str, str], field: str, default: int = 0) -> int:
    value = _value(row, field, "").strip().lower()
    if value == "":
        return default
    try:
        return int(float(value))
    except ValueError:
        return 1 if value in {"true", "yes", "y", "x", "overload"} else default


def import_sites_csv(db: Session, content: bytes) -> ImportResult:
    decoded = _decode_csv(content)
    reader = csv.DictReader(StringIO(decoded))
    result = ImportResult(inserted=0, updated=0, skipped=0, errors=[])
    dem_sampler = DemSampler()

    for line_number, row in enumerate(reader, start=2):
        try:
            site_code = _value(row, "site_code")
            if not site_code:
                result.skipped += 1
                result.errors.append(f"Line {line_number}: missing site_code")
                continue

            site = db.scalar(select(Site).where(Site.site_code == site_code))
            is_new = site is None
            if site is None:
                site = Site(site_code=site_code, site_name=site_code, latitude=0, longitude=0)

            site.site_name = _value(row, "site_name", site_code)
            site.latitude = _float(row, "latitude")
            site.longitude = _float(row, "longitude")
            csv_elevation = _value(row, "ground_elevation_m", "")
            site.ground_elevation_m = (
                float(csv_elevation)
                if csv_elevation != ""
                else dem_sampler.sample(site.latitude, site.longitude, fallback_m=0)
            )
            site.tower_height_m = _float(row, "tower_height_m", 30)
            site.available_height_m = _float(row, "available_height_m", site.tower_height_m)
            site.overload = _int_flag(row, "overload", 0)
            site.diverse_routing = _bool(row, "diverse_routing", False)
            site.status = _value(row, "status", "active")

            if is_new:
                db.add(site)
                result.inserted += 1
            else:
                result.updated += 1
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"Line {line_number}: {exc}")

    db.commit()
    return result


def search_sites(db: Session, lat: float, lon: float, radius_km: float) -> list[SiteSearchResult]:
    sites = db.scalars(select(Site).where(Site.status == "active")).all()
    results: list[SiteSearchResult] = []
    for site in sites:
        distance = haversine_km(lat, lon, site.latitude, site.longitude)
        if distance <= radius_km:
            results.append(
                SiteSearchResult(
                    id=site.id,
                    site_code=site.site_code,
                    site_name=site.site_name,
                    latitude=site.latitude,
                    longitude=site.longitude,
                    ground_elevation_m=site.ground_elevation_m,
                    tower_height_m=site.tower_height_m,
                    available_height_m=site.available_height_m,
                    overload=site.overload,
                    diverse_routing=site.diverse_routing,
                    status=site.status,
                    distance_km=round(distance, 3),
                    bearing_deg=round(bearing_deg(lat, lon, site.latitude, site.longitude), 1),
                )
            )
    return sorted(results, key=lambda item: item.distance_km)


def list_sites(db: Session, limit: int = 500, offset: int = 0) -> list[Site]:
    return list(
        db.scalars(
            select(Site)
            .order_by(Site.site_code)
            .offset(offset)
            .limit(min(max(limit, 1), 5000))
        ).all()
    )
