from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("MW_DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'data' / 'mwplanner.db').as_posix()}")

from app.database.session import SessionLocal, init_db  # noqa: E402
from app.schemas.planning import SingleLinkPlanRequest  # noqa: E402
from app.services.planner import plan_single_link  # noqa: E402
from app.terrain.downloader import download_gis_tiles, tiles_for_radius  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.services.site_lookup import site_lookup  # noqa: E402


TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
HELP_TEXT = """MW Pre-planning Telegram

Lệnh:
/plan site DN001 16.032 108.221 radius 30 height 30
/status
/site DN001

Bot sẽ tự kiểm tra GIS. Nếu thiếu DEM/WorldCover, bot tải GIS trước rồi mới chạy planning.
"""


def _worldcover_tile_name(lat_floor: int, lon_floor: int) -> str:
    lat_origin = (lat_floor // 3) * 3
    lon_origin = (lon_floor // 3) * 3
    ns = "N" if lat_origin >= 0 else "S"
    ew = "E" if lon_origin >= 0 else "W"
    return f"ESA_WorldCover_10m_2020_v100_{ns}{abs(lat_origin):02d}{ew}{abs(lon_origin):03d}_Map.tif"


def _worldcover_tiles_for_radius(latitude: float, longitude: float, radius_km: float) -> list[str]:
    import math

    lat_delta = radius_km / 111.0
    lon_scale = max(math.cos(math.radians(latitude)), 0.1)
    lon_delta = radius_km / (111.0 * lon_scale)
    min_lat = math.floor(latitude - lat_delta)
    max_lat = math.floor(latitude + lat_delta)
    min_lon = math.floor(longitude - lon_delta)
    max_lon = math.floor(longitude + lon_delta)
    return sorted(
        {
            _worldcover_tile_name(lat, lon)
            for lat in range(min_lat, max_lat + 1)
            for lon in range(min_lon, max_lon + 1)
        }
    )


def parse_plan(text: str) -> SingleLinkPlanRequest | None:
    normalized = text.replace(",", " ")
    numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", normalized)]
    coordinate: tuple[float, float] | None = None
    for index in range(len(numbers) - 1):
        lat = numbers[index]
        lon = numbers[index + 1]
        if abs(lat) <= 90 and abs(lon) <= 180 and abs(lon) > 90:
            coordinate = (lat, lon)
            break
    if coordinate is None:
        return None

    latitude, longitude = coordinate

    site_match = re.search(r"(?:site|ten|t[eê]n|name)\s+([A-Za-z][A-Za-z0-9_-]{2,})", text, re.IGNORECASE)
    if site_match is None:
        site_match = re.search(r"/plan\s+([A-Za-z][A-Za-z0-9_-]{2,})", text, re.IGNORECASE)
    radius_match = re.search(r"(?:radius|ban kinh|b[aá]n k[ií]nh|r)\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
    height_match = re.search(r"(?:height|tower|cao|cot|c[oộ]t)\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)

    return SingleLinkPlanRequest(
        site_name=(site_match.group(1).upper() if site_match else "NEW_SITE"),
        latitude=latitude,
        longitude=longitude,
        radius_km=float(radius_match.group(1)) if radius_match else 30,
        tower_height_m=float(height_match.group(1)) if height_match else 30,
        band="AUTO",
    )


def parse_plan(text: str) -> SingleLinkPlanRequest | None:
    normalized = text.replace(",", " ")
    numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", normalized)]
    coordinate: tuple[float, float] | None = None
    for index in range(len(numbers) - 1):
        lat = numbers[index]
        lon = numbers[index + 1]
        if abs(lat) <= 90 and abs(lon) <= 180 and abs(lon) > 90:
            coordinate = (lat, lon)
            break
    if coordinate is None:
        return None

    latitude, longitude = coordinate
    site_match = re.search(r"(?:site|ten|t[eê]n|name)\s+([A-Za-z][A-Za-z0-9_-]{2,})", text, re.IGNORECASE)
    if site_match is None:
        site_match = re.search(r"/plan\s+([A-Za-z][A-Za-z0-9_-]{2,})", text, re.IGNORECASE)
    min_radius_pattern = (
        r"(?:min[_\s-]*(?:radius|r)|minimum[_\s-]*(?:radius|r)|min\s+ban\s+kinh|"
        r"ban\s+kinh\s+toi\s+thieu|b[aá]n\s+k[ií]nh\s+t[oố]i\s+thi[eể]u)\s*[:=]?\s*(\d+(?:\.\d+)?)"
    )
    min_radius_match = re.search(min_radius_pattern, text, re.IGNORECASE)
    radius_source = re.sub(min_radius_pattern, " ", text, flags=re.IGNORECASE)
    radius_match = re.search(r"(?:radius|ban kinh|b[aá]n k[ií]nh|r)\s*[:=]?\s*(\d+(?:\.\d+)?)", radius_source, re.IGNORECASE)
    height_match = re.search(r"(?:height|tower|cao|cot|c[oộ]t)\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)

    return SingleLinkPlanRequest(
        site_name=(site_match.group(1).upper() if site_match else "NEW_SITE"),
        latitude=latitude,
        longitude=longitude,
        radius_km=float(radius_match.group(1)) if radius_match else 30,
        min_radius_km=float(min_radius_match.group(1)) if min_radius_match else None,
        tower_height_m=float(height_match.group(1)) if height_match else 30,
        band="AUTO",
    )


def parse_site_lookup(text: str) -> str | None:
    command = re.search(r"^/(?:site|lookup|tram)\s+([A-Za-z][A-Za-z0-9_-]{2,})\s*$", text, re.IGNORECASE)
    if command:
        return command.group(1).upper()
    direct_code = re.search(r"^\s*([A-Za-z]{2,}[A-Za-z0-9_-]*\d[A-Za-z0-9_-]*)\s*$", text)
    if direct_code:
        return direct_code.group(1).upper()
    if re.search(
        r"tra\s*cứu|tra\s*cuu|thông\s*tin|thong\s*tin|trạm|tram|tuyến\s*mw|tuyen\s*mw|cell|vu\s*hồi|vu\s*hoi|overload",
        text,
        re.IGNORECASE,
    ):
        code = re.search(r"\b([A-Za-z]{2,}[A-Za-z0-9_-]*\d[A-Za-z0-9_-]*)\b", text)
        if code:
            return code.group(1).upper()
    return None


def ensure_gis(request: SingleLinkPlanRequest) -> str:
    settings = get_settings()
    dem_missing = [
        tile
        for tile in tiles_for_radius(request.latitude, request.longitude, request.radius_km or 30)
        if not (settings.dem_directory / f"{tile}.tif").exists()
    ]
    worldcover_missing = [
        tile
        for tile in _worldcover_tiles_for_radius(request.latitude, request.longitude, request.radius_km or 30)
        if not (settings.worldcover_directory / tile).exists()
    ]
    if not dem_missing and not worldcover_missing:
        return "GIS OK."

    result = download_gis_tiles(request.latitude, request.longitude, request.radius_km or 30)
    failed = len(result.dem.failed_tiles) + len(result.worldcover.failed_tiles)
    summary = (
        f"GIS auto-download: DEM new {len(result.dem.downloaded_tiles)}, existing {len(result.dem.existing_tiles)}, failed {len(result.dem.failed_tiles)}; "
        f"WorldCover new {len(result.worldcover.downloaded_tiles)}, existing {len(result.worldcover.existing_tiles)}, failed {len(result.worldcover.failed_tiles)}."
    )
    if failed:
        raise RuntimeError(summary)
    return summary


def format_result(request: SingleLinkPlanRequest) -> str:
    with SessionLocal() as db:
        result = plan_single_link(db, request)

    lines = [
        f"Done {request.site_name}: {result.summary.total_candidates} candidates, {result.summary.accepted} accepted, {result.summary.rejected} rejected.",
    ]
    if result.best_candidate:
        best = result.best_candidate
        lines.append(
            f"Best: {best.candidate.site_code} | {best.link.distance_km:.2f} km | {best.link.band} | score {best.link.score:.1f} | {best.link.status}"
        )
        if best.calloff:
            lines.append(
                f"Calloff: {best.calloff.line}, new az {best.calloff.new_site_azimuth_deg} deg, root az {best.calloff.root_site_azimuth_deg} deg."
            )
    else:
        lines.append("No accepted candidate.")

    top = result.candidate_links[:5]
    if top:
        lines.append("")
        lines.append("Top candidates:")
        for item in top:
            flags = ", ".join(item.link.risk_flags) or "-"
            lines.append(
                f"{item.rank}. {item.candidate.site_code}: {item.link.distance_km:.2f} km, {item.link.score:.1f}, {item.link.status}, {flags}"
            )
    return "\n".join(lines)


class TelegramBot:
    def __init__(self, token: str) -> None:
        self.token = token
        self.offset = 0
        self.client = httpx.AsyncClient(timeout=60)

    async def close(self) -> None:
        await self.client.aclose()

    async def call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.post(TELEGRAM_API.format(token=self.token, method=method), json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(str(data))
        return data

    async def send_message(self, chat_id: int, text: str) -> None:
        chunks = [text[index : index + 3900] for index in range(0, len(text), 3900)] or [""]
        for chunk in chunks:
            await self.call("sendMessage", {"chat_id": chat_id, "text": chunk})

    async def get_updates(self) -> list[dict[str, Any]]:
        data = await self.call("getUpdates", {"offset": self.offset, "timeout": 30, "allowed_updates": ["message"]})
        return data["result"]

    async def handle_message(self, message: dict[str, Any]) -> None:
        chat_id = message["chat"]["id"]
        text = (message.get("text") or "").strip()
        if text in {"/start", "/help"}:
            await self.send_message(chat_id, HELP_TEXT)
            return
        if text == "/status":
            settings = get_settings()
            await self.send_message(
                chat_id,
                f"DB: {os.environ['MW_DATABASE_URL']}\nDEM: {settings.dem_directory}\nWorldCover: {settings.worldcover_directory}",
            )
            return
        lookup_code = parse_site_lookup(text)
        if lookup_code:
            with SessionLocal() as db:
                await self.send_message(chat_id, site_lookup(db, lookup_code))
            return
        if text.startswith("/plan") or re.search(r"(quy hoach|quy hoạch|plan|site)", text, re.IGNORECASE):
            request = parse_plan(text)
            if request is None:
                await self.send_message(chat_id, "Sai cú pháp. Ví dụ: /plan site DN001 16.032 108.221 radius 30 height 30")
                return
            await self.send_message(chat_id, f"Checking GIS for {request.site_name}...")
            try:
                gis_message = await asyncio.to_thread(ensure_gis, request)
                await self.send_message(chat_id, gis_message)
                await self.send_message(chat_id, "Running planner...")
                result_message = await asyncio.to_thread(format_result, request)
                await self.send_message(chat_id, result_message)
            except Exception as exc:
                await self.send_message(chat_id, f"Failed: {exc}")
            return
        await self.send_message(chat_id, "Gõ /help để xem lệnh.")

    async def run(self) -> None:
        await self.call("deleteWebhook", {"drop_pending_updates": False})
        while True:
            try:
                updates = await self.get_updates()
                for update in updates:
                    self.offset = max(self.offset, update["update_id"] + 1)
                    if "message" in update:
                        await self.handle_message(update["message"])
            except httpx.HTTPError as exc:
                print(f"Telegram network error: {exc}", flush=True)
                await asyncio.sleep(5)
            except Exception as exc:
                print(f"Telegram bot error: {exc}", flush=True)
                await asyncio.sleep(2)


async def main() -> None:
    token = os.environ.get("MW_TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("Set MW_TELEGRAM_BOT_TOKEN before running the Telegram bot.")
    init_db()
    bot = TelegramBot(token)
    try:
        print("Telegram bot is running.", flush=True)
        await bot.run()
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
