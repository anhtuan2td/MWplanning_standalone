from pathlib import Path

from app.services import mw_links


def test_import_existing_links_writes_to_runtime_directory(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime_mw_links"
    default_file = tmp_path / "bundled" / "existing_links.csv"
    default_file.parent.mkdir()
    settings = type(
        "Settings",
        (),
        {
            "mw_links_directory": runtime_dir,
            "default_mw_links_file": default_file,
        },
    )()
    monkeypatch.setattr(mw_links, "get_settings", lambda: settings)
    mw_links.load_existing_links.cache_clear()

    content = (
        "sitecode_a,sitecode_b,freq_a,freq_b,antenna_diameter_a,antenna_diameter_b,height_a_m,height_b_m,distance_km\n"
        "A001,B001,18GHz Low,18GHz High,0.6,0.6,30,30,2.5\n"
    ).encode()

    result = mw_links.import_existing_links_csv(content)

    assert result == {"imported": 1}
    assert (runtime_dir / "current_links.csv").read_bytes() == content

    mw_links.load_existing_links.cache_clear()
