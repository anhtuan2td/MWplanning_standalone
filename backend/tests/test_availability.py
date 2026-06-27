from app.rf.availability import estimate_availability, estimate_availability_details
from app.scoring.scorer import score_link


def test_heavier_rain_and_longer_link_reduce_availability():
    dry, _ = estimate_availability(2, "18GHz", "A")
    wet, zone = estimate_availability(8, "18GHz", "N")
    assert zone == "N"
    assert wet < dry


def test_availability_changes_candidate_score():
    common = dict(los_pass=True, worst_clearance_m=10, fresnel_percent=80, distance_km=2, band="18GHz", tower_margin_m=10)
    good, _, _ = score_link(**common, availability_percent=99.999)
    near_target, _, near_flags = score_link(**common, availability_percent=99.98)
    poor, _, flags = score_link(**common, availability_percent=99.9)
    assert near_target < good
    assert "LOW_AVAILABILITY" not in near_flags
    assert poor < good
    assert "LOW_AVAILABILITY" in flags


def test_ray3_profile_uses_link_budget_and_fade_margin():
    details = estimate_availability_details(1.0, "24GHz", "N", antenna_diameter_m=0.6)
    assert details["equipment_profile"] == "RACOM_RAy3_24_56_256QAM"
    assert details["fade_margin_db"] > 0
    assert 95 < details["availability_percent"] <= 100
