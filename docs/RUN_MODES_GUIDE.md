# Huong Dan Chay MW Pre-planning Lite

Tai lieu nay tom tat cac cach chay hien co:

1. Chay qua chat: Telegram, NetChat, hoac ca hai song song.
2. Gui ket qua qua NetChat mot lan.
3. Chay web local.
4. Build file EXE.

## 1. Chay Qua Chat

Muc nay dung khi chi can bot chat, khong can frontend web.

Ho tro:

- Telegram bot: `scripts/telegram_bot.py`
- NetChat bot realtime WebSocket: `scripts/netchat_bot.py`
- Gui NetChat mot lan/test quyen: `scripts/netchat_send.py`

### 1.1 Can Copy Len May Chay Bot

Copy cac file/thu muc bat buoc:

```text
backend/
config/
data/
scripts/
requirements-chat.txt
```

Trong `scripts/`, can co toi thieu:

```text
scripts/telegram_bot.py
scripts/netchat_bot.py
scripts/netchat_send.py
```

Trong `data/`, nen copy:

```text
data/mwplanner.db
data/dem/
data/worldcover/
data/mw_links/
data/sites/
```

Ghi chu:

- `data/mwplanner.db` la SQLite DB local. Neu khong copy file nay, bot se tao DB moi va ban phai import site lai.
- `data/dem/` va `data/worldcover/` co the bo trong neu may bot co internet de auto download GIS.
- Neu chay offline/noi bo, nen copy san `data/dem/` va `data/worldcover/`.

Khong can copy neu chi chay chat:

```text
frontend/
.nodejs/
build/
dist/
packaging/
docker/
.venv/
node_modules/
```

Co the copy them de tham khao, nhung khong bat buoc:

```text
README.md
docs/
.env.example
```

### 1.2 Cai Dependency Chat

Tao/cai venv tren may chay bot:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-chat.txt
```

Neu da co `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-chat.txt
```

Khong dung full `requirements.txt` neu chi chay chat tren VPS/may bot, vi file full co PyInstaller va cac dependency build khong can thiet.

### 1.3 Bien Moi Truong Chung

Set database:

```powershell
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
```

Lenh chat mau dung cho ca Telegram va NetChat:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
```

Bot se:

- Kiem tra GIS can thiet cho toa do va ban kinh.
- Neu thieu DEM hoac WorldCover thi tu dong tai.
- Sau khi GIS san sang, chay planning.
- Tra ve best link va top candidates.

### 1.4 Chay Telegram Bot

Can co:

- Telegram bot token tao tu BotFather.
- Database local SQLite hoac data site da import.
- Internet neu can tu dong tai GIS.

Chay bot:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:MW_TELEGRAM_BOT_TOKEN = "<telegram bot token>"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\telegram_bot.py
```

### 1.5 Chay NetChat Bot Realtime

NetChat bot hien dung WebSocket theo mau `testNetChat.py`, khong polling REST nua.

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:NETCHAT_SERVER_URL = "https://bot-netchat.viettel.vn"
$env:NETCHAT_TOKEN = "<TOKEN_CUA_BAN>"
$env:NETCHAT_SSL_VERIFY = "false"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\netchat_bot.py
```

Script se:

- Lay thong tin bot bang:

```text
GET https://bot-netchat.viettel.vn/api/v4/users/me
```

- Nghe tin realtime qua:

```text
wss://bot-netchat.viettel.vn/api/v4/websocket
```

- Tra loi qua:

```text
POST https://bot-netchat.viettel.vn/api/v4/posts
```

Sau khi bot chay, nhan trong NetChat:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
```

### 1.6 Chay Telegram Va NetChat Song Song

Mo 2 terminal rieng.

Terminal 1:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:MW_TELEGRAM_BOT_TOKEN = "<telegram bot token>"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\telegram_bot.py
```

Terminal 2:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:NETCHAT_SERVER_URL = "https://bot-netchat.viettel.vn"
$env:NETCHAT_TOKEN = "<netchat bot token>"
$env:NETCHAT_SSL_VERIFY = "false"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\netchat_bot.py
```

Luu y:

- Ca hai bot dung chung SQLite DB.
- Neu ca hai cung chay planning nang va cung tai GIS, co the cham. Nen chuan bi GIS truoc hoac tranh chay nhieu lenh nang cung luc.

## 2. Gui Ket Qua Qua NetChat Mot Lan / Test NetChat

Dung script nay de test token hoac gui mot message/ket qua planning, khong chay bot realtime.

Set env:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:NETCHAT_SERVER_URL = "https://bot-netchat.viettel.vn"
$env:NETCHAT_TOKEN = "<TOKEN_CUA_BAN>"
$env:NETCHAT_SSL_VERIFY = "false"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
```

Kiem tra auth:

```powershell
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --check-auth
```

Gui tin nhan test:

```powershell
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --message "Hello from MW Pre-planning"
```

Chay planning va gui ket qua vao NetChat:

```powershell
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --plan "/plan site DN001 16.032 108.221 radius 30 height 30"
```

Neu can test cookie session browser, van co the dung cookie mode, nhung day chi la cach tam thoi:

```powershell
$env:NETCHAT_SERVER_URL = "https://netchat.viettel.vn"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_TOKEN = "<GIA_TRI_COOKIE_MMAUTHTOKEN>"
$env:NETCHAT_MMUSERID = "<GIA_TRI_COOKIE_MMUSERID>"
$env:NETCHAT_MMCSRF = "<GIA_TRI_COOKIE_MMCSRF>"
```

Khong commit hoac chia se token/cookie.

## 3. Chay Web Local

Can chay 2 thanh phan: backend va frontend.

### Backend

Mo terminal thu nhat:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Kiem tra backend:

```text
http://127.0.0.1:8000/health
```

Ket qua dung:

```text
status: ok
database: ok
```

### Frontend

Mo terminal thu hai:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a\frontend
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\vite\bin\vite.js --host 127.0.0.1
```

Mo trinh duyet:

```text
http://127.0.0.1:5173/
```

Ghi chu:

- Neu frontend bao khong ket noi duoc backend, hay kiem tra backend `127.0.0.1:8000` da chay chua.
- Neu backend bi dung o buoc startup, hay chac chan da set `MW_DATABASE_URL` sang SQLite nhu lenh tren. Mac dinh dev co the tro toi PostgreSQL.

## 4. Tao File EXE

Can co:

- Python dependencies da cai trong `.venv`.
- Node/npm hoac Node bundled trong `.nodejs`.
- Frontend build duoc.
- PyInstaller tu `requirements.txt`.

Build truc tiep:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Neu `npm` khong co trong PATH, build frontend thu cong bang Node bundled truoc:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a\frontend
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\typescript\bin\tsc
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\vite\bin\vite.js build
```

Sau do quay lai root va build EXE:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Output EXE nam trong thu muc `dist` hoac theo duong dan ma script build in ra.

## Ghi Chu Ve GIS

Ca web chat va Telegram bot deu da co buoc auto GIS preflight:

- Truoc khi planning, he thong tinh cac DEM/WorldCover tile can cho toa do va ban kinh hien tai.
- Neu thieu tile, he thong goi download GIS.
- Neu download loi tile nao, planning se dung va bao loi.
- Neu GIS da du, planning chay ngay.

Neu chay offline/noi bo, co the copy san file GIS vao:

```text
data/dem/
data/worldcover/
```
