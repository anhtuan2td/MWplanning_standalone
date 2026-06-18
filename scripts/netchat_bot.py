from __future__ import annotations

import argparse
import asyncio
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any

import aiohttp


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("MW_DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'data' / 'mwplanner.db').as_posix()}")

from app.core.config import get_settings  # noqa: E402
from app.database.session import init_db  # noqa: E402
from scripts.netchat_send import (  # noqa: E402
    apply_netchat_config,
    apply_netchat_env_config,
    build_netchat_auth,
    endpoint_from_server_url,
    netchat_base_url,
    netchat_ssl_verify,
    required_env,
)
from scripts.telegram_bot import ensure_gis, format_result, parse_plan  # noqa: E402


HELP_TEXT = """MW Pre-planning NetChat

Lenh:
/plan site DN001 16.032 108.221 radius 30 height 30
/status

Bot se tu kiem tra GIS. Neu thieu DEM/WorldCover, bot tai GIS truoc roi moi chay planning.
"""


def websocket_url(endpoint: str) -> str:
    base = netchat_base_url(endpoint)
    if base.startswith("https://"):
        return f"wss://{base.removeprefix('https://')}/api/v4/websocket"
    if base.startswith("http://"):
        return f"ws://{base.removeprefix('http://')}/api/v4/websocket"
    raise SystemExit(f"Unsupported NetChat base URL: {base}")


def aiohttp_ssl_context() -> ssl.SSLContext | bool:
    if netchat_ssl_verify():
        return True
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


class NetChatBot:
    def __init__(self, endpoint: str, token: str) -> None:
        self.endpoint = endpoint
        self.base_url = netchat_base_url(endpoint)
        self.ws_url = websocket_url(endpoint)
        self.token = token
        self.reply_in_thread = os.environ.get("NETCHAT_REPLY_IN_THREAD", "true").lower() in {"1", "true", "yes", "on"}
        self.reconnect_seconds = float(os.environ.get("NETCHAT_RECONNECT_SECONDS", "5"))
        self.bot_user_id = os.environ.get("NETCHAT_BOT_USER_ID", "")
        self.ssl_context = aiohttp_ssl_context()
        self.seq = 1

    def auth(self) -> tuple[dict[str, str], dict[str, str]]:
        return build_netchat_auth(self.token, self.endpoint)

    async def get_bot_user_id(self, session: aiohttp.ClientSession) -> str:
        headers, cookies = self.auth()
        async with session.get(f"{self.base_url}/api/v4/users/me", headers=headers, cookies=cookies, ssl=self.ssl_context) as response:
            text = await response.text()
            if response.status >= 400:
                raise RuntimeError(f"GET /users/me failed {response.status}: {text}")
            data = json.loads(text)
            return data["id"]

    async def send_reply(self, session: aiohttp.ClientSession, channel_id: str, message: str, root_id: str | None = None) -> None:
        headers, cookies = self.auth()
        payload: dict[str, Any] = {
            "channel_id": channel_id,
            "message": message,
        }
        if root_id and self.reply_in_thread:
            payload["root_id"] = root_id

        async with session.post(f"{self.base_url}/api/v4/posts", headers=headers, cookies=cookies, json=payload, ssl=self.ssl_context) as response:
            text = await response.text()
            if response.status >= 400:
                raise RuntimeError(f"POST /posts failed {response.status}: {text}")

    async def send_chunks(self, session: aiohttp.ClientSession, channel_id: str, text: str, root_id: str | None = None) -> None:
        chunks = [text[index : index + 3900] for index in range(0, len(text), 3900)] or [""]
        for chunk in chunks:
            await self.send_reply(session, channel_id, chunk, root_id=root_id)

    async def handle_post(self, session: aiohttp.ClientSession, event: dict[str, Any], bot_user_id: str) -> None:
        data = event.get("data", {})
        post_raw = data.get("post")
        if not post_raw:
            return

        post = json.loads(post_raw)
        post_id = post.get("id")
        user_id = post.get("user_id")
        channel_id = post.get("channel_id")
        root_id = post.get("root_id") or post_id
        message = (post.get("message") or "").strip()

        if user_id == bot_user_id or (self.bot_user_id and user_id == self.bot_user_id):
            return
        if not message:
            return

        print(f"NetChat message from {user_id} in {channel_id}: {message}", flush=True)

        if message in {"/help", "help"}:
            await self.send_chunks(session, channel_id, HELP_TEXT, root_id=root_id)
            return
        if message == "/status":
            settings = get_settings()
            await self.send_chunks(
                session,
                channel_id,
                f"DB: {os.environ['MW_DATABASE_URL']}\nDEM: {settings.dem_directory}\nWorldCover: {settings.worldcover_directory}",
                root_id=root_id,
            )
            return
        if message.startswith("/plan") or "plan" in message.lower() or "site" in message.lower() or "quy hoạch" in message.lower():
            request = parse_plan(message)
            if request is None:
                await self.send_chunks(session, channel_id, "Sai cu phap. Vi du: /plan site DN001 16.032 108.221 radius 30 height 30", root_id=root_id)
                return
            await self.send_chunks(session, channel_id, f"Checking GIS for {request.site_name}...", root_id=root_id)
            try:
                gis_message = await asyncio.to_thread(ensure_gis, request)
                await self.send_chunks(session, channel_id, gis_message, root_id=root_id)
                await self.send_chunks(session, channel_id, "Running planner...", root_id=root_id)
                result_message = await asyncio.to_thread(format_result, request)
                await self.send_chunks(session, channel_id, result_message, root_id=root_id)
            except Exception as exc:
                await self.send_chunks(session, channel_id, f"Failed: {exc}", root_id=root_id)

    async def websocket_loop(self, session: aiohttp.ClientSession, bot_user_id: str) -> None:
        headers, _ = self.auth()
        while True:
            try:
                print(f"Connecting NetChat WebSocket: {self.ws_url}", flush=True)
                async with session.ws_connect(self.ws_url, headers=headers, ssl=self.ssl_context) as ws:
                    await ws.send_json(
                        {
                            "seq": self.seq,
                            "action": "authentication_challenge",
                            "data": {"token": self.token},
                        }
                    )
                    self.seq += 1
                    print("NetChat WebSocket connected.", flush=True)

                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.TEXT:
                            event = json.loads(message.data)
                            if event.get("event") == "posted":
                                await self.handle_post(session, event, bot_user_id)
                        elif message.type in {aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                            print("NetChat WebSocket closed/error. Reconnecting.", flush=True)
                            break
            except Exception as exc:
                print(f"NetChat WebSocket error: {exc}", flush=True)
                await asyncio.sleep(self.reconnect_seconds)

    async def run(self) -> None:
        async with aiohttp.ClientSession() as session:
            bot_user_id = await self.get_bot_user_id(session)
            print("NetChat bot is running.", flush=True)
            print(f"bot_user_id = {bot_user_id}", flush=True)
            await self.websocket_loop(session, bot_user_id)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run MW Pre-planning NetChat WebSocket bot.")
    parser.add_argument("--config", help="Read NetChat settings from a config JSON with a netchat block.")
    args = parser.parse_args()

    apply_netchat_config(args.config)
    apply_netchat_env_config()
    if not os.environ.get("NETCHAT_API_ENDPOINT") and not os.environ.get("NETCHAT_SERVER_URL"):
        os.environ["NETCHAT_API_ENDPOINT"] = endpoint_from_server_url("https://bot-netchat.viettel.vn")

    endpoint = required_env("NETCHAT_API_ENDPOINT")
    token = os.environ.get("NETCHAT_API_TOKEN") or os.environ.get("NETCHAT_TOKEN")
    if not token:
        raise SystemExit("Set NETCHAT_TOKEN or NETCHAT_API_TOKEN.")

    init_db()
    await NetChatBot(endpoint, token).run()


if __name__ == "__main__":
    asyncio.run(main())
