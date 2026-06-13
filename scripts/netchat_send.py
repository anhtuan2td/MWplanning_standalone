from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("MW_DATABASE_URL", f"sqlite:///{(PROJECT_ROOT / 'data' / 'mwplanner.db').as_posix()}")

from scripts.telegram_bot import ensure_gis, format_result, parse_plan  # noqa: E402
from app.database.session import init_db  # noqa: E402


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Set {name} before running NetChat sender.")
    return value


def optional_verification_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    bot_id = os.environ.get("NETCHAT_BOT_ID")
    if bot_id:
        # First guess for NetChat/BMS verification. Override with
        # NETCHAT_BMS_HEADER_NAME/VALUE if the BMS team provides a different header.
        headers["X-Bot-Id"] = bot_id

    header_name = os.environ.get("NETCHAT_BMS_HEADER_NAME")
    header_value = os.environ.get("NETCHAT_BMS_HEADER_VALUE")
    if header_name and header_value:
        headers[header_name] = header_value

    extra_headers = os.environ.get("NETCHAT_EXTRA_HEADERS_JSON")
    if extra_headers:
        try:
            parsed = json.loads(extra_headers)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"NETCHAT_EXTRA_HEADERS_JSON is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SystemExit("NETCHAT_EXTRA_HEADERS_JSON must be a JSON object.")
        headers.update({str(key): str(value) for key, value in parsed.items()})
    return headers


async def send_netchat_message(endpoint: str, token: str, channel_id: str, message: str) -> None:
    headers, cookies = build_netchat_auth(token, endpoint)
    payload: dict[str, Any] = {
        "channel_id": channel_id,
        "message": message,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(endpoint, headers=headers, cookies=cookies, json=payload)
        if response.is_error:
            detail = response.text.strip()
            raise RuntimeError(
                f"NetChat API returned {response.status_code} {response.reason_phrase}. "
                f"Response: {detail or '<empty response>'}"
            )


async def check_netchat_auth(endpoint: str, token: str) -> None:
    headers, cookies = build_netchat_auth(token, endpoint)
    url = f"{netchat_base_url(endpoint)}/api/v4/users/me"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=headers, cookies=cookies)
        if response.is_error:
            detail = response.text.strip()
            raise RuntimeError(
                f"NetChat auth check returned {response.status_code} {response.reason_phrase}. "
                f"Response: {detail or '<empty response>'}"
            )
        data = response.json()
        username = data.get("username") or data.get("email") or data.get("id") or "<unknown>"
        print(f"NetChat auth OK: {username}")


def build_netchat_auth(token: str, endpoint: str) -> tuple[dict[str, str], dict[str, str]]:
    auth_mode = os.environ.get("NETCHAT_AUTH_MODE", "bearer").lower()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": os.environ.get("NETCHAT_USER_AGENT", "MW-Preplanning-Bot/1.0"),
    }
    cookies: dict[str, str] = {}
    if auth_mode == "cookie":
        headers.update(
            {
                "Accept": os.environ.get("NETCHAT_ACCEPT", "*/*"),
                "Accept-Language": os.environ.get("NETCHAT_ACCEPT_LANGUAGE", "vi"),
                "DNT": "1",
                "Origin": os.environ.get("NETCHAT_ORIGIN", "https://netchat.viettel.vn"),
                "Referer": os.environ.get("NETCHAT_REFERER", "https://netchat.viettel.vn/"),
                "User-Agent": os.environ.get("NETCHAT_USER_AGENT", "Mozilla/5.0"),
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        cookies["MMAUTHTOKEN"] = token
    else:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(optional_verification_headers())
    return headers, cookies


def netchat_base_url(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"Invalid NETCHAT_API_ENDPOINT: {endpoint}")
    return f"{parsed.scheme}://{parsed.netloc}"


async def login_netchat_cookie(endpoint: str) -> str:
    login_id = os.environ.get("NETCHAT_LOGIN_ID")
    password = os.environ.get("NETCHAT_PASSWORD")
    if not login_id or not password:
        raise SystemExit(
            "Set NETCHAT_API_TOKEN, or set NETCHAT_LOGIN_ID and NETCHAT_PASSWORD to auto-login NetChat."
        )

    login_url = f"{netchat_base_url(endpoint)}/api/v4/users/login"
    headers = {
        "Accept": "*/*",
        "Accept-Language": os.environ.get("NETCHAT_ACCEPT_LANGUAGE", "vi"),
        "Content-Type": "application/json",
        "DNT": "1",
        "Origin": os.environ.get("NETCHAT_ORIGIN", netchat_base_url(endpoint)),
        "Referer": os.environ.get("NETCHAT_REFERER", f"{netchat_base_url(endpoint)}/"),
        "User-Agent": os.environ.get("NETCHAT_USER_AGENT", "Mozilla/5.0"),
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {"login_id": login_id, "password": password}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(login_url, headers=headers, json=payload)
        if response.is_error:
            detail = response.text.strip()
            raise RuntimeError(
                f"NetChat login returned {response.status_code} {response.reason_phrase}. "
                f"Response: {detail or '<empty response>'}"
            )
        cookie_token = response.cookies.get("MMAUTHTOKEN")
        if cookie_token:
            return cookie_token
        header_token = response.headers.get("Token") or response.headers.get("token")
        if header_token:
            return header_token
        raise RuntimeError("NetChat login succeeded but no MMAUTHTOKEN cookie or Token header was returned.")


def build_message(args: argparse.Namespace) -> str:
    if args.plan:
        request = parse_plan(args.plan)
        if request is None:
            raise SystemExit("Invalid plan command. Example: --plan \"/plan site DN001 16.032 108.221 radius 30 height 30\"")
        gis_message = ensure_gis(request)
        result_message = format_result(request)
        return f"{gis_message}\n\n{result_message}"
    return args.message


async def main() -> None:
    parser = argparse.ArgumentParser(description="Send MW Pre-planning messages to NetChat.")
    parser.add_argument("--message", default="Hello from MW Pre-planning", help="Plain message to send.")
    parser.add_argument("--plan", help="Run a planning command and send the result.")
    parser.add_argument("--check-auth", action="store_true", help="Check NetChat token/cookie with /api/v4/users/me.")
    args = parser.parse_args()

    endpoint = required_env("NETCHAT_API_ENDPOINT")
    token = os.environ.get("NETCHAT_API_TOKEN", "")
    channel_id = required_env("NETCHAT_CHANNEL_ID")

    init_db()
    if not token and os.environ.get("NETCHAT_AUTH_MODE", "bearer").lower() == "cookie":
        token = await login_netchat_cookie(endpoint)
    if args.check_auth:
        await check_netchat_auth(endpoint, token)
        return
    message = await asyncio.to_thread(build_message, args)
    await send_netchat_message(endpoint, token, channel_id, message)
    print("NetChat message sent.")


if __name__ == "__main__":
    asyncio.run(main())
