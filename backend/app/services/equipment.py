import csv
import io
from functools import lru_cache
from pathlib import Path

from app.core.config import get_planner_config


FIELDS = ("profile_id", "vendor", "model", "band_ghz", "channel_bw_mhz", "modulation", "capacity_mbps", "rx_threshold_dbm", "tx_power_min_dbm", "tx_power_max_dbm")
NUMERIC_FIELDS = set(FIELDS[3:5] + FIELDS[6:])
CATALOG_PATH = Path(__file__).resolve().parents[3] / "data" / "equipment" / "equipment_profiles.csv"


def _validated(row: dict[str, str], line: int) -> dict[str, str | float]:
    missing = [field for field in FIELDS if not str(row.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Line {line}: missing {', '.join(missing)}")
    result: dict[str, str | float] = {}
    for field in FIELDS:
        value = str(row[field]).strip()
        result[field] = float(value) if field in NUMERIC_FIELDS else value
    if float(result["band_ghz"]) <= 0 or float(result["channel_bw_mhz"]) <= 0:
        raise ValueError(f"Line {line}: band/channel bandwidth must be positive")
    return result


@lru_cache(maxsize=1)
def _list_equipment_profiles_cached(mtime_ns: int, size: int) -> tuple[tuple[tuple[str, str | float], ...], ...]:
    if not CATALOG_PATH.exists():
        return ()
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
        return tuple(
            tuple(_validated(row, index).items())
            for index, row in enumerate(csv.DictReader(stream), 2)
        )


def list_equipment_profiles() -> list[dict[str, str | float]]:
    if not CATALOG_PATH.exists():
        return []
    stat = CATALOG_PATH.stat()
    return [dict(row) for row in _list_equipment_profiles_cached(stat.st_mtime_ns, stat.st_size)]


def equipment_profile(profile_id: str | None) -> tuple[str, dict | None]:
    default_id = str(get_planner_config().get("availability", {}).get("default_equipment_profile", ""))
    selected = profile_id or default_id
    for profile in list_equipment_profiles():
        if profile["profile_id"] == selected:
            return selected, profile
    legacy = get_planner_config().get("availability", {}).get("equipment_profiles", {}).get(selected)
    return selected, legacy


def import_equipment_profiles(content: bytes) -> dict[str, int]:
    text = content.decode("utf-8-sig")
    incoming = [_validated(row, index) for index, row in enumerate(csv.DictReader(io.StringIO(text)), 2)]
    merged = {str(row["profile_id"]): row for row in list_equipment_profiles()}
    before = len(merged)
    for row in incoming:
        merged[str(row["profile_id"])] = row
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(merged.values())
    _list_equipment_profiles_cached.cache_clear()
    return {"imported": len(incoming), "total": len(merged), "added": len(merged) - before}
