import re

from app.schemas.planning import TerrainProfile


def band_to_ghz(band: str) -> float:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", band)
    if not match:
        raise ValueError(f"Unsupported band: {band}")
    return float(match.group(1))


def fresnel_clearance(profile: TerrainProfile, band: str) -> tuple[float, float]:
    frequency_ghz = band_to_ghz(band)
    total_km = profile.distance_m[-1] / 1000 if profile.distance_m else 0
    if total_km <= 0 or not profile.los_elevation_m:
        return 100.0, 0.0

    minimum_percent = 100.0
    minimum_clearance_m = float("inf")
    for distance_m, terrain_m, los_m in zip(
        profile.distance_m,
        profile.effective_terrain_elevation_m,
        profile.los_elevation_m,
        strict=True,
    ):
        d1_km = distance_m / 1000
        d2_km = total_km - d1_km
        if d1_km == 0 or d2_km == 0:
            continue
        radius_m = 17.32 * ((d1_km * d2_km) / (frequency_ghz * total_km)) ** 0.5
        clearance_m = los_m - terrain_m
        percent = (clearance_m / radius_m) * 100 if radius_m > 0 else 100
        minimum_percent = min(minimum_percent, percent)
        minimum_clearance_m = min(minimum_clearance_m, clearance_m)

    if minimum_clearance_m == float("inf"):
        minimum_clearance_m = 0.0
    return round(max(0.0, minimum_percent), 1), round(minimum_clearance_m, 2)
