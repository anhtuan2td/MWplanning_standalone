from pathlib import Path
from types import SimpleNamespace

from app.terrain import downloader
from app.terrain.dem import DemSampler


def test_download_dem_tiles_clears_sampler_cache(tmp_path, monkeypatch):
    settings = type(
        "Settings",
        (),
        {
            "dem_directory": tmp_path,
            "dem_source": "copernicus",
            "copernicus_dem_base_url": "https://example.com/copernicus",
        },
    )()
    monkeypatch.setattr(downloader, "get_settings", lambda: settings)
    monkeypatch.setattr(downloader, "tiles_for_radius", lambda latitude, longitude, radius_km: ["N12E108"])
    monkeypatch.setattr(downloader, "urlretrieve", lambda url, path: path.write_text("tif"))

    DemSampler._dataset_cache[tmp_path.resolve()] = ["cached"]

    result = downloader.download_dem_tiles(12.6, 108.0, 30)

    assert result.downloaded_tiles == ["N12E108"]
    assert DemSampler._dataset_cache == {}


def test_copernicus_tile_url_uses_public_cog_key(monkeypatch):
    settings = type("Settings", (), {"copernicus_dem_base_url": "https://example.com/copernicus"})()
    monkeypatch.setattr(downloader, "get_settings", lambda: settings)

    assert downloader._copernicus_tile_url("N16E107") == (
        "https://example.com/copernicus/"
        "Copernicus_DSM_COG_10_N16_00_E107_00_DEM/"
        "Copernicus_DSM_COG_10_N16_00_E107_00_DEM.tif"
    )


def test_copernicus_fallback_uses_skadi_hgt(tmp_path, monkeypatch):
    settings = type(
        "Settings",
        (),
        {
            "dem_directory": tmp_path,
            "dem_source": "copernicus",
            "copernicus_dem_base_url": "https://example.com/copernicus",
        },
    )()
    urls: list[str] = []

    def fake_urlretrieve(url, path):
        urls.append(url)
        if "copernicus" in url:
            raise OSError("copernicus unavailable")
        path.write_bytes(b"gz")

    monkeypatch.setattr(downloader, "get_settings", lambda: settings)
    monkeypatch.setattr(downloader, "tiles_for_radius", lambda latitude, longitude, radius_km: ["N12E108"])
    monkeypatch.setattr(downloader, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(downloader, "_convert_hgt_gz_to_tif", lambda gz_path, tif_path: tif_path.write_text("tif"))

    result = downloader.download_dem_tiles(12.6, 108.0, 30)

    assert result.downloaded_tiles == ["N12E108"]
    assert urls[-1] == "https://s3.amazonaws.com/elevation-tiles-prod/skadi/N12/N12E108.hgt.gz"


def test_worldcover_tiles_use_three_degree_esa_tiles():
    assert downloader._worldcover_tiles_for_radius(12.6, 108.0, 30) == [
        "ESA_WorldCover_10m_2020_v100_N12E105_Map.tif",
        "ESA_WorldCover_10m_2020_v100_N12E108_Map.tif"
    ]


def test_sample_surface_adds_worldcover_offsets(monkeypatch):
    settings = type(
        "Settings",
        (),
        {
            "dem_directory": Path("/tmp/dem"),
            "worldcover_directory": Path("/tmp/worldcover"),
            "worldcover_apply_height_offsets": True,
            "worldcover_height_offsets": {50: 15.0},
        },
    )()
    monkeypatch.setattr("app.terrain.dem.get_settings", lambda: settings)

    class FakeRaster:
        def __init__(self, bounds, value):
            self.bounds = bounds
            self._value = value

        def sample(self, coordinates):
            yield [self._value]

        def close(self):
            pass

    sampler = DemSampler()
    sampler._dataset_cache.clear()
    sampler._worldcover_dataset_cache.clear()
    monkeypatch.setattr(sampler, "_load", lambda: [FakeRaster(SimpleNamespace(left=0, right=10, bottom=0, top=10), 100.0)])
    monkeypatch.setattr(sampler, "_load_worldcover", lambda: [FakeRaster(SimpleNamespace(left=0, right=10, bottom=0, top=10), 50)])

    result = sampler.sample_surface(5.0, 5.0, fallback_m=0.0)

    assert result == 115.0
