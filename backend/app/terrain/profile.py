import math

from app.core.config import get_planner_config, get_settings
from app.schemas.planning import Endpoint, TerrainProfile
from app.services.geo import curvature_bulge_m, haversine_km, interpolate_points
from app.terrain.dem import DemSampler


def generate_profile(a: Endpoint, b: Endpoint, step_m: float | None = None) -> TerrainProfile:
    config = get_planner_config()
    step = step_m or config.get("sampling", {}).get("terrain_step_m", 30)
    distance_m = haversine_km(a.latitude, a.longitude, b.latitude, b.longitude) * 1000
    samples = max(2, math.ceil(distance_m / step) + 1)
    points = interpolate_points(a.latitude, a.longitude, b.latitude, b.longitude, samples)
    sampler = DemSampler()

    distances: list[float] = []
    terrain: list[float] = []

    use_surface = get_settings().worldcover_apply_height_offsets
    for index, (lat, lon) in enumerate(points):
        d = distance_m * index / (samples - 1)
        fallback = a.ground_elevation_m + (b.ground_elevation_m - a.ground_elevation_m) * index / (samples - 1)
        if use_surface:
            elev = sampler.sample_surface(lat, lon, fallback)
        else:
            elev = sampler.sample(lat, lon, fallback)
        distances.append(round(d, 2))
        terrain.append(round(elev, 2))

    effective: list[float] = []
    los: list[float] = []
    a_amsl = terrain[0] + a.tower_height_m
    b_amsl = terrain[-1] + b.tower_height_m

    for index, (d, elev) in enumerate(zip(distances, terrain, strict=True)):
        los_elev = a_amsl + (b_amsl - a_amsl) * index / (samples - 1)
        effective.append(round(elev + curvature_bulge_m(d, distance_m), 2))
        los.append(round(los_elev, 2))

    return TerrainProfile(
        distance_m=distances,
        terrain_elevation_m=terrain,
        effective_terrain_elevation_m=effective,
        los_elevation_m=los,
    )
