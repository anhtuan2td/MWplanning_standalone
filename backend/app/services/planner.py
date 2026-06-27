from collections.abc import Awaitable, Callable
from time import perf_counter
from math import atan2, degrees
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_band_config, get_planner_config, get_settings
from app.rf.fresnel import fresnel_clearance
from app.rf.los import check_los
from app.rf.availability import estimate_availability_details
from app.schemas.planning import (
    CandidateLink,
    CalloffInfo,
    Endpoint,
    LinkCheckRequest,
    LinkCheckResult,
    PlanSummary,
    SingleLinkPlanRequest,
    SingleLinkPlanResult,
)
from app.scoring.scorer import score_link
from app.models.site import Site
from app.services.geo import bearing_deg, haversine_km
from app.services.mw_links import (
    band_for_site,
    height_for_site,
    links_for_site,
    lowest_height_for_site,
    normalize_code,
    other_site_code,
    root_side_for_new_link,
    suggested_antenna_diameter,
    band_group,
)
from app.services.sites import search_sites
from app.terrain.dem import DemSampler
from app.terrain.profile import generate_profile


RADIUS_SCAN_STEP_KM = 1.0
MIN_CANDIDATE_DISTANCE_KM = 1.0


def _normalize_site_code(value: str) -> str:
    return "".join(value.upper().split())


def _auto_band(distance_km: float) -> str:
    bands = get_planner_config().get("bands", {})
    ranked_bands = sorted(
        (
            (band, float(config.get("max_distance_km", 0)))
            for band, config in bands.items()
            if float(config.get("max_distance_km", 0)) > 0
        ),
        key=lambda item: item[1],
    )
    for band, max_distance in ranked_bands:
        if distance_km <= max_distance:
            return band
    return ranked_bands[-1][0] if ranked_bands else "6GHz"


def _candidate_scan_radius(distance_km: float, step_km: float = RADIUS_SCAN_STEP_KM) -> float:
    if distance_km <= 0:
        return step_km
    return ((int((distance_km - 0.000001) / step_km) + 1) * step_km)


def _radius_scan_candidates(
    db: Session,
    request: SingleLinkPlanRequest,
    max_radius_km: float,
) -> list:
    new_site_code = _normalize_site_code(request.site_name)
    min_distance_km = max(MIN_CANDIDATE_DISTANCE_KM, request.min_radius_km or 0.0)
    return [
        candidate
        for candidate in search_sites(db, request.latitude, request.longitude, max_radius_km)
        if _normalize_site_code(candidate.site_code) != new_site_code
        and candidate.distance_km >= min_distance_km
    ]


def _candidate_scan_rings(candidates: list, max_radius_km: float) -> list[list]:
    rings: list[list] = []
    consumed = 0
    while consumed < len(candidates):
        selected_radius = min(max_radius_km, _candidate_scan_radius(candidates[consumed].distance_km))
        ring = []
        while consumed < len(candidates) and candidates[consumed].distance_km <= selected_radius:
            ring.append(candidates[consumed])
            consumed += 1
        rings.append(ring)
    return rings


def _freq_label(band: str, side: str) -> str:
    if not side:
        return ""
    return f"{band.replace('GHz', 'GHz')} {side.title()}"


def _angle_delta_deg(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _tilt_deg(near_total_elevation_m: float, far_total_elevation_m: float, distance_km: float) -> float:
    distance_m = max(distance_km * 1000, 1)
    return round(degrees(atan2(far_total_elevation_m - near_total_elevation_m, distance_m)), 2)


def _site_by_code(db: Session, site_code: str) -> Site | None:
    return db.scalar(select(Site).where(Site.site_code == site_code))


def _overlapping_existing_height(
    db: Session,
    candidate_code: str,
    band: str,
    new_link_azimuth_deg: float,
    threshold_deg: float,
) -> float | None:
    candidate = _site_by_code(db, candidate_code)
    if candidate is None:
        return None
    overlapping_heights = []
    for link in links_for_site(candidate_code):
        if band_group(band_for_site(link, candidate_code)) != band_group(band):
            continue
        other_code = other_site_code(link, candidate_code)
        other_site = _site_by_code(db, other_code)
        if other_site is None:
            continue
        existing_azimuth = bearing_deg(candidate.latitude, candidate.longitude, other_site.latitude, other_site.longitude)
        if _angle_delta_deg(new_link_azimuth_deg, existing_azimuth) <= threshold_deg:
            existing_height = height_for_site(link, candidate_code)
            if existing_height > 0:
                overlapping_heights.append(existing_height)
    return min(overlapping_heights) if overlapping_heights else None


def _effective_root_height(
    db: Session,
    candidate,
    band: str,
    root_azimuth: float,
    available_height_m: float,
) -> float:
    config = get_planner_config().get("calloff", {})
    root_height = available_height_m
    lowest_existing_height = lowest_height_for_site(candidate.site_code)
    if lowest_existing_height is not None:
        root_height = min(root_height, lowest_existing_height)
    overlap_height = _overlapping_existing_height(
        db,
        candidate.site_code,
        band,
        root_azimuth,
        float(config.get("azimuth_overlap_threshold_deg", 15)),
    )
    if overlap_height is not None:
        root_height = max(0, min(root_height, overlap_height - float(config.get("overlap_height_step_down_m", 3))))
    return root_height


def _calloff(
    db: Session,
    new_site: str,
    new_endpoint: Endpoint,
    candidate,
    band: str,
    new_height: float,
    root_height: float,
    distance_km: float,
) -> CalloffInfo:
    root_side = root_side_for_new_link(candidate.site_code, band)
    new_side = "high" if root_side == "low" else "low" if root_side == "high" else ""
    root_azimuth = bearing_deg(candidate.latitude, candidate.longitude, new_endpoint.latitude, new_endpoint.longitude)
    root_height = _effective_root_height(db, candidate, band, root_azimuth, root_height)
    antenna_diameter = suggested_antenna_diameter(band, distance_km)
    new_total_elevation = new_endpoint.ground_elevation_m + new_height
    root_total_elevation = candidate.ground_elevation_m + root_height
    new_azimuth = bearing_deg(new_endpoint.latitude, new_endpoint.longitude, candidate.latitude, candidate.longitude)
    new_tilt = _tilt_deg(new_total_elevation, root_total_elevation, distance_km)
    root_tilt = _tilt_deg(root_total_elevation, new_total_elevation, distance_km)
    return CalloffInfo(
        line=f"{new_site}-{candidate.site_code}-01",
        frequency=band,
        new_site=new_site,
        new_site_frequency=_freq_label(band, new_side),
        new_site_band_side=new_side.title(),
        new_site_antenna_diameter_m=antenna_diameter,
        new_site_height_m=new_height,
        new_site_azimuth_deg=round(new_azimuth, 1),
        new_site_tilt_deg=new_tilt,
        root_site=candidate.site_code,
        root_site_frequency=_freq_label(band, root_side),
        root_site_band_side=root_side.title(),
        root_site_antenna_diameter_m=antenna_diameter,
        root_site_height_m=root_height,
        root_site_azimuth_deg=round(root_azimuth, 1),
        root_site_tilt_deg=root_tilt,
        distance_km=round(distance_km, 3),
    )


def _append_flag(link: LinkCheckResult, flag: str) -> None:
    if flag not in link.risk_flags:
        link.risk_flags.append(flag)


def _apply_calloff_conflict(link: LinkCheckResult, calloff: CalloffInfo) -> None:
    if calloff.root_site_band_side:
        return
    _append_flag(link, "Band side conflict")
    if link.status != "REJECTED":
        link.status = "OVERLINK"


def _apply_operational_rules(link: LinkCheckResult, candidate, existing_link_count: int, config: dict) -> None:
    scoring_config = config.get("scoring", {})

    if candidate.diverse_routing and link.status != "REJECTED":
        link.score = min(100, round(link.score + float(scoring_config.get("diverse_routing_bonus", 8)), 1))
        _append_flag(link, "Diverse routing")

    if "-" in candidate.site_code:
        link.score = max(0, round(link.score - float(scoring_config.get("extended_rru_penalty", 10)), 1))
        _append_flag(link, "RRU kéo dài")

    overload_value = int(candidate.overload or 0)
    if overload_value >= 1:
        link.score = max(0, round(link.score - float(scoring_config.get("overload_penalty", 30)), 1))
        _append_flag(link, f"Danger - Overload {overload_value}")
        if link.status != "REJECTED":
            link.status = "DANGER"

    if existing_link_count >= 2:
        link.score = max(0, round(link.score - float(scoring_config.get("overlink_penalty", 25)), 1))
        _append_flag(link, "Overlink")
        if link.status != "REJECTED":
            link.status = "OVERLINK"


def _site_code_number(site_code: str) -> int | None:
    matches = re.findall(r"\d+", site_code)
    return int(matches[-1]) if matches else None


def _apply_acceptance_filters(link: LinkCheckResult, candidate, existing_link_count: int, config: dict) -> None:
    filters = config.get("accepted_filters", {})
    if hasattr(filters, "model_dump"):
        filters = filters.model_dump()
    if not filters:
        return

    reject_reasons: list[str] = []
    blocked_text = str(filters.get("reject_site_code_contains") or "")
    if blocked_text and blocked_text in candidate.site_code:
        reject_reasons.append(f"site_code contains {blocked_text}")

    min_site_code_number = filters.get("min_site_code_number")
    if min_site_code_number is not None:
        site_code_number = _site_code_number(candidate.site_code)
        if site_code_number is None or site_code_number <= int(min_site_code_number):
            reject_reasons.append(f"site_code number <= {int(min_site_code_number)}")

    if bool(filters.get("reject_overload")) and int(candidate.overload or 0) >= 1:
        reject_reasons.append("overload")

    if bool(filters.get("reject_overlink")) and existing_link_count >= 2:
        reject_reasons.append("overlink")

    if not reject_reasons:
        return

    for reason in reject_reasons:
        _append_flag(link, f"Acceptance filter - {reason}")
    link.status = "REJECTED"


def check_link(request: LinkCheckRequest) -> LinkCheckResult:
    distance_km = haversine_km(request.a.latitude, request.a.longitude, request.b.latitude, request.b.longitude)
    band = request.band if request.band and request.band != "AUTO" else _auto_band(distance_km)
    get_band_config(band)
    sampler = DemSampler()
    sample_elevation = sampler.sample_surface if get_settings().worldcover_apply_height_offsets else sampler.sample
    request.a.ground_elevation_m = sample_elevation(
        request.a.latitude,
        request.a.longitude,
        fallback_m=request.a.ground_elevation_m,
    )
    request.b.ground_elevation_m = sample_elevation(
        request.b.latitude,
        request.b.longitude,
        fallback_m=request.b.ground_elevation_m,
    )
    profile = generate_profile(request.a, request.b, request.step_m)
    los_pass, worst_clearance_m, worst_point_km = check_los(profile)
    fresnel_percent, minimum_clearance_m = fresnel_clearance(profile, band)
    availability_details = estimate_availability_details(
        distance_km, band, request.rain_zone, request.antenna_diameter_m, request.a.latitude, request.equipment_profile
    )
    availability = float(availability_details["availability_percent"])
    rain_zone = str(availability_details["rain_zone"])
    tower_margin_m = min(request.a.tower_height_m, request.b.tower_height_m) - max(0.0, -worst_clearance_m)
    score, status, flags = score_link(
        los_pass=los_pass,
        worst_clearance_m=worst_clearance_m,
        fresnel_percent=fresnel_percent,
        distance_km=distance_km,
        band=band,
        tower_margin_m=tower_margin_m,
        availability_percent=availability,
        diverse_routing=False,
    )
    return LinkCheckResult(
        distance_km=round(distance_km, 3),
        band=band,
        los_pass=los_pass,
        worst_clearance_m=worst_clearance_m,
        worst_point_km=worst_point_km,
        fresnel_clearance_percent=fresnel_percent,
        minimum_clearance_m=minimum_clearance_m,
        score=score,
        status=status,
        risk_flags=flags,
        terrain_profile=profile,
        availability_percent=availability,
        rain_zone=rain_zone,
        fade_margin_db=float(availability_details["fade_margin_db"]),
        equipment_profile=str(availability_details["equipment_profile"]),
    )


def plan_single_link(db: Session, request: SingleLinkPlanRequest) -> SingleLinkPlanResult:
    started_at = perf_counter()
    config = get_planner_config()
    acceptance_config = {**config, "accepted_filters": request.accepted_filters or config.get("accepted_filters", {})}
    radius = request.radius_km or float(config.get("candidate_radius_km", 30))
    candidates = _radius_scan_candidates(db, request, radius)
    sampler = DemSampler()
    sample_elevation = sampler.sample_surface if get_settings().worldcover_apply_height_offsets else sampler.sample
    new_site = Endpoint(
        latitude=request.latitude,
        longitude=request.longitude,
        ground_elevation_m=sample_elevation(request.latitude, request.longitude, fallback_m=0),
        tower_height_m=request.tower_height_m,
    )

    accepted: list[CandidateLink] = []
    rejected: list[CandidateLink] = []
    processed = 0
    for ring in _candidate_scan_rings(candidates, radius):
        ring_accepted = 0
        for candidate in ring:
            root_azimuth = bearing_deg(candidate.latitude, candidate.longitude, new_site.latitude, new_site.longitude)
            distance_km = haversine_km(new_site.latitude, new_site.longitude, candidate.latitude, candidate.longitude)
            band = request.band if request.band and request.band != "AUTO" else _auto_band(distance_km)
            root_height = _effective_root_height(db, candidate, band, root_azimuth, candidate.available_height_m)
            candidate_endpoint = Endpoint(
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                ground_elevation_m=candidate.ground_elevation_m,
                tower_height_m=root_height,
            )
            diameter = request.antenna_diameter_m or suggested_antenna_diameter(band, distance_km)
            link = check_link(LinkCheckRequest(a=new_site, b=candidate_endpoint, band=band, rain_zone=request.rain_zone, antenna_diameter_m=diameter, equipment_profile=request.equipment_profile))
            item = CandidateLink(
                candidate=candidate,
                link=link,
                calloff=_calloff(db, request.site_name, new_site, candidate, link.band, request.tower_height_m, root_height, link.distance_km),
            )
            if item.calloff:
                _apply_calloff_conflict(link, item.calloff)
            candidate_links = links_for_site(candidate.site_code)
            _apply_operational_rules(link, candidate, len(candidate_links), config)
            _apply_acceptance_filters(link, candidate, len(candidate_links), acceptance_config)
            if link.status == "REJECTED":
                rejected.append(item)
            else:
                accepted.append(item)
                ring_accepted += 1
            processed += 1
        if ring_accepted:
            break

    accepted.sort(key=lambda item: item.link.score, reverse=True)
    for rank, item in enumerate(accepted, start=1):
        item.rank = rank

    elapsed = round(perf_counter() - started_at, 3)
    return SingleLinkPlanResult(
        best_candidate=accepted[0] if accepted else None,
        candidate_links=accepted,
        rejected_links=rejected,
        summary=PlanSummary(
            total_candidates=len(candidates),
            accepted=len(accepted),
            rejected=len(rejected),
            band=None,
            elapsed_seconds=elapsed,
            avg_seconds_per_link=round(elapsed / processed, 3) if processed else 0,
        ),
    )


async def plan_single_link_cancellable(
    db: Session,
    request: SingleLinkPlanRequest,
    should_cancel: Callable[[], Awaitable[bool]],
) -> SingleLinkPlanResult:
    started_at = perf_counter()
    config = get_planner_config()
    acceptance_config = {**config, "accepted_filters": request.accepted_filters or config.get("accepted_filters", {})}
    radius = request.radius_km or float(config.get("candidate_radius_km", 30))
    candidates = _radius_scan_candidates(db, request, radius)
    sampler = DemSampler()
    sample_elevation = sampler.sample_surface if get_settings().worldcover_apply_height_offsets else sampler.sample
    new_site = Endpoint(
        latitude=request.latitude,
        longitude=request.longitude,
        ground_elevation_m=sample_elevation(request.latitude, request.longitude, fallback_m=0),
        tower_height_m=request.tower_height_m,
    )

    accepted: list[CandidateLink] = []
    rejected: list[CandidateLink] = []
    processed = 0
    for ring in _candidate_scan_rings(candidates, radius):
        ring_accepted = 0
        for candidate in ring:
            if await should_cancel():
                break
            root_azimuth = bearing_deg(candidate.latitude, candidate.longitude, new_site.latitude, new_site.longitude)
            distance_km = haversine_km(new_site.latitude, new_site.longitude, candidate.latitude, candidate.longitude)
            band = request.band if request.band and request.band != "AUTO" else _auto_band(distance_km)
            root_height = _effective_root_height(db, candidate, band, root_azimuth, candidate.available_height_m)
            candidate_endpoint = Endpoint(
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                ground_elevation_m=candidate.ground_elevation_m,
                tower_height_m=root_height,
            )
            diameter = request.antenna_diameter_m or suggested_antenna_diameter(band, distance_km)
            link = check_link(LinkCheckRequest(a=new_site, b=candidate_endpoint, band=band, rain_zone=request.rain_zone, antenna_diameter_m=diameter, equipment_profile=request.equipment_profile))
            item = CandidateLink(
                candidate=candidate,
                link=link,
                calloff=_calloff(db, request.site_name, new_site, candidate, link.band, request.tower_height_m, root_height, link.distance_km),
            )
            if item.calloff:
                _apply_calloff_conflict(link, item.calloff)
            candidate_links = links_for_site(candidate.site_code)
            _apply_operational_rules(link, candidate, len(candidate_links), config)
            _apply_acceptance_filters(link, candidate, len(candidate_links), acceptance_config)
            if link.status == "REJECTED":
                rejected.append(item)
            else:
                accepted.append(item)
                ring_accepted += 1
            processed += 1
        if ring_accepted or await should_cancel():
            break

    accepted.sort(key=lambda item: item.link.score, reverse=True)
    for rank, item in enumerate(accepted, start=1):
        item.rank = rank

    elapsed = round(perf_counter() - started_at, 3)
    return SingleLinkPlanResult(
        best_candidate=accepted[0] if accepted else None,
        candidate_links=accepted,
        rejected_links=rejected,
        summary=PlanSummary(
            total_candidates=len(candidates),
            accepted=len(accepted),
            rejected=len(rejected),
            band=None,
            elapsed_seconds=elapsed,
            avg_seconds_per_link=round(elapsed / processed, 3) if processed else 0,
        ),
    )
