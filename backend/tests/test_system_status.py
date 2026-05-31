from app.services.status import _dem_regions, _dem_unmapped_tiles


def test_dem_regions_include_dak_lak_for_central_highlands_tiles():
    regions = _dem_regions(["N12E107", "N12E108"])

    assert "Dak Lak" in regions


def test_dem_regions_include_binh_thuan_for_south_central_tile():
    regions = _dem_regions(["N10E108"])

    assert "Binh Thuan" in regions


def test_dem_regions_include_all_provinces_inside_loaded_tiles():
    regions = _dem_regions(["N11E108", "N12E108"])

    assert "Dak Lak" in regions
    assert "Gia Lai" in regions
    assert "Khanh Hoa" in regions
    assert "Lam Dong" in regions


def test_dem_regions_include_hue_for_hue_tiles():
    regions = _dem_regions(["N16E107", "N16E108"])

    assert "Hue" in regions


def test_dem_unmapped_tiles_are_reported():
    unmapped = _dem_unmapped_tiles(["N10E108", "N01E001"])

    assert unmapped == ["N01E001"]
