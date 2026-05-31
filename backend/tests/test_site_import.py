from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.site import Base, Site
from app.services.sites import import_sites_csv


def test_import_accepts_missing_elevation_and_extra_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    content = (
        "site_code,site_name,latitude,longitude,tower_height_m,available_height_m,status,owner\n"
        "A001,Alpha,10.1,100.1,42,35,active,MW\n"
    ).encode()

    with session_factory() as db:
        result = import_sites_csv(db, content)
        site = db.query(Site).filter(Site.site_code == "A001").one()

    assert result.inserted == 1
    assert result.skipped == 0
    assert site.ground_elevation_m == 0
    assert site.available_height_m == 35


def test_import_accepts_windows_encoded_csv_and_seven_char_site_code():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    content = (
        "site_code,site_name,latitude,longitude,status\n"
        "DN00001,Mi An,10.05,100.24,active\n"
    ).replace("Mi", "Mì").encode("cp1252")

    with session_factory() as db:
        result = import_sites_csv(db, content)
        site = db.query(Site).filter(Site.site_code == "DN00001").one()

    assert result.inserted == 1
    assert result.skipped == 0
    assert site.site_code == "DN00001"
    assert site.latitude == 10.05


def test_import_accepts_vh_as_diverse_routing_flag():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    content = (
        "site_code,site_name,latitude,longitude,tower_height_m,available_height_m,status,owner,region,overload,VH\n"
        "DN001,Da Nang Core 01,16.0471,108.2068,45,40,active,MW Team,Da Nang,,1\n"
        "DN002,Da Nang Core 02,16.0802,108.2205,42,35,active,MW Team,Da Nang,2,\n"
    ).encode()

    with session_factory() as db:
        result = import_sites_csv(db, content)
        diverse_site = db.query(Site).filter(Site.site_code == "DN001").one()
        overload_site = db.query(Site).filter(Site.site_code == "DN002").one()

    assert result.inserted == 2
    assert result.skipped == 0
    assert diverse_site.diverse_routing is True
    assert diverse_site.overload == 0
    assert overload_site.overload == 2
    assert overload_site.diverse_routing is False
