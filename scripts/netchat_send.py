from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
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


DEFAULT_NETCHAT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0"
)


def truthy(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def bot_server_url(server_url: str) -> str:
    return server_url.rstrip("/").replace("https://netchat.viettel.vn", "https://bot-netchat.viettel.vn")


def endpoint_from_server_url(server_url: str) -> str:
    return f"{bot_server_url(server_url)}/api/v4/posts"


def apply_netchat_config(config_path: str | None) -> None:
    path_value = config_path or os.environ.get("NETCHAT_CONFIG_PATH")
    if not path_value:
        return
    path = Path(path_value)
    data = json.loads(path.read_text(encoding="utf-8"))
    netchat = data.get("netchat", {})
    if not isinstance(netchat, dict):
        raise SystemExit(f"Invalid netchat config in {path}")

    server_url = str(netchat.get("server_url") or "").strip()
    if server_url and not os.environ.get("NETCHAT_API_ENDPOINT"):
        endpoint = endpoint_from_server_url(server_url)
        os.environ["NETCHAT_API_ENDPOINT"] = endpoint
        os.environ.setdefault("NETCHAT_ORIGIN", netchat_base_url(endpoint))
        os.environ.setdefault("NETCHAT_REFERER", f"{netchat_base_url(endpoint)}/")

    token = str(netchat.get("token") or "").strip()
    if token:
        os.environ.setdefault("NETCHAT_API_TOKEN", token)

    channel_id = str(netchat.get("channel_id") or "").strip()
    if channel_id:
        os.environ.setdefault("NETCHAT_CHANNEL_ID", channel_id)

    if "ssl_verify" in netchat:
        os.environ.setdefault("NETCHAT_SSL_VERIFY", "true" if truthy(netchat.get("ssl_verify")) else "false")
    if "auto_send_interval_seconds" in netchat:
        os.environ.setdefault("NETCHAT_POLL_SECONDS", str(netchat["auto_send_interval_seconds"]))
    if "reply_in_thread" in netchat:
        os.environ.setdefault("NETCHAT_REPLY_IN_THREAD", "true" if truthy(netchat.get("reply_in_thread")) else "false")


def apply_netchat_env_config() -> None:
    server_url = os.environ.get("NETCHAT_SERVER_URL", "").strip()
    if server_url and not os.environ.get("NETCHAT_API_ENDPOINT"):
        endpoint = endpoint_from_server_url(server_url)
        os.environ["NETCHAT_API_ENDPOINT"] = endpoint
        os.environ.setdefault("NETCHAT_ORIGIN", netchat_base_url(endpoint))
        os.environ.setdefault("NETCHAT_REFERER", f"{netchat_base_url(endpoint)}/")

    token = os.environ.get("NETCHAT_TOKEN", "").strip()
    if token and not os.environ.get("NETCHAT_API_TOKEN"):
        os.environ["NETCHAT_API_TOKEN"] = token

    if os.environ.get("NETCHAT_CHANNEL_ID") and not os.environ.get("NETCHAT_API_ENDPOINT"):
        endpoint = endpoint_from_server_url("https://bot-netchat.viettel.vn")
        os.environ["NETCHAT_API_ENDPOINT"] = endpoint
        os.environ.setdefault("NETCHAT_ORIGIN", netchat_base_url(endpoint))
        os.environ.setdefault("NETCHAT_REFERER", f"{netchat_base_url(endpoint)}/")


def netchat_ssl_verify() -> bool:
    return truthy(os.environ.get("NETCHAT_SSL_VERIFY"), default=True)


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
    user_id = os.environ.get("NETCHAT_MMUSERID") or os.environ.get("NETCHAT_USER_ID") or ""
    payload: dict[str, Any] = {
        "channel_id": channel_id,
        "create_at": 0,
        "file_ids": [],
        "message": message,
        "metadata": {},
        "pending_post_id": f"{user_id}:{int(time.time() * 1000)}" if user_id else "",
        "props": {"disable_group_highlight": True},
        "reply_count": 0,
        "root_id": os.environ.get("NETCHAT_ROOT_ID", ""),
    }
    async with httpx.AsyncClient(timeout=60, verify=netchat_ssl_verify()) as client:
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
    async with httpx.AsyncClient(timeout=60, verify=netchat_ssl_verify()) as client:
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


async def check_netchat_read(endpoint: str, token: str, channel_id: str) -> None:
    headers, cookies = build_netchat_auth(token, endpoint)
    url = f"{netchat_base_url(endpoint)}/api/v4/channels/{channel_id}/posts"
    async with httpx.AsyncClient(timeout=60, verify=netchat_ssl_verify()) as client:
        response = await client.get(url, headers=headers, cookies=cookies, params={"page": 0, "per_page": 1})
        if response.is_error:
            detail = response.text.strip()
            raise RuntimeError(
                f"NetChat read check returned {response.status_code} {response.reason_phrase}. "
                f"Response: {detail or '<empty response>'}"
            )
        data = response.json()
        order = data.get("order", [])
        print(f"NetChat read OK: {len(order)} post id(s) returned.")


def build_netchat_auth(token: str, endpoint: str) -> tuple[dict[str, str], dict[str, str]]:
    auth_mode = os.environ.get("NETCHAT_AUTH_MODE", "bearer").lower()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": os.environ.get("NETCHAT_USER_AGENT", DEFAULT_NETCHAT_USER_AGENT),
    }
    cookies: dict[str, str] = {}
    if auth_mode == "cookie":
        headers.update(
            {
                "Accept": os.environ.get("NETCHAT_ACCEPT", "*/*"),
                "Accept-Language": os.environ.get("NETCHAT_ACCEPT_LANGUAGE", "vi"),
                "Accept-Encoding": os.environ.get("NETCHAT_ACCEPT_ENCODING", "gzip, deflate, br, zstd"),
                "DNT": "1",
                "Origin": os.environ.get("NETCHAT_ORIGIN", netchat_base_url(endpoint)),
                "Referer": os.environ.get("NETCHAT_REFERER", f"{netchat_base_url(endpoint)}/"),
                "Sec-CH-UA": os.environ.get("NETCHAT_SEC_CH_UA", '"Microsoft Edge";v="149", "Chromium";v="149", "Not)A;Brand";v="24"'),
                "Sec-CH-UA-Mobile": os.environ.get("NETCHAT_SEC_CH_UA_MOBILE", "?0"),
                "Sec-CH-UA-Platform": os.environ.get("NETCHAT_SEC_CH_UA_PLATFORM", '"Windows"'),
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": os.environ.get("NETCHAT_USER_AGENT", DEFAULT_NETCHAT_USER_AGENT),
                "X-Requested-With": "XMLHttpRequest",
            }
        )
        cookies["MMAUTHTOKEN"] = token
        mm_user_id = os.environ.get("NETCHAT_MMUSERID") or os.environ.get("NETCHAT_USER_ID")
        mm_csrf = os.environ.get("NETCHAT_MMCSRF") or os.environ.get("NETCHAT_CSRF_TOKEN")
        if mm_user_id:
            cookies["MMUSERID"] = mm_user_id
        if mm_csrf:
            cookies["MMCSRF"] = mm_csrf
            headers["X-CSRF-Token"] = mm_csrf
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
        "User-Agent": os.environ.get("NETCHAT_USER_AGENT", DEFAULT_NETCHAT_USER_AGENT),
        "X-Requested-With": "XMLHttpRequest",
    }
    payload = {"login_id": login_id, "password": password}
    async with httpx.AsyncClient(timeout=60, verify=netchat_ssl_verify()) as client:
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
    parser.add_argument("--check-read", action="store_true", help="Check read permission with /api/v4/channels/{channel_id}/posts.")
    parser.add_argument("--check-post", action="store_true", help="Check write permission by posting a short message.")
    parser.add_argument("--config", help="Read NetChat settings from a config JSON with a netchat block.")
    args = parser.parse_args()

    apply_netchat_config(args.config)
    apply_netchat_env_config()
    endpoint = required_env("NETCHAT_API_ENDPOINT")
    token = os.environ.get("NETCHAT_API_TOKEN", "")

    init_db()
    if not token and os.environ.get("NETCHAT_AUTH_MODE", "bearer").lower() == "cookie":
        token = await login_netchat_cookie(endpoint)
    if args.check_auth:
        await check_netchat_auth(endpoint, token)
        return
    channel_id = required_env("NETCHAT_CHANNEL_ID")
    if args.check_read:
        await check_netchat_read(endpoint, token, channel_id)
        return
    if args.check_post:
        await send_netchat_message(endpoint, token, channel_id, "NetChat POST permission test from MW Pre-planning.")
        print("NetChat post OK.")
        return
    message = await asyncio.to_thread(build_message, args)
    await send_netchat_message(endpoint, token, channel_id, message)
    print("NetChat message sent.")


if __name__ == "__main__":
    asyncio.run(main())
