from app.services.status import _dem_regions, _dem_unmapped_tiles, _worldcover_regions, _worldcover_unmapped_maps


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


def test_dem_regions_include_quang_tri_for_north_central_tiles():
    regions = _dem_regions(["N16E106", "N17E106", "N17E107"])

    assert "Quang Tri" in regions


def test_dem_regions_include_coastal_merged_provinces_for_n13e109():
    regions = _dem_regions(["N13E109"])

    assert "Dak Lak" in regions
    assert "Gia Lai" in regions


def test_dem_unmapped_tiles_are_reported():
    unmapped = _dem_unmapped_tiles(["N10E108", "N01E001"])

    assert unmapped == ["N01E001"]


def test_worldcover_regions_expand_three_degree_maps_to_province_names():
    regions = _worldcover_regions(["ESA_WorldCover_10m_2020_v100_N15E105_Map"])

    assert "Quang Tri" in regions
    assert "Da Nang" in regions
    assert "Hue" in regions


def test_worldcover_unmapped_maps_are_reported_without_tile_codes_in_regions():
    unmapped = _worldcover_unmapped_maps(["ESA_WorldCover_10m_2020_v100_N00E000_Map"])

    assert unmapped == ["ESA_WorldCover_10m_2020_v100_N00E000_Map"]
