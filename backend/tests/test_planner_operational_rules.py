from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.site import Base
from app.schemas.planning import AcceptedFilters, LinkCheckResult, TerrainProfile
from app.services.mw_links import ExistingMwLink, antenna_rule_table, band_group, lowest_height_for_site, root_side_for_new_link
from app.services.planner import _apply_acceptance_filters, _apply_calloff_conflict, _apply_operational_rules, _calloff, _effective_root_height


def _link() -> LinkCheckResult:
    return LinkCheckResult(
        distance_km=1.2,
        band="18GHz",
        los_pass=True,
        worst_clearance_m=8,
        worst_point_km=0.5,
        fresnel_clearance_percent=80,
        minimum_clearance_m=5,
        score=80,
        status="ACCEPTED",
        risk_flags=[],
        terrain_profile=TerrainProfile(
            distance_m=[0, 1200],
            terrain_elevation_m=[0, 0],
            effective_terrain_elevation_m=[0, 0],
            los_elevation_m=[30, 30],
        ),
    )


def test_overload_is_danger_not_rejected():
    link = _link()
    candidate = SimpleNamespace(site_code="BDH0001", overload=2, diverse_routing=False)

    _apply_operational_rules(
        link,
        candidate,
        existing_link_count=0,
        config={"scoring": {"overload_penalty": 30}},
    )

    assert link.status == "DANGER"
    assert link.score == 50
    assert "Danger - Overload 2" in link.risk_flags


def test_overlink_and_extended_rru_are_scored_and_not_rejected():
    link = _link()
    candidate = SimpleNamespace(site_code="BDH0001-41", overload=False, diverse_routing=False)

    _apply_operational_rules(
        link,
        candidate,
        existing_link_count=2,
        config={"scoring": {"overlink_penalty": 25, "extended_rru_penalty": 10}},
    )

    assert link.status == "OVERLINK"
    assert link.score == 45
    assert "Overlink" in link.risk_flags
    assert "RRU kéo dài" in link.risk_flags


def test_calloff_matches_mw_import_form_fields():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    new_endpoint = SimpleNamespace(latitude=13.7, longitude=109.1, ground_elevation_m=10)
    candidate = SimpleNamespace(
        site_code="BTN9706",
        latitude=13.75,
        longitude=109.2,
        ground_elevation_m=20,
    )

    with session_factory() as db:
        calloff = _calloff(db, "NEW001", new_endpoint, candidate, "7GHz", 30, 60, 8.2)

    assert calloff.line == "NEW001-BTN9706-01"
    assert calloff.frequency == "7GHz"
    assert calloff.new_site == "NEW001"
    assert calloff.new_site_band_side in {"High", "Low"}
    assert calloff.new_site_antenna_diameter_m > 0
    assert 0 <= calloff.new_site_azimuth_deg < 360
    assert calloff.root_site == "BTN9706"
    assert calloff.root_site_band_side in {"High", "Low"}
    assert calloff.root_site_antenna_diameter_m > 0
    assert 0 <= calloff.root_site_azimuth_deg < 360


def test_acceptance_filters_reject_blocked_code_overload_and_overlink():
    link = _link()
    candidate = SimpleNamespace(site_code="BDH0001-41", overload=1, diverse_routing=False)

    _apply_acceptance_filters(
        link,
        candidate,
        existing_link_count=2,
        config={
            "accepted_filters": {
                "reject_site_code_contains": "-",
                "reject_overload": True,
                "reject_overlink": True,
            }
        },
    )

    assert link.status == "REJECTED"
    assert "Acceptance filter - site_code contains -" in link.risk_flags
    assert "Acceptance filter - overload" in link.risk_flags
    assert "Acceptance filter - overlink" in link.risk_flags


def test_acceptance_filters_can_require_site_code_number_above_threshold():
    rejected = _link()
    accepted = _link()

    _apply_acceptance_filters(
        rejected,
        SimpleNamespace(site_code="BDH0099", overload=0),
        existing_link_count=0,
        config={"accepted_filters": {"min_site_code_number": 99}},
    )
    _apply_acceptance_filters(
        accepted,
        SimpleNamespace(site_code="BDH0100", overload=0),
        existing_link_count=0,
        config={"accepted_filters": {"min_site_code_number": 99}},
    )

    assert rejected.status == "REJECTED"
    assert "Acceptance filter - site_code number <= 99" in rejected.risk_flags
    assert accepted.status == "ACCEPTED"


def test_acceptance_filters_accept_request_model_with_all_toggles_off():
    link = _link()

    _apply_acceptance_filters(
        link,
        SimpleNamespace(site_code="BDH0001-41", overload=1),
        existing_link_count=2,
        config={"accepted_filters": AcceptedFilters()},
    )

    assert link.status == "ACCEPTED"
    assert link.risk_flags == []


def test_low_band_group_uses_existing_7ghz_side_for_6ghz_calloff(monkeypatch):
    link = ExistingMwLink(
        site_a="BTN9706",
        freq_a="7GHz Low",
        antenna_diameter_a_m=1.2,
        height_a_m=45,
        site_b="BTN9701",
        freq_b="7GHz High",
        antenna_diameter_b_m=1.2,
        height_b_m=45,
        distance_km=8,
    )
    monkeypatch.setattr("app.services.mw_links.load_existing_links", lambda: (link,))

    assert band_group("7GHz") == "6GHz"
    assert root_side_for_new_link("BTN9706", "6GHz") == "high"


def test_calloff_does_not_assign_side_when_both_high_low_are_used(monkeypatch):
    links = (
        ExistingMwLink(
            site_a="ROOT001",
            freq_a="6GHz Low",
            antenna_diameter_a_m=1.2,
            height_a_m=45,
            site_b="FAR001",
            freq_b="6GHz High",
            antenna_diameter_b_m=1.2,
            height_b_m=45,
            distance_km=8,
        ),
        ExistingMwLink(
            site_a="ROOT001",
            freq_a="7GHz High",
            antenna_diameter_a_m=1.2,
            height_a_m=42,
            site_b="FAR002",
            freq_b="7GHz Low",
            antenna_diameter_b_m=1.2,
            height_b_m=42,
            distance_km=9,
        ),
    )
    monkeypatch.setattr("app.services.mw_links.load_existing_links", lambda: links)

    assert root_side_for_new_link("ROOT001", "6GHz") == ""

    link = _link()
    calloff = SimpleNamespace(root_site_band_side="")
    _apply_calloff_conflict(link, calloff)

    assert link.status == "OVERLINK"
    assert "Band side conflict" in link.risk_flags


def test_calloff_root_height_is_not_above_lowest_existing_height(monkeypatch):
    links = (
        ExistingMwLink(
            site_a="ROOT001",
            freq_a="18GHz Low",
            antenna_diameter_a_m=0.6,
            height_a_m=35,
            site_b="FAR001",
            freq_b="18GHz High",
            antenna_diameter_b_m=0.6,
            height_b_m=35,
            distance_km=3,
        ),
        ExistingMwLink(
            site_a="ROOT001",
            freq_a="15GHz Low",
            antenna_diameter_a_m=0.6,
            height_a_m=28,
            site_b="FAR002",
            freq_b="15GHz High",
            antenna_diameter_b_m=0.6,
            height_b_m=28,
            distance_km=8,
        ),
    )
    monkeypatch.setattr("app.services.mw_links.load_existing_links", lambda: links)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    new_endpoint = SimpleNamespace(latitude=13.7, longitude=109.1, ground_elevation_m=10)
    candidate = SimpleNamespace(
        site_code="ROOT001",
        latitude=13.75,
        longitude=109.2,
        ground_elevation_m=20,
    )

    with session_factory() as db:
        calloff = _calloff(db, "NEW001", new_endpoint, candidate, "18GHz", 30, 60, 8.2)

    assert lowest_height_for_site("ROOT001") == 28
    assert calloff.root_site_height_m == 28


def test_effective_root_height_is_not_above_lowest_existing_height(monkeypatch):
    links = (
        ExistingMwLink(
            site_a="ROOT001",
            freq_a="18GHz Low",
            antenna_diameter_a_m=0.6,
            height_a_m=28,
            site_b="FAR001",
            freq_b="18GHz High",
            antenna_diameter_b_m=0.6,
            height_b_m=28,
            distance_km=3,
        ),
    )
    monkeypatch.setattr("app.services.mw_links.load_existing_links", lambda: links)

    candidate = SimpleNamespace(
        site_code="ROOT001",
        latitude=13.75,
        longitude=109.2,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        assert _effective_root_height(db, candidate, "18GHz", 45, 60) == 28


def test_antenna_rule_table_exposes_distance_band_and_antenna():
    rules = antenna_rule_table()

    assert rules[0]["distance"] == "<= 3 km"
    assert rules[0]["band"] == "24GHz"
    assert rules[0]["antenna_diameter_m"] > 0
