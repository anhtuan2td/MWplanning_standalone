from __future__ import annotations

import math


EARTH_RADIUS_M = 6_371_000


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return (2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))) / 1000


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    y = math.sin(d_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def interpolate_points(lat1: float, lon1: float, lat2: float, lon2: float, samples: int) -> list[tuple[float, float]]:
    if samples < 2:
        return [(lat1, lon1), (lat2, lon2)]
    return [
        (lat1 + (lat2 - lat1) * i / (samples - 1), lon1 + (lon2 - lon1) * i / (samples - 1))
        for i in range(samples)
    ]


def curvature_bulge_m(distance_from_a_m: float, total_distance_m: float, k_factor: float = 4 / 3) -> float:
    if total_distance_m <= 0:
        return 0
    distance_from_b_m = total_distance_m - distance_from_a_m
    return (distance_from_a_m * distance_from_b_m) / (2 * k_factor * EARTH_RADIUS_M)
