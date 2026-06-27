from types import SimpleNamespace

from app.schemas.planning import SingleLinkPlanRequest
from app.services.planner import _candidate_scan_rings, _radius_scan_candidates


def test_candidate_scan_collects_all_candidates_inside_max_radius(monkeypatch):
    candidates = [
        SimpleNamespace(site_code="TOO_NEAR", distance_km=0.9),
        SimpleNamespace(site_code="NEAR1", distance_km=2.2),
        SimpleNamespace(site_code="NEAR2", distance_km=2.8),
        SimpleNamespace(site_code="FAR1", distance_km=3.1),
    ]
    monkeypatch.setattr("app.services.planner.search_sites", lambda db, lat, lon, radius: candidates)

    selected = _radius_scan_candidates(
        None,
        SingleLinkPlanRequest(site_name="NEW001", latitude=12.0, longitude=108.0, radius_km=30),
        30,
    )

    assert [candidate.site_code for candidate in selected] == ["NEAR1", "NEAR2", "FAR1"]


def test_candidate_scan_keeps_one_km_candidate(monkeypatch):
    candidates = [
        SimpleNamespace(site_code="ROOT1", distance_km=0.999),
        SimpleNamespace(site_code="ROOT2", distance_km=1.0),
    ]
    monkeypatch.setattr("app.services.planner.search_sites", lambda db, lat, lon, radius: candidates)

    selected = _radius_scan_candidates(
        None,
        SingleLinkPlanRequest(site_name="NEW001", latitude=12.0, longitude=108.0, radius_km=30),
        30,
    )

    assert [candidate.site_code for candidate in selected] == ["ROOT2"]


def test_candidate_scan_respects_request_min_radius(monkeypatch):
    candidates = [
        SimpleNamespace(site_code="ROOT1", distance_km=1.0),
        SimpleNamespace(site_code="ROOT2", distance_km=4.999),
        SimpleNamespace(site_code="ROOT3", distance_km=5.0),
        SimpleNamespace(site_code="ROOT4", distance_km=5.5),
    ]
    monkeypatch.setattr("app.services.planner.search_sites", lambda db, lat, lon, radius: candidates)

    selected = _radius_scan_candidates(
        None,
        SingleLinkPlanRequest(site_name="NEW001", latitude=12.0, longitude=108.0, radius_km=30, min_radius_km=5),
        30,
    )

    assert [candidate.site_code for candidate in selected] == ["ROOT3", "ROOT4"]


def test_candidate_scan_rings_group_candidates_by_one_km_expansion():
    candidates = [
        SimpleNamespace(site_code="NEAR1", distance_km=2.2),
        SimpleNamespace(site_code="NEAR2", distance_km=2.8),
        SimpleNamespace(site_code="FAR1", distance_km=3.1),
    ]

    rings = _candidate_scan_rings(candidates, 30)

    assert [[candidate.site_code for candidate in ring] for ring in rings] == [["NEAR1", "NEAR2"], ["FAR1"]]


def test_candidate_scan_excludes_input_site_before_selecting_ring(monkeypatch):
    candidates = [
        SimpleNamespace(site_code="NEW001", distance_km=0.0),
        SimpleNamespace(site_code="ROOT1", distance_km=4.4),
        SimpleNamespace(site_code="ROOT2", distance_km=5.1),
    ]
    monkeypatch.setattr("app.services.planner.search_sites", lambda db, lat, lon, radius: candidates)

    selected = _radius_scan_candidates(
        None,
        SingleLinkPlanRequest(site_name="NEW001", latitude=12.0, longitude=108.0, radius_km=30),
        30,
    )

    assert [candidate.site_code for candidate in selected] == ["ROOT1", "ROOT2"]
