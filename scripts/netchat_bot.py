from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("MW_DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'data' / 'mwplanner.db').as_posix()}")

from app.database.session import init_db  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from scripts.telegram_bot import ensure_gis, format_result, parse_plan  # noqa: E402
from scripts.netchat_send import (  # noqa: E402
    build_netchat_auth,
    login_netchat_cookie,
    netchat_base_url,
    required_env,
    send_netchat_message,
)


HELP_TEXT = """MW Pre-planning NetChat

Lenh:
/plan site DN001 16.032 108.221 radius 30 height 30
/status

Bot se tu kiem tra GIS. Neu thieu DEM/WorldCover, bot tai GIS truoc roi moi chay planning.
"""


class NetChatBot:
    def __init__(self, endpoint: str, token: str, channel_id: str) -> None:
        self.endpoint = endpoint
        self.base_url = netchat_base_url(endpoint)
        self.token = token
        self.channel_id = channel_id
        self.poll_seconds = float(os.environ.get("NETCHAT_POLL_SECONDS", "4"))
        self.skip_existing = os.environ.get("NETCHAT_SKIP_EXISTING", "1") != "0"
        self.last_create_at = 0
        self.seen_post_ids: set[str] = set()
        self.bot_user_id = os.environ.get("NETCHAT_BOT_USER_ID", "")
        self.client = httpx.AsyncClient(timeout=60)

    async def close(self) -> None:
        await self.client.aclose()

    def auth(self) -> tuple[dict[str, str], dict[str, str]]:
        return build_netchat_auth(self.token, self.endpoint)

    async def get_posts(self) -> list[dict[str, Any]]:
        headers, cookies = self.auth()
        url = f"{self.base_url}/api/v4/channels/{self.channel_id}/posts"
        response = await self.client.get(url, headers=headers, cookies=cookies, params={"page": 0, "per_page": 30})
        if response.is_error:
            detail = response.text.strip()
            raise RuntimeError(
                f"NetChat read returned {response.status_code} {response.reason_phrase}. "
                f"Response: {detail or '<empty response>'}"
            )
        data = response.json()
        order = data.get("order", [])
        posts = data.get("posts", {})
        result = [posts[post_id] for post_id in reversed(order) if post_id in posts]
        return result

    async def send(self, text: str) -> None:
        chunks = [text[index : index + 3900] for index in range(0, len(text), 3900)] or [""]
        for chunk in chunks:
            await send_netchat_message(self.endpoint, self.token, self.channel_id, chunk)

    async def handle_post(self, post: dict[str, Any]) -> None:
        post_id = str(post.get("id", ""))
        if not post_id or post_id in self.seen_post_ids:
            return
        self.seen_post_ids.add(post_id)

        create_at = int(post.get("create_at") or 0)
        self.last_create_at = max(self.last_create_at, create_at)

        if self.bot_user_id and post.get("user_id") == self.bot_user_id:
            return
        text = (post.get("message") or "").strip()
        if not text:
            return

        if text in {"/help", "help"}:
            await self.send(HELP_TEXT)
            return
        if text == "/status":
            settings = get_settings()
            await self.send(
                f"DB: {os.environ['MW_DATABASE_URL']}\nDEM: {settings.dem_directory}\nWorldCover: {settings.worldcover_directory}"
            )
            return
        if text.startswith("/plan") or re.search(r"(quy hoach|quy hoạch|plan|site)", text, re.IGNORECASE):
            request = parse_plan(text)
            if request is None:
                await self.send("Sai cu phap. Vi du: /plan site DN001 16.032 108.221 radius 30 height 30")
                return
            await self.send(f"Checking GIS for {request.site_name}...")
            try:
                gis_message = await asyncio.to_thread(ensure_gis, request)
                await self.send(gis_message)
                await self.send("Running planner...")
                result_message = await asyncio.to_thread(format_result, request)
                await self.send(result_message)
            except Exception as exc:
                await self.send(f"Failed: {exc}")

    async def initialize_cursor(self) -> None:
        posts = await self.get_posts()
        if not posts:
            return
        if self.skip_existing:
            self.last_create_at = max(int(post.get("create_at") or 0) for post in posts)
            self.seen_post_ids.update(str(post.get("id", "")) for post in posts if post.get("id"))
            print(f"Skipped {len(posts)} existing NetChat posts.", flush=True)

    async def run(self) -> None:
        await self.initialize_cursor()
        print("NetChat polling bot is running.", flush=True)
        while True:
            try:
                posts = await self.get_posts()
                for post in posts:
                    create_at = int(post.get("create_at") or 0)
                    if create_at < self.last_create_at:
                        continue
                    await self.handle_post(post)
            except httpx.HTTPError as exc:
                print(f"NetChat network error: {exc}", flush=True)
            except Exception as exc:
                print(f"NetChat bot error: {exc}", flush=True)
            await asyncio.sleep(self.poll_seconds)


async def main() -> None:
    endpoint = required_env("NETCHAT_API_ENDPOINT")
    channel_id = required_env("NETCHAT_CHANNEL_ID")
    token = os.environ.get("NETCHAT_API_TOKEN", "")
    if not token and os.environ.get("NETCHAT_AUTH_MODE", "bearer").lower() == "cookie":
        token = await login_netchat_cookie(endpoint)
    if not token:
        raise SystemExit("Set NETCHAT_API_TOKEN, or set cookie auto-login env vars.")

    init_db()
    bot = NetChatBot(endpoint, token, channel_id)
    try:
        await bot.run()
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
