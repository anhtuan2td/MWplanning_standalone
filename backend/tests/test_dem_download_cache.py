from app.terrain import downloader
from app.terrain.dem import DemSampler


def test_download_dem_tiles_clears_sampler_cache(tmp_path, monkeypatch):
    settings = type("Settings", (), {"dem_directory": tmp_path})()
    monkeypatch.setattr(downloader, "get_settings", lambda: settings)
    monkeypatch.setattr(downloader, "tiles_for_radius", lambda latitude, longitude, radius_km: ["N12E108"])
    monkeypatch.setattr(downloader, "_convert_hgt_gz_to_tif", lambda gz_path, tif_path: tif_path.write_text("tif"))
    monkeypatch.setattr(downloader, "urlretrieve", lambda url, path: path.write_text("gz"))

    DemSampler._dataset_cache[tmp_path.resolve()] = ["cached"]

    result = downloader.download_dem_tiles(12.6, 108.0, 30)

    assert result.downloaded_tiles == ["N12E108"]
    assert DemSampler._dataset_cache == {}
