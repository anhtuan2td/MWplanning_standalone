from app.core.config import get_planner_config
from app.schemas.planning import TerrainProfile


def check_los(profile: TerrainProfile) -> tuple[bool, float, float]:
    config = get_planner_config()
    minimum_margin = float(config.get("minimum_los_margin_m", 1))
    if not profile.los_elevation_m:
        raise ValueError("Terrain profile is missing LOS elevation data")

    worst_clearance = float("inf")
    worst_point_km = 0.0
    for distance_m, terrain_m, los_m in zip(
        profile.distance_m,
        profile.effective_terrain_elevation_m,
        profile.los_elevation_m,
        strict=True,
    ):
        clearance = los_m - terrain_m
        if clearance < worst_clearance:
            worst_clearance = clearance
            worst_point_km = distance_m / 1000

    return worst_clearance >= minimum_margin, round(worst_clearance, 2), round(worst_point_km, 3)
