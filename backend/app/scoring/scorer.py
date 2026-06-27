from app.core.config import get_band_config, get_planner_config
from app.rf.availability import availability_score


def score_link(
    *,
    los_pass: bool,
    worst_clearance_m: float,
    fresnel_percent: float,
    distance_km: float,
    band: str,
    tower_margin_m: float,
    availability_percent: float = 100.0,
    diverse_routing: bool = False,
) -> tuple[float, str, list[str]]:
    config = get_planner_config()
    band_config = get_band_config(band)
    weights = config.get("scoring", {})
    los_weight = float(weights.get("los_weight", 40))
    fresnel_weight = float(weights.get("fresnel_weight", 30))
    distance_weight = float(weights.get("distance_weight", 15))
    tower_weight = float(weights.get("tower_margin_weight", 15))
    diverse_bonus = float(weights.get("diverse_routing_bonus", 8))
    availability_weight = float(weights.get("availability_weight", 0))
    max_distance = float(band_config.get("max_distance_km", 999))

    flags: list[str] = []
    rejected = False

    if not los_pass:
        flags.append("TERRAIN_BLOCKED")
        rejected = True
    elif worst_clearance_m < 3:
        flags.append("NEAR_OBSTRUCTION")

    if fresnel_percent < 40:
        flags.append("LOW_FRESNEL_MARGIN")
        rejected = True
    elif fresnel_percent < float(band_config.get("min_fresnel_clearance_percent", 60)):
        flags.append("LOW_FRESNEL_MARGIN")

    if distance_km > max_distance:
        flags.append("EXCESSIVE_DISTANCE")
        rejected = True

    if tower_margin_m < 0:
        flags.append("HIGH_TOWER_REQUIREMENT")
        rejected = True
    elif tower_margin_m < 5:
        flags.append("HIGH_TOWER_REQUIREMENT")

    los_score = los_weight if los_pass else 0
    fresnel_score = fresnel_weight * min(1.0, max(0.0, fresnel_percent / 80))
    distance_ratio = distance_km / max_distance if max_distance else 1
    distance_score = distance_weight * max(0.0, 1 - max(0.0, distance_ratio - 0.6) / 0.4)
    tower_score = tower_weight * min(1.0, max(0.0, tower_margin_m / 10))

    availability_config = config.get("availability", {})
    target = float(availability_config.get("target_percent", 99.99))
    warning = float(availability_config.get("warning_percent", 99.95))
    score = los_score + fresnel_score + distance_score + tower_score + availability_score(availability_percent, availability_weight, target)
    if availability_percent < warning:
        flags.append("LOW_AVAILABILITY")
    if diverse_routing and not rejected:
        score += diverse_bonus
        flags.append("DIVERSE_ROUTING_BONUS")
    score = round(min(100.0, score), 1)
    status = "REJECTED" if rejected else ("RISKY" if flags else "ACCEPTED")
    return score, status, flags
