# Huong Dan Chay MW Pre-planning Lite

Tai lieu nay tom tat 3 cach chay hien co:

1. Dung chat Telegram.
2. Gui ket qua qua NetChat.
3. Chay web local.
4. Build file EXE.

## 1. Dung Chat Telegram

Can co:

- Telegram bot token tao tu BotFather.
- Database local SQLite hoac data site da import.
- Internet neu can tu dong tai GIS.
- Cai dependency bang `requirements-chat.txt`, khong dung `requirements.txt` neu chi chay bot tren VPS.

Cai dependency:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
.\.venv\Scripts\python.exe -m pip install -r requirements-chat.txt
```

Chay bot:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:MW_TELEGRAM_BOT_TOKEN = "<telegram bot token>"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\telegram_bot.py
```

Lenh mau trong Telegram:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
```

Bot se:

- Kiem tra GIS can thiet cho toa do va ban kinh.
- Neu thieu DEM hoac WorldCover thi tu dong tai.
- Sau khi GIS san sang, chay planning.
- Tra ve best link va top candidates.

## 2. Gui Ket Qua Qua NetChat

Thong tin NetChat hien co:

```text
NETCHAT_API_ENDPOINT=https://netchat.viettel.vn/api/v4/posts
NETCHAT_CHANNEL_ID=xcq93473uin5ube9iyxhoeptza
NETCHAT_BOT_ID=rfm7pcsrdfgk7quzuyk7cbj7ze
```

Can co them token NetChat va set bien moi truong:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:NETCHAT_API_TOKEN = "<TOKEN_CUA_BAN>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
$env:NETCHAT_BOT_ID = "rfm7pcsrdfgk7quzuyk7cbj7ze"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
```

Script se thu gui them header:

```text
X-Bot-Id: rfm7pcsrdfgk7quzuyk7cbj7ze
```

Neu NetChat bao loi `API bot phai duoc goi qua BMS kem header xac minh hop le`, can xin admin BMS ten header va gia tri xac minh, roi set them:

```powershell
$env:NETCHAT_BMS_HEADER_NAME = "<TEN_HEADER_BMS>"
$env:NETCHAT_BMS_HEADER_VALUE = "<GIA_TRI_HEADER_BMS>"
```

Neu BMS yeu cau nhieu header, co the dung JSON:

```powershell
$env:NETCHAT_EXTRA_HEADERS_JSON = '{"X-BMS-Client":"...","X-BMS-Signature":"..."}'
```

Neu API Bearer bi chan boi BMS nhung ban co cookie session dang nhap NetChat nhu code mau `MMAUTHTOKEN`, co the chay cookie mode:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_API_TOKEN = "<GIA_TRI_COOKIE_MMAUTHTOKEN>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
```

De ben hon, khong copy cookie thu cong, co the de script tu login lay cookie:

```powershell
$env:NETCHAT_API_ENDPOINT = "https://netchat.viettel.vn/api/v4/posts"
$env:NETCHAT_AUTH_MODE = "cookie"
$env:NETCHAT_LOGIN_ID = "<TAI_KHOAN_NETCHAT>"
$env:NETCHAT_PASSWORD = "<MAT_KHAU_NETCHAT>"
$env:NETCHAT_CHANNEL_ID = "xcq93473uin5ube9iyxhoeptza"
```

Khi `NETCHAT_AUTH_MODE=cookie` va khong set `NETCHAT_API_TOKEN`, script se goi:

```text
POST https://netchat.viettel.vn/api/v4/users/login
```

roi lay `MMAUTHTOKEN` tu response cookie hoac `Token` tu response header.

Luu y: cach auto-login chi hoat dong neu NetChat cho phep login bang API username/password. Neu NetChat dung SSO, captcha, OTP hoac BMS rieng thi can API credential chinh thuc tu admin.

Trong cookie mode, script gui request voi browser-like headers va cookie:

```text
Cookie: MMAUTHTOKEN=<GIA_TRI_COOKIE_MMAUTHTOKEN>
X-Requested-With: XMLHttpRequest
Origin: https://netchat.viettel.vn
Referer: https://netchat.viettel.vn/
```

Khong commit hoac chia se gia tri `MMAUTHTOKEN`; day la session dang nhap.

Gui tin nhan test:

```powershell
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --message "Hello from MW Pre-planning"
```

Chay planning va gui ket qua vao NetChat:

```powershell
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --plan "/plan site DN001 16.032 108.221 radius 30 height 30"
```

Chay NetChat bot hai chieu bang polling channel:

```powershell
$env:NETCHAT_POLL_SECONDS = "4"
$env:NETCHAT_SKIP_EXISTING = "1"
.\.venv\Scripts\python.exe .\scripts\netchat_bot.py
```

Sau khi bot chay, nhan trong NetChat channel:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
```

Bot se doc tin moi bang:

```text
GET /api/v4/channels/{channel_id}/posts
```

va tra loi bang:

```text
POST /api/v4/posts
```

Ghi chu:

- `scripts/netchat_send.py` gui message mot lan.
- `scripts/netchat_bot.py` chay polling lien tuc de doc lenh moi trong channel.
- Neu bot tu doc lai message cua chinh no va lap vo han, set `NETCHAT_BOT_USER_ID` bang user id cua bot.

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
