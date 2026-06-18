# Chat Test Scenarios

Tai lieu nay ghi lai cac tinh huong da test trong qua trinh tich hop chat cho MW Pre-planning Lite.

## 1. Web Chat Local

### 1.1 Frontend Vite

Muc tieu:
- Chay giao dien web chat local.

Lenh da dung:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a\frontend
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\vite\bin\vite.js --host 127.0.0.1
```

URL:

```text
http://127.0.0.1:5173/
```

Ket qua:
- Vite build/dev server chay duoc.
- Co luc browser bao `ERR_CONNECTION_REFUSED` vi dev server foreground bi dung khi command timeout.
- Da xu ly bang cach chay process nen tach rieng.

### 1.2 Backend FastAPI

Muc tieu:
- Chay API local cho frontend.

Lenh dung voi SQLite:

```powershell
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
cd D:\MWpre_planning_standalone_59c8a8a\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

Ket qua:

```text
status: ok
database: ok
```

Luu y:
- Neu khong set `MW_DATABASE_URL`, backend dev mac dinh tro toi PostgreSQL `postgres:5432` va co the ket o startup/retry.

## 2. Auto GIS Preflight

Muc tieu:
- Truoc khi planning, he thong tu kiem tra DEM/WorldCover.
- Neu thieu thi tu download.
- Neu download loi tile nao thi dung planning va bao loi.

Da implement trong frontend:
- `tilesForRadius`
- `worldcoverTilesForRadius`
- `missingGis`
- `ensureGisReady`

Ket qua test:
- TypeScript pass.
- Vite build pass.
- Backend `/health` pass.

Luu y:
- Download GIS can internet outbound.
- Offline deployment co the copy san GIS vao:

```text
data/dem/
data/worldcover/
```

## 3. Telegram Bot

### 3.1 Dependency tren VPS

Tinh huong:
- Cai full `requirements.txt` tren VPS bi loi vi `pyinstaller==5.13.0` khong ho tro Python moi.

Loi gap:

```text
No matching distribution found for pyinstaller==5.13.0
```

Xu ly:
- Tao `requirements-chat.txt` cho chat-only runtime.

Lenh dung:

```powershell
python -m pip install -r requirements-chat.txt
```

Ket qua:
- Khong can PyInstaller khi chi chay Telegram/NetChat bot.

### 3.2 PowerShell Environment Variables

Tinh huong:
- Dung `set MW_TELEGRAM_BOT_TOKEN=...` trong PowerShell khong co tac dung voi Python process.

Sai:

```powershell
set MW_TELEGRAM_BOT_TOKEN=...
```

Dung:

```powershell
$env:MW_TELEGRAM_BOT_TOKEN = "<telegram bot token>"
$env:MW_DATABASE_URL = "sqlite:///C:/mw_preplanning/data/mwplanner.db"
python scripts\telegram_bot.py
```

Ket qua:
- Bot Telegram doc duoc token khi dung `$env:`.

Luu y bao mat:
- Telegram bot token da tung bi paste trong chat. Nen revoke/regenerate neu token do con dung.

## 4. NetChat Send API

### 4.1 Endpoint `POST /api/v4/posts`

Endpoint dung:

```text
https://netchat.viettel.vn/api/v4/posts
```

Payload:

```json
{
  "channel_id": "xcq93473uin5ube9iyxhoeptza",
  "message": "Hello from Python"
}
```

Da implement:
- `scripts/netchat_send.py`

Lenh test:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
python scripts\netchat_send.py --message "Hello from MW Pre-planning"
```

## 5. NetChat Auth Tests

### 5.1 Bearer Bot Token - Auth OK

Test:

```powershell
$headers = @{
  Authorization = "Bearer $($env:NETCHAT_API_TOKEN)"
  Accept = "application/json"
}

Invoke-RestMethod `
  -Uri "https://netchat.viettel.vn/api/v4/users/me" `
  -Headers $headers | ConvertTo-Json -Depth 5
```

Ket qua:
- Bot token hop le.
- `/api/v4/users/me` tra ve bot user:

```text
id: rfm7pcsrdfgk7quzuyk7cbj7ze
username: bot_mw_anhtuan2td
first_name: MW_assistant_KV2
is_bot: true
roles: system_user
```

Ket luan:
- Authentication bang bot token OK.

### 5.2 Bearer Bot Token - Messaging API Bi BMS Chan

Test:

```powershell
Invoke-RestMethod `
  -Uri "https://netchat.viettel.vn/api/v4/channels/$($env:NETCHAT_CHANNEL_ID)/posts" `
  -Headers $headers | ConvertTo-Json -Depth 5
```

Ket qua loi:

```json
{
  "id": "api.context.bms_verified.app_error",
  "message": "API bot phải được gọi qua BMS kèm header xác minh hợp lệ.",
  "status_code": 403
}
```

Ket luan:
- Bot token dung nhung messaging endpoints bi BMS policy chan.
- Loi nay xay ra voi read posts va write posts.
- Endpoint dung, token dung, nhung thieu BMS verification header/route.

### 5.3 BMS Header Thu Bang Bot ID

Da thu them header:

```text
X-Bot-Id: rfm7pcsrdfgk7quzuyk7cbj7ze
```

Ket qua:
- Van bi 403 BMS.

Ket luan:
- Bot ID khong phai BMS verification header du.

### 5.4 User-Agent `curl/8.7.1`

Da thu doi default User-Agent:

```text
User-Agent: curl/8.7.1
```

Ket qua:
- Van bi 403.

Ket luan:
- User-Agent `curl/8.7.1` khong giai quyet BMS policy.

### 5.5 User-Agent Edge/Chrome

Da thu User-Agent:

```text
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36 Edg/149.0.0.0
```

Ket qua:
- Van bi 403 BMS.

Ket luan:
- User-Agent khong phai dieu kien chinh.
- Can BMS verification header/credential dung.

### 5.6 Cloudrity Access Denied

Co luc response la HTML:

```text
Access denied
cloudrity
```

Ket luan:
- Request bi chan o lop WAF/Cloudrity truoc khi vao API NetChat.
- Sau khi dung endpoint/API/auth khac, loi chuyen thanh JSON BMS 403, nghia la da vao duoc tang API hon.

### 5.7 Cookie Mode Bang `MMAUTHTOKEN`

Nguoi dung cung cap code mau dang chay duoc voi:

```python
cookies = {
    "MMAUTHTOKEN": "..."
}
```

Headers dang browser-like:

```text
Accept: */*
Accept-Language: vi
Content-Type: application/json
DNT: 1
Origin: https://netchat.viettel.vn
Referer: https://netchat.viettel.vn/
User-Agent: Mozilla/5.0
X-Requested-With: XMLHttpRequest
```

Da implement:
- `NETCHAT_AUTH_MODE=cookie`
- `NETCHAT_API_TOKEN=<MMAUTHTOKEN>`

Lenh:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_API_TOKEN = "<MMAUTHTOKEN>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"

python scripts\netchat_send.py --message "Hello from MW Pre-planning"
```

Ket qua:
- Gui message thanh cong voi `MMAUTHTOKEN`.

Ket luan:
- Cookie session cua user co the gui message.
- Day la workaround chay duoc, nhung khong ben vi cookie het han.

### 5.7.1 Network Capture 201 Created

File `network.json` cho thay request thanh cong `201 Created` co dang:

```text
POST https://netchat.viettel.vn/api/v4/posts
```

Headers/cookies quan trong:

```text
Cookie: MMAUTHTOKEN=<secret>
Cookie: MMUSERID=<secret>
Cookie: MMCSRF=<secret>
X-CSRF-Token: <MMCSRF>
Origin: https://netchat.viettel.vn
Referer: https://netchat.viettel.vn/
X-Requested-With: XMLHttpRequest
User-Agent: Mozilla/5.0 ... Edg/149.0.0.0
```

Payload co them cac field browser hay gui:

```json
{
  "channel_id": "...",
  "create_at": 0,
  "file_ids": [],
  "message": "hello",
  "metadata": {},
  "pending_post_id": "<user_id>:<timestamp>",
  "props": {
    "disable_group_highlight": true
  },
  "reply_count": 0,
  "root_id": ""
}
```

Da cap nhat `scripts/netchat_send.py` cookie mode de gui them:

```text
NETCHAT_MMUSERID
NETCHAT_MMCSRF
X-CSRF-Token
browser-like payload
```

### 5.8 Cookie Het Han

Loi gap:

```json
{
  "id": "api.context.session_expired.app_error",
  "message": "Không hợp lệ hoặc hết hạn, xin vui lòng nhập một lần nữa.",
  "status_code": 401
}
```

Ket luan:
- `MMAUTHTOKEN` het han hoac copy sai.
- Can login lai NetChat va lay cookie moi.

### 5.9 Auto Login Lay `MMAUTHTOKEN`

Da implement:

```powershell
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_LOGIN_ID = "<TAI_KHOAN_NETCHAT>"
$env:NETCHAT_PASSWORD = "<MAT_KHAU_NETCHAT>"
```

Script se goi:

```text
POST https://netchat.viettel.vn/api/v4/users/login
```

Ket qua:
- Neu NetChat cho phep username/password API login thi co the tu lay token/cookie.
- Neu dung SSO, OTP, captcha hoac BMS login rieng thi co the van fail.

## 6. NetChat Polling Bot

Ban dau da implement:
- `scripts/netchat_bot.py`

Co che polling cu:
- Poll channel bang:

```text
GET /api/v4/channels/{channel_id}/posts
```

- Nhan lenh:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
/help
/status
```

- Tra loi bang:

```text
POST /api/v4/posts
```

Lenh chay:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_API_TOKEN = "<MMAUTHTOKEN>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
$env:NETCHAT_POLL_SECONDS = "4"
$env:NETCHAT_SKIP_EXISTING = "1"

python scripts\netchat_bot.py
```

Ket luan cu:
- Polling REST bi BMS chan voi bearer bot token.

## 6.1 NetChat WebSocket Bot

Nguoi dung cung cap `testNetChat.py` da test OK.

Co che dung:

```text
GET  https://bot-netchat.viettel.vn/api/v4/users/me
WSS  wss://bot-netchat.viettel.vn/api/v4/websocket
POST https://bot-netchat.viettel.vn/api/v4/posts
```

WebSocket auth:

```json
{
  "seq": 1,
  "action": "authentication_challenge",
  "data": {
    "token": "<BOT_TOKEN>"
  }
}
```

Event can nghe:

```text
event == "posted"
```

Trong event, `data.post` la JSON string cua post moi.

Reply:

```json
{
  "channel_id": "<channel_id tu post>",
  "message": "...",
  "root_id": "<post_id hoac root_id>"
}
```

Da cap nhat `scripts/netchat_bot.py`:
- Bo polling REST lam co che chinh.
- Dung `aiohttp`.
- Nghe realtime qua WebSocket.
- Ignore message cua chinh bot.
- Xu ly `/plan`, `/help`, `/status`.
- Reply in thread neu `NETCHAT_REPLY_IN_THREAD=true`.

Ket luan moi:
- Duong dung cho bot tu dong la WebSocket tren `bot-netchat.viettel.vn`, khong phai polling `GET /channels/{channel_id}/posts`.
- REST `POST /posts` van duoc dung de reply, nhung goi qua host `bot-netchat.viettel.vn` va bot token.

## 7. Bot_Netchat.docx

Tai lieu Word thuc chat la anh/OLE nhung doc duoc noi dung chinh sau khi convert WMF sang PNG.

Noi dung doc xac nhan cac endpoint:

```text
GET  /api/v4/channels/{channel_id}/posts
POST /api/v4/posts
POST /api/v4/channels/direct
POST /api/v4/channels/group
GET  /api/v4/users/me-like endpoints khac
POST /api/v4/files
```

Ket luan:
- Doc xac nhan path API dung.
- Doc khong co thong tin BMS verification header, app secret, signature, webhook, hay proxy endpoint.

## 8. Ket Luan Tong Hop

### Da chay duoc

- Web chat local.
- Backend local voi SQLite.
- Auto GIS preflight.
- Telegram bot.
- NetChat send message bang `MMAUTHTOKEN`.
- NetChat send one-shot script.
- NetChat polling bot code da co, phu thuoc quyen doc posts cua auth mode.

### Chua giai quyet dut diem

- Dung bot access token de read/write messaging endpoints NetChat.

Ly do:

```text
Bot token auth OK voi /api/v4/users/me,
nhung messaging APIs bi BMS chan voi api.context.bms_verified.app_error.
```

### Can lay them tu admin NetChat/BMS

Mot trong cac thong tin sau:

```text
- BMS verification header name/value
- BMS proxy endpoint cho bot API
- App secret/signature rule
- Service account token co scope messaging:read va messaging:write
- Webhook/callback chinh thuc cho bot
```

## 9. Luu Y Bao Mat

- Khong commit/paste Telegram token.
- Khong commit/paste NetChat bot access token.
- Khong commit/paste `MMAUTHTOKEN`.
- Neu token/cookie da bi paste vao chat, nen revoke/regenerate hoac logout session.
