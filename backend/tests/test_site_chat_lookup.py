from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.site import Base, Site
from app.services.site_lookup import site_lookup
from scripts.telegram_bot import parse_plan, parse_site_lookup


def test_plan_parser_accepts_min_radius():
    request = parse_plan("/plan site DN001 16.032 108.221 radius 30 min_radius 5 height 30")
    assert request is not None
    assert request.radius_km == 30
    assert request.min_radius_km == 5


def test_plan_parser_does_not_treat_min_radius_as_scan_radius():
    request = parse_plan("/plan site DN001 16.032 108.221 min_radius 1 height 30")
    assert request is not None
    assert request.radius_km == 30
    assert request.min_radius_km == 1


def test_lookup_parser_accepts_command_direct_code_and_natural_language():
    assert parse_site_lookup("/site BDH0001") == "BDH0001"
    assert parse_site_lookup("/lookup bdh0001") == "BDH0001"
    assert parse_site_lookup("BDH0001") == "BDH0001"
    assert parse_site_lookup("trạm BDH0001 có bao nhiêu cell 4G?") == "BDH0001"
    assert parse_site_lookup("BDH0001 đã vu hồi chưa?") == "BDH0001"


def test_site_lookup_reports_cells_routing_and_overload():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(
            Site(
                site_code="TEST001",
                site_name="Test",
                latitude=0,
                longitude=0,
                cells_4g=6,
                cells_5g=3,
                diverse_routing=True,
                overload=2,
            )
        )
        db.commit()
        answer = site_lookup(db, "test001")
    assert "4G = 6; 5G = 3" in answer
    assert "Vu hồi: Có" in answer
    assert "Overload: Có; hệ số = 2" in answer
