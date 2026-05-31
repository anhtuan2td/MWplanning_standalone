from __future__ import annotations

import csv
import re
import shutil
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import get_planner_config, get_settings


def _runtime_link_file() -> Path:
    return get_settings().mw_links_directory / "current_links.csv"


def _default_link_file() -> Path:
    return get_settings().default_mw_links_file


@dataclass(frozen=True)
class ExistingMwLink:
    site_a: str
    freq_a: str
    antenna_diameter_a_m: float
    height_a_m: float
    site_b: str
    freq_b: str
    antenna_diameter_b_m: float
    height_b_m: float
    distance_km: float


def normalize_code(value: str) -> str:
    return "".join(value.upper().split())


def normalize_band(value: str) -> str:
    match = re.search(r"(\d+(?:\.\d+)?)\s*G", value.upper())
    if not match:
        return value.strip()
    band = match.group(1).rstrip("0").rstrip(".")
    return f"{band}GHz"


def band_group(value: str) -> str:
    band = normalize_band(value)
    if band in {"6GHz", "7GHz", "8GHz"}:
        return "6GHz"
    return band


def normalize_side(value: str) -> str:
    value = value.upper()
    if "HIGH" in value:
        return "high"
    if "LOW" in value:
        return "low"
    return ""


def _float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _header_key(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower().strip())
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", without_accents).strip()


def _get(row: dict[str, str], names: list[str]) -> str:
    normalized = {
        _header_key(key): (value or "")
        for key, value in row.items()
        if key is not None
    }
    for name in names:
        value = normalized.get(_header_key(name), "")
        if value.strip():
            return value.strip()
    return ""


def _frequency_for_side(row: dict[str, str], direct_names: list[str], side_names: list[str]) -> str:
    direct = _get(row, direct_names)
    if direct:
        return direct
    frequency = _get(row, ["frequency", "freq", "dai tan", "tan so"])
    side = _get(row, side_names)
    return " ".join(part for part in [frequency, side] if part)


@lru_cache
def load_existing_links(path: str | None = None) -> tuple[ExistingMwLink, ...]:
    runtime_link_file = _runtime_link_file()
    file_path = Path(path) if path else (runtime_link_file if runtime_link_file.exists() else _default_link_file())
    if not file_path.exists():
        return ()
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        links = []
        for row in reader:
            site_a = normalize_code(_get(row, ["sitecode a", "sitecode_a", "site_a", "a end", "a_end"]))
            site_b = normalize_code(_get(row, ["sitecode b", "sitecode_b", "site_b", "b end", "b_end"]))
            if not site_a or not site_b:
                continue
            links.append(
                ExistingMwLink(
                    site_a=site_a,
                    freq_a=_frequency_for_side(
                        row,
                        ["tan so site a", "freq_a", "frequency_a"],
                        ["band (a)", "band_a", "side_a", "polar_a"],
                    ),
                    antenna_diameter_a_m=_float(
                        _get(row, ["antena diameter (a)", "antenna diameter (a)", "antenna_diameter_a", "diameter_a"])
                    ),
                    height_a_m=_float(
                        _get(
                            row,
                            [
                                "do cao treo anten site a",
                                "height_a_m",
                                "antenna_height_a",
                                "elevation (a)",
                                "elevation_a",
                            ],
                        )
                    ),
                    site_b=site_b,
                    freq_b=_frequency_for_side(
                        row,
                        ["tan so site b", "freq_b", "frequency_b"],
                        ["band (b)", "band_b", "side_b", "polar_b"],
                    ),
                    antenna_diameter_b_m=_float(
                        _get(row, ["antena diameter (b)", "antenna diameter (b)", "antenna_diameter_b", "diameter_b"])
                    ),
                    height_b_m=_float(
                        _get(
                            row,
                            [
                                "do cao anten site b",
                                "height_b_m",
                                "antenna_height_b",
                                "elevation (b)",
                                "elevation_b",
                            ],
                        )
                    ),
                    distance_km=_float(_get(row, ["khoang cach", "distance_km", "distance"])),
                )
            )
        return tuple(links)


def links_for_site(site_code: str) -> list[ExistingMwLink]:
    code = normalize_code(site_code)
    return [link for link in load_existing_links() if link.site_a == code or link.site_b == code]


def side_for_site(link: ExistingMwLink, site_code: str) -> str:
    code = normalize_code(site_code)
    if link.site_a == code:
        return normalize_side(link.freq_a)
    if link.site_b == code:
        return normalize_side(link.freq_b)
    return ""


def band_for_site(link: ExistingMwLink, site_code: str) -> str:
    code = normalize_code(site_code)
    if link.site_a == code:
        return normalize_band(link.freq_a)
    if link.site_b == code:
        return normalize_band(link.freq_b)
    return ""


def height_for_site(link: ExistingMwLink, site_code: str) -> float:
    code = normalize_code(site_code)
    if link.site_a == code:
        return link.height_a_m
    if link.site_b == code:
        return link.height_b_m
    return 0.0


def antenna_diameter_for_site(link: ExistingMwLink, site_code: str) -> float:
    code = normalize_code(site_code)
    if link.site_a == code:
        return link.antenna_diameter_a_m
    if link.site_b == code:
        return link.antenna_diameter_b_m
    return 0.0


def lowest_height_for_site(site_code: str) -> float | None:
    heights = [height_for_site(link, site_code) for link in links_for_site(site_code)]
    valid_heights = [height for height in heights if height > 0]
    return min(valid_heights) if valid_heights else None


def other_site_code(link: ExistingMwLink, site_code: str) -> str:
    code = normalize_code(site_code)
    if link.site_a == code:
        return link.site_b
    if link.site_b == code:
        return link.site_a
    return ""


def suggested_antenna_diameter(band: str, distance_km: float) -> float:
    same_band = [link for link in load_existing_links() if normalize_band(link.freq_a) == band or normalize_band(link.freq_b) == band]
    if not same_band and band == "6GHz":
        same_band = [
            link
            for link in load_existing_links()
            if normalize_band(link.freq_a) in {"7GHz", "8GHz"} or normalize_band(link.freq_b) in {"7GHz", "8GHz"}
        ]

    def bucket(distance: float) -> int:
        for index, limit in enumerate((2, 5, 10, 20, 45)):
            if distance <= limit:
                return index
        return 5

    target_bucket = bucket(distance_km)
    candidates = [link for link in same_band if bucket(link.distance_km) == target_bucket] or same_band
    counts: dict[float, int] = {}
    for link in candidates:
        for value in (link.antenna_diameter_a_m, link.antenna_diameter_b_m):
            if value > 0:
                counts[value] = counts.get(value, 0) + 1
    if counts:
        return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return 0.6


def antenna_rule_table() -> list[dict[str, float | str]]:
    bands = sorted(
        (
            (band, float(config.get("max_distance_km", 0)))
            for band, config in get_planner_config().get("bands", {}).items()
            if float(config.get("max_distance_km", 0)) > 0
        ),
        key=lambda item: item[1],
    )
    rules = []
    previous_distance = 0.0
    for band, max_distance in bands:
        distance_label = f"<= {max_distance:g} km" if previous_distance == 0 else f"> {previous_distance:g} - {max_distance:g} km"
        rules.append(
            {
                "distance": distance_label,
                "band": band,
                "antenna_diameter_m": suggested_antenna_diameter(band, max_distance),
            }
        )
        previous_distance = max_distance
    return rules


def root_side_for_new_link(root_site_code: str, band: str) -> str:
    used_sides = used_sides_for_site_band(root_site_code, band)
    if not used_sides:
        return "low"
    if "low" not in used_sides:
        return "low"
    if "high" not in used_sides:
        return "high"
    return ""


def used_sides_for_site_band(root_site_code: str, band: str) -> set[str]:
    used_sides = set()
    for link in links_for_site(root_site_code):
        if band_group(band_for_site(link, root_site_code)) == band_group(band):
            existing_side = side_for_site(link, root_site_code)
            if existing_side:
                used_sides.add(existing_side)
    return used_sides


def import_existing_links_csv(content: bytes) -> dict[str, int]:
    runtime_link_file = _runtime_link_file()
    runtime_link_file.parent.mkdir(parents=True, exist_ok=True)
    backup_path = runtime_link_file.with_suffix(".csv.bak")
    if runtime_link_file.exists():
        shutil.copyfile(runtime_link_file, backup_path)
    runtime_link_file.write_bytes(content)
    load_existing_links.cache_clear()
    count = len(load_existing_links())
    return {"imported": count}
