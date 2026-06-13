# Chat Integration Handoff

This document captures the current state so another session/agent can continue the work.

## Current App State

The project is `MW Pre-planning Lite`, a FastAPI + React/Vite app for microwave link candidate planning.

Frontend:
- Main UI is now chat-first in `frontend/src/App.tsx`.
- Styling for the chat UI is in `frontend/src/styles.css`.
- The web chat accepts Vietnamese/English planning commands such as:

```text
quy hoạch site DN001 tại 16.032, 108.221 bán kính 30km cao 30m
plan site DN001 16.032 108.221 radius 30 height 30
```

Backend:
- FastAPI app is in `backend/app/main.py`.
- Main planning route is `POST /plan/single-link`.
- GIS download route is `POST /gis/download`.
- In local standalone mode, use SQLite:

```powershell
$env:MW_DATABASE_URL = "sqlite:///$(pwd)\data\mwplanner.db"
```

## Implemented Changes

### Web Chat UI

Files changed:
- `frontend/src/App.tsx`
- `frontend/src/styles.css`

Implemented:
- Chat panel with assistant/user/system messages.
- Local command parser for site name, coordinates, radius, and tower height.
- Chat commands/intents:
  - plan/planning/quy hoạch/chạy/scan/tìm/candidate/link
  - GIS/download DEM/WorldCover
  - refresh/status
  - help
- Existing map/table/chart planning workspace remains.
- Import/export actions are still available via buttons because browser file selection cannot be fully driven by chat text.

### Automatic GIS Preflight

Before running planning, the frontend now:
- Computes required DEM tiles for the current coordinate/radius.
- Computes required ESA WorldCover tiles for the current coordinate/radius.
- Checks current `/system/status`.
- If required GIS files are missing, calls `POST /gis/download`.
- If any GIS tile fails to download, planning is stopped and the chat reports the failure.
- If GIS is ready, planning proceeds.

Important helper functions in `frontend/src/App.tsx`:
- `tilesForRadius`
- `worldcoverTilesForRadius`
- `missingGis`
- `ensureGisReady`

### Telegram Bot

File added:
- `scripts/telegram_bot.py`

Environment variable added:
- `.env.example`: `MW_TELEGRAM_BOT_TOKEN=`

README section added:
- `Run via Telegram`

Telegram bot characteristics:
- Uses Telegram Bot API via `httpx`; no new Python dependency was added.
- Uses long polling, so it can run locally without a public webhook URL.
- Uses the same backend services directly:
  - `init_db`
  - `download_gis_tiles`
  - `plan_single_link`
- Defaults to local SQLite if `MW_DATABASE_URL` is not already set.
- Supports:

```text
/start
/help
/status
/plan site DN001 16.032 108.221 radius 30 height 30
```

It checks/downloads GIS before planning and returns:
- total candidates
- accepted/rejected counts
- best candidate
- calloff summary if available
- top 5 candidates

For VPS chat-only deployment, use `requirements-chat.txt` instead of the full `requirements.txt`. The full file includes `pyinstaller==5.13.0`, which can fail on newer Python versions and is not needed for Telegram bot runtime.

## How To Run Locally

### Frontend Dev Server

The workspace uses a bundled Node runtime:

```powershell
cd frontend
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\vite\bin\vite.js --host 127.0.0.1
```

Note: in the previous session, `npm` was not on `PATH`, so direct Node commands were used instead.

Production build verification:

```powershell
cd frontend
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\typescript\bin\tsc
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\vite\bin\vite.js build
```

Actual path used successfully:

```powershell
D:\MWpre_planning_standalone_59c8a8a\.nodejs\node-v22.17.1-win-x64\node.exe
```

### Backend API

For local SQLite:

```powershell
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

Expected:

```text
status: ok
database: ok
```

Important note:
- Default development config points to PostgreSQL at `postgres:5432`.
- If PostgreSQL is not running, backend startup can hang/retry in `init_db`.
- For standalone/local runs, explicitly set `MW_DATABASE_URL` to SQLite.

### Telegram Bot

Create a bot token via BotFather, then run:

```powershell
$env:MW_TELEGRAM_BOT_TOKEN = "<telegram bot token>"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
D:\MWpre_planning_standalone_59c8a8a\.venv\Scripts\python.exe D:\MWpre_planning_standalone_59c8a8a\scripts\telegram_bot.py
```

Then send this in Telegram:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
```

Validation already performed:

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\telegram_bot.py
.\.venv\Scripts\python.exe -c "from scripts.telegram_bot import parse_plan; r=parse_plan('/plan site DN001 16.032 108.221 radius 30 height 30'); print(r.model_dump())"
```

Parser output:

```python
{
  'site_name': 'DN001',
  'latitude': 16.032,
  'longitude': 108.221,
  'tower_height_m': 30.0,
  'radius_km': 30.0,
  'band': 'AUTO'
}
```

## Current Runtime Notes From Previous Session

Frontend and backend were successfully run on:
- Frontend: `http://127.0.0.1:5173/`
- Backend: `http://127.0.0.1:8000/`

Because the Codex shell sandbox killed foreground dev servers after command timeout, long-running local servers were launched with detached Windows process creation in that session.

Observed process/port state at one point:
- Vite Node process on `127.0.0.1:5173`
- FastAPI Python process on `127.0.0.1:8000`
- `/health` returned `ok`.

## NetChat / Viettel Follow-Up

The user wants Telegram plus another chat platform:

```text
https://bot-netchat.viettel.vn
```

NetChat send-message information provided:

```text
NETCHAT_BOT_ID=rfm7pcsrdfgk7quzuyk7cbj7ze
NETCHAT_API_ENDPOINT=https://netchat.viettel.vn/api/v4/posts
NETCHAT_CHANNEL_ID=xcq93473uin5ube9iyxhoeptza
Authorization: Bearer <TOKEN>
Content-Type: application/json
<BMS verification header>: <BMS verification value>
```

Payload format:

```json
{
  "channel_id": "xcq93473uin5ube9iyxhoeptza",
  "message": "Hello from Python"
}
```

Implemented file:
- `scripts/netchat_send.py`
- `scripts/netchat_bot.py`

Supported:
- Send plain text to NetChat.
- Run a planning command and send the result to NetChat.
- Poll NetChat channel with `GET /api/v4/channels/{channel_id}/posts`.
- Handle `/plan`, `/help`, and `/status` from NetChat messages.
- Reply using `POST /api/v4/posts`.

Example:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:NETCHAT_API_TOKEN = "<TOKEN>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
$env:NETCHAT_BOT_ID = "rfm7pcsrdfgk7quzuyk7cbj7ze"
$env:NETCHAT_BMS_HEADER_NAME = "<TEN_HEADER_BMS>"
$env:NETCHAT_BMS_HEADER_VALUE = "<GIA_TRI_HEADER_BMS>"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --plan "/plan site DN001 16.032 108.221 radius 30 height 30"
```

Still missing for full NetChat bot behavior:
- Webhook support is still unknown, but polling channel posts is implemented.
- If bot repeats its own replies, set `NETCHAT_BOT_USER_ID`.
- BMS/service account auth may still be needed for durable production instead of copied `MMAUTHTOKEN`.

Observed NetChat API error:

```json
{
  "id": "api.context.bms_verified.app_error",
  "message": "API bot phải được gọi qua BMS kèm header xác minh hợp lệ.",
  "status_code": 403
}
```

The script supports BMS verification through:
- `NETCHAT_BOT_ID`, which sends `X-Bot-Id: <bot id>` as the first guess.
- `NETCHAT_BMS_HEADER_NAME`
- `NETCHAT_BMS_HEADER_VALUE`
- or `NETCHAT_EXTRA_HEADERS_JSON` for multiple headers.

The user later provided a working NetChat example using browser session cookie auth:

```python
cookies = {"MMAUTHTOKEN": "..."}
headers = {
    "Accept": "*/*",
    "Accept-Language": "vi",
    "Content-Type": "application/json",
    "DNT": "1",
    "Origin": "https://netchat.viettel.vn",
    "Referer": "https://netchat.viettel.vn/",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
}
```

`scripts/netchat_send.py` now supports this through:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_API_TOKEN = "<MMAUTHTOKEN>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
```

In cookie mode, `NETCHAT_API_TOKEN` is treated as the `MMAUTHTOKEN` cookie value. Do not commit or share this value.

To avoid manually copying `MMAUTHTOKEN`, `scripts/netchat_send.py` also supports auto-login:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_LOGIN_ID = "<NETCHAT_USERNAME>"
$env:NETCHAT_PASSWORD = "<NETCHAT_PASSWORD>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
```

If `NETCHAT_AUTH_MODE=cookie` and `NETCHAT_API_TOKEN` is empty, the script calls:

```text
POST https://netchat.viettel.vn/api/v4/users/login
```

It then uses `MMAUTHTOKEN` from response cookies, or `Token` from response headers as fallback. This only works if NetChat allows username/password API login. If NetChat uses SSO, captcha, OTP, or BMS-only app credentials, ask NetChat admin for an official machine credential flow.

Recommended architecture:

```text
Telegram message
        |
        v
Telegram adapter
        |
        v
Shared chat planner core
        |
        v
GIS check/download + MW planning
        |
        v
Response formatter
        |
        +--> Telegram reply
        +--> NetChat reply
```

Next refactor recommended:
- Extract shared Telegram logic into a reusable module, for example:
  - `backend/app/chat/parser.py`
  - `backend/app/chat/planning.py`
  - `backend/app/chat/formatters.py`
- Keep platform-specific code thin:
- `scripts/telegram_bot.py`
- `scripts/netchat_send.py`
- `scripts/netchat_bot.py`
- later, if NetChat supports webhook: `backend/app/api/netchat_webhook.py`

Shared function target:

```python
def run_chat_plan(text: str) -> str:
    request = parse_plan(text)
    ensure_gis(request)
    result = plan_single_link(...)
    return format_result(result)
```

If NetChat uses webhook:
- Add a FastAPI route, e.g. `POST /chat/netchat/webhook`.
- Validate NetChat token/signature.
- Parse incoming message.
- Call shared `run_chat_plan`.
- Send response using NetChat reply API.
- Expose backend over HTTPS using Cloudflare Tunnel, ngrok, or internal HTTPS ingress.

If NetChat uses polling:
- Create a script similar to `scripts/telegram_bot.py`.
- Use `httpx.AsyncClient` to poll NetChat updates.
- Reuse the same shared planner core.

## Important Existing Files

Core backend:
- `backend/app/api/routes.py`
- `backend/app/services/planner.py`
- `backend/app/terrain/downloader.py`
- `backend/app/database/session.py`
- `backend/app/core/config.py`

Frontend:
- `frontend/src/App.tsx`
- `frontend/src/api.ts`
- `frontend/src/types.ts`
- `frontend/src/styles.css`
- `frontend/src/components/CandidateMap.tsx`
- `frontend/src/components/TerrainChart.tsx`

Telegram:
- `scripts/telegram_bot.py`

Docs/config:
- `README.md`
- `.env.example`

## Git Working Tree Notes

Expected changed/added files from this work:
- Modified: `.env.example`
- Modified: `README.md`
- Modified: `frontend/src/App.tsx`
- Modified: `frontend/src/styles.css`
- Added: `scripts/telegram_bot.py`
- Added: `scripts/netchat_send.py`
- Added: `scripts/netchat_bot.py`
- Added: `docs/CHAT_INTEGRATION_HANDOFF.md`

Generated runtime files may exist and should be treated carefully:
- `data/mwplanner.db`
- `data/worldcover/`

Do not delete generated data unless the user explicitly asks.
