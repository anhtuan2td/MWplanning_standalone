from pathlib import Path

from app.schemas.planning import SingleLinkPlanRequest
from app.services.gis_preflight import check_batch_gis_coverage
from app.terrain.downloader import central_region_gis_tiles


def test_batch_gis_preflight_reports_missing_tiles(tmp_path, monkeypatch):
    dem_dir = tmp_path / "dem"
    worldcover_dir = tmp_path / "worldcover"
    dem_dir.mkdir()
    worldcover_dir.mkdir()

    settings = type(
        "Settings",
        (),
        {
            "dem_directory": dem_dir,
            "worldcover_directory": worldcover_dir,
            "worldcover_apply_height_offsets": True,
        },
    )()
    monkeypatch.setattr("app.services.gis_preflight.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.gis_preflight.get_planner_config", lambda: {"candidate_radius_km": 1})

    result = check_batch_gis_coverage(
        [SingleLinkPlanRequest(site_name="NEW001", latitude=12.6, longitude=108.0, radius_km=1)]
    )
    coverage = result["0:NEW001"]

    assert coverage.status == "GIS_MISSING"
    assert "N12E107" in coverage.missing_dem_tiles
    assert "ESA_WorldCover_10m_2020_v100_N12E108_Map.tif" in coverage.missing_worldcover_tiles


def test_batch_gis_preflight_accepts_existing_tiles(tmp_path, monkeypatch):
    dem_dir = tmp_path / "dem"
    worldcover_dir = tmp_path / "worldcover"
    dem_dir.mkdir()
    worldcover_dir.mkdir()
    for tile in ("N12E107", "N12E108"):
        Path(dem_dir / f"{tile}.tif").touch()
    Path(worldcover_dir / "ESA_WorldCover_10m_2020_v100_N12E105_Map.tif").touch()
    Path(worldcover_dir / "ESA_WorldCover_10m_2020_v100_N12E108_Map.tif").touch()

    settings = type(
        "Settings",
        (),
        {
            "dem_directory": dem_dir,
            "worldcover_directory": worldcover_dir,
            "worldcover_apply_height_offsets": True,
        },
    )()
    monkeypatch.setattr("app.services.gis_preflight.get_settings", lambda: settings)
    monkeypatch.setattr("app.services.gis_preflight.get_planner_config", lambda: {"candidate_radius_km": 1})

    result = check_batch_gis_coverage(
        [SingleLinkPlanRequest(site_name="NEW001", latitude=12.6, longitude=108.0, radius_km=1)]
    )
    coverage = result["0:NEW001"]

    assert coverage.status == "DEM+WORLDCOVER_OK"
    assert coverage.missing_dem_tiles == []
    assert coverage.missing_worldcover_tiles == []


def test_central_region_gis_tiles_cover_quang_tri_to_lam_dong_band():
    dem_tiles, worldcover_tiles = central_region_gis_tiles()

    assert "N18E105" in dem_tiles
    assert "N10E109" in dem_tiles
    assert len(dem_tiles) == 45
    assert "ESA_WorldCover_10m_2020_v100_N09E105_Map.tif" in worldcover_tiles
    assert "ESA_WorldCover_10m_2020_v100_N18E108_Map.tif" in worldcover_tiles
