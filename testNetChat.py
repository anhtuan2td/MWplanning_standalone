import asyncio
import aiohttp
import json
import ssl
import os

HOST = "bot-netchat.viettel.vn"
PORT = 443
TOKEN = "4xdwxq9mubb7mpueja6zhf77mr"

API = f"https://{HOST}:{PORT}/api/v4"
WS = f"wss://{HOST}:{PORT}/api/v4/websocket"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


async def get_bot_user_id(session):
    async with session.get(f"{API}/users/me", headers=HEADERS, ssl=ssl_ctx) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data["id"]


async def send_reply(session, channel_id, message, root_id=None):
    payload = {
        "channel_id": channel_id,
        "message": message,
    }

    if root_id:
        payload["root_id"] = root_id

    async with session.post(f"{API}/posts", headers=HEADERS, json=payload, ssl=ssl_ctx) as resp:
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"POST /posts lỗi {resp.status}: {text}")

        return await resp.json()


async def handle_post(session, event, bot_user_id):
    data = event.get("data", {})
    post_raw = data.get("post")

    if not post_raw:
        return

    post = json.loads(post_raw)

    post_id = post.get("id")
    user_id = post.get("user_id")
    channel_id = post.get("channel_id")
    root_id = post.get("root_id") or post_id
    message = post.get("message", "")

    # Không tự trả lời chính bot
    if user_id == bot_user_id:
        return

    if not message.strip():
        return

    print("Tin mới:")
    print("  user_id   :", user_id)
    print("  channel_id:", channel_id)
    print("  message   :", message)

    reply = "Bot đã nhận: " + message

    await send_reply(
        session=session,
        channel_id=channel_id,
        message=reply,
        root_id=root_id,
    )

    print("Đã trả lời:", reply)


async def websocket_loop(session, bot_user_id):
    seq = 1

    while True:
        try:
            print("Đang kết nối WebSocket...")

            async with session.ws_connect(WS, headers=HEADERS, ssl=ssl_ctx) as ws:
                await ws.send_json({
                    "seq": seq,
                    "action": "authentication_challenge",
                    "data": {
                        "token": TOKEN
                    },
                })
                seq += 1

                print("WebSocket đã kết nối.")

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        event = json.loads(msg.data)

                        event_name = event.get("event")

                        if event_name == "posted":
                            await handle_post(session, event, bot_user_id)

                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        print("WebSocket bị đóng/lỗi. Sẽ kết nối lại.")
                        break

        except Exception as e:
            print("Lỗi WebSocket:", e)
            print("Thử kết nối lại sau 5 giây...")
            await asyncio.sleep(5)


async def main():
    if not TOKEN or TOKEN == "your_bot_token_here":
        raise RuntimeError("Chưa nhập BOT_TOKEN")

    async with aiohttp.ClientSession() as session:
        bot_user_id = await get_bot_user_id(session)

        print("Bot đang chạy.")
        print("bot_user_id =", bot_user_id)

        await websocket_loop(session, bot_user_id)


if __name__ == "__main__":
    asyncio.run(main())