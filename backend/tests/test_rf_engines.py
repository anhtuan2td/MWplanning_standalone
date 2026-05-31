from app.rf.fresnel import fresnel_clearance
from app.rf.los import check_los
from app.schemas.planning import Endpoint
from app.services.planner import _normalize_site_code
from app.terrain.downloader import tiles_for_radius
from app.terrain.profile import generate_profile


def test_los_and_fresnel_clear_for_simple_link():
    a = Endpoint(latitude=16.032, longitude=108.221, ground_elevation_m=10, tower_height_m=35)
    b = Endpoint(latitude=16.0471, longitude=108.2068, ground_elevation_m=12, tower_height_m=35)

    profile = generate_profile(a, b, step_m=200)
    los_pass, worst_clearance_m, _ = check_los(profile)
    fresnel_percent, minimum_clearance_m = fresnel_clearance(profile, "18GHz")

    assert los_pass is True
    assert worst_clearance_m > 1
    assert fresnel_percent > 40
    assert minimum_clearance_m > 1


def test_site_code_normalization_for_self_link_filter():
    assert _normalize_site_code(" dng0081 ") == "DNG0081"


def test_dem_tile_selection_for_radius():
    assert tiles_for_radius(16.032, 108.221, 30) == ["N15E107", "N15E108", "N16E107", "N16E108"]
