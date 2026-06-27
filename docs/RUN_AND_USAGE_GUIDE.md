# Hướng Dẫn Chạy Và Sử Dụng MW Pre-planning

Tài liệu này dành cho bản hiện tại của MW Pre-planning, gồm cách chạy web local, chạy Telegram/NetChat bot, và cách sử dụng giao diện/chat.

## 1. Chuẩn Bị Runtime

### 1.1. File cần có trên máy chạy

Nếu chạy đầy đủ web + chat, copy các thư mục/file:

```text
backend/
config/
data/
frontend/
scripts/
requirements.txt
requirements-chat.txt
```

Nếu chỉ chạy chat trên VPS, copy tối thiểu:

```text
backend/
config/
data/
scripts/
requirements-chat.txt
```

Data quan trọng:

```text
data/mwplanner.db
data/mw_links/current_links.csv
data/dem/
data/worldcover/
```

Ghi chú:

- `data/mwplanner.db` chứa site inventory và metadata như cell 4G/5G, vu hồi, overload.
- `data/mw_links/current_links.csv` là nguồn tuyến MW runtime. Nếu thiếu file này, chat có thể trả `Tuyến MW: 0`.
- `data/dem/` và `data/worldcover/` cần cho planning có GIS/LOS/Fresnel. Nếu máy có Internet, bot/web có thể tự tải GIS khi thiếu.

### 1.2. Cài dependency

Chat-only trên VPS:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-chat.txt
```

Web/backend đầy đủ:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 1.3. Kiểm tra syntax sau khi copy

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts\telegram_bot.py scripts\netchat_bot.py backend\app\services\site_lookup.py
```

## 2. Cách Chạy

### 2.1. Chạy backend web

Terminal 1:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Kiểm tra:

```text
http://127.0.0.1:8000/health
```

### 2.2. Chạy frontend web

Terminal 2:

```powershell
cd D:\MWpre_planning_standalone_59c8a8a\frontend
..\.nodejs\node-v22.17.1-win-x64\node.exe node_modules\vite\bin\vite.js --host 127.0.0.1
```

Mở:

```text
http://127.0.0.1:5173/
```

### 2.3. Chạy Telegram bot

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:MW_TELEGRAM_BOT_TOKEN = "<telegram bot token>"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\telegram_bot.py
```

### 2.4. Chạy NetChat bot realtime

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:NETCHAT_SERVER_URL = "https://bot-netchat.viettel.vn"
$env:NETCHAT_TOKEN = "<netchat token>"
$env:NETCHAT_SSL_VERIFY = "false"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\netchat_bot.py
```

### 2.5. Chạy Telegram và NetChat song song

Mở 2 terminal riêng:

- Terminal 1 chạy `scripts\telegram_bot.py`.
- Terminal 2 chạy `scripts\netchat_bot.py`.

Cả hai bot dùng chung `MW_DATABASE_URL`. Sau khi copy code mới lên VPS, phải restart đúng process bot để nhận code mới và refresh cache runtime.

### 2.6. Test gửi NetChat một lần

```powershell
cd D:\MWpre_planning_standalone_59c8a8a
$env:NETCHAT_SERVER_URL = "https://bot-netchat.viettel.vn"
$env:NETCHAT_TOKEN = "<netchat token>"
$env:NETCHAT_SSL_VERIFY = "false"
$env:NETCHAT_AUTH_MODE = "bearer"
$env:MW_DATABASE_URL = "sqlite:///D:/MWpre_planning_standalone_59c8a8a/data/mwplanner.db"
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --check-auth
```

Gửi message test:

```powershell
.\.venv\Scripts\python.exe .\scripts\netchat_send.py --message "Hello from MW Pre-planning"
```

## 3. Hướng Dẫn Sử Dụng Giao Diện Web

### 3.1. Import dữ liệu

1. Bấm `Import site CSV`.
2. Chọn file site inventory.
3. Bấm `Import MW links`.
4. Chọn file tuyến MW hiện hữu.

Cột site tối thiểu:

```text
site_code,latitude,longitude
```

Cột khuyến nghị:

```text
site_code,site_name,latitude,longitude,tower_height_m,available_height_m,status,owner,region,overload,VH,cells_4g,cells_5g
```

File MW links sau import được lưu tại:

```text
data/mw_links/current_links.csv
```

### 3.2. Chạy single-site planning

Nhập các trường:

- `Site name`: mã site mới.
- `Latitude`, `Longitude`: tọa độ decimal.
- `Radius km`: bán kính quét tối đa.
- `Min radius km`: loại candidate gần hơn bán kính tối thiểu.
- `Tower m`: chiều cao treo antenna.
- `Band`: để `AUTO` nếu muốn hệ thống tự chọn.

Quy trình:

1. Kiểm tra site/MW links đã import.
2. Bấm `Download GIS` nếu thiếu DEM/WorldCover và máy có Internet.
3. Bấm `Run planning`.
4. Xem summary và bảng candidate.
5. Chọn candidate để xem map/terrain/calloff.
6. Export calloff XLS hoặc raw JSON/CSV nếu cần.

### 3.3. Chạy batch planning

Vào màn hình batch, import CSV có các cột:

```text
site_name,lat,long
```

Cột tùy chọn:

```text
tower_height_m,radius_km,min_radius_km,band,rain_zone,antenna_diameter_m,equipment_profile
```

Batch sẽ chạy từng site, hiển thị progress và trả top candidate theo từng dòng.

### 3.4. Ý nghĩa kết quả candidate

- `ACCEPTED`: candidate đạt rule chính.
- `RISKY`: có cảnh báo nhưng vẫn có thể xem xét.
- `DANGER`: rủi ro lớn như overload.
- `OVERLINK`: candidate đã có nhiều tuyến MW.
- `REJECTED`: bị loại theo rule hoặc LOS/Fresnel/operational constraint.

Các note thường gặp:

- `Danger - Overload N`: site có hệ số overload.
- `Band side conflict`: hết High/Low side phù hợp.
- `RRU keo dai`: site thuộc nhóm kéo dài cần thận trọng.
- `SCREENING_FALLBACK`: thiếu equipment profile phù hợp nên dùng mô hình screening.

## 4. Hướng Dẫn Sử Dụng Chat

Telegram và NetChat dùng cùng cú pháp.

### 4.1. Tra cứu thông tin trạm

Cú pháp lệnh:

```text
/site BDH0001
/lookup BDH0001
/tram BDH0001
BDH0001
```

Câu hỏi tự nhiên:

```text
trạm BDH0001 có bao nhiêu cell 4G?
BDH0001 đã vu hồi chưa?
BDH0001 overload bao nhiêu?
BDH0001 có những tuyến MW nào?
thông tin trạm BDH0001
```

Bot trả về:

- số tuyến MW của trạm;
- danh sách tuyến MW;
- số cell 4G/5G;
- trạng thái vu hồi;
- overload và hệ số overload.

### 4.2. Chạy planning qua chat

Cú pháp cơ bản:

```text
/plan site DN001 16.032 108.221 radius 30 height 30
```

Có `min_radius`:

```text
/plan site DN001 16.032 108.221 radius 30 min_radius 1 height 30
```

Các biến thể `min_radius` được hỗ trợ:

```text
min_radius 1
min radius 1
min-r 1
minimum radius 1
ban kinh toi thieu 1
bán kính tối thiểu 1
```

Ghi chú quan trọng:

- Nếu không nhập `radius`, chat dùng mặc định `radius 30`.
- `min_radius 1` nghĩa là loại candidate gần hơn 1 km, không làm bán kính quét tối đa thành 1 km.
- Candidate ở 2.1 km vẫn phải còn nếu các rule khác không loại.

### 4.3. Status và help

```text
/status
/help
```

`/status` trả đường dẫn DB, DEM, WorldCover mà bot đang dùng. Nếu chat trả sai dữ liệu, kiểm tra `/status` trước để chắc bot đang chạy đúng thư mục/runtime.

## 5. Checklist Deploy Lên VPS

Copy tối thiểu cho chat:

```text
scripts/telegram_bot.py
scripts/netchat_bot.py
scripts/netchat_send.py
backend/app/services/site_lookup.py
backend/app/services/mw_links.py
backend/app/models/site.py
backend/app/schemas/site.py
backend/app/services/sites.py
backend/app/database/session.py
backend/app/schemas/planning.py
backend/app/services/planner.py
config/planner_config.yaml
requirements-chat.txt
data/mwplanner.db
data/mw_links/current_links.csv
```

Nếu chat có chạy `/plan`, copy thêm GIS/runtime planner liên quan:

```text
backend/app/scoring/
backend/app/terrain/
backend/app/rf/
backend/app/services/equipment.py
backend/app/services/gis_preflight.py
data/dem/
data/worldcover/
data/equipment/
```

Sau khi copy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-chat.txt
.\.venv\Scripts\python.exe -m py_compile scripts\telegram_bot.py scripts\netchat_bot.py backend\app\services\site_lookup.py
```

Restart process bot:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_bot.py*' -or $_.CommandLine -like '*netchat_bot.py*' } | Select-Object ProcessId,CommandLine
```

Dừng process cũ bằng đúng `ProcessId`, rồi chạy lại bot bằng lệnh ở mục 2.3 hoặc 2.4.

## 6. Lỗi Thường Gặp

### Chat trả `Tuyến MW: 0`

Kiểm tra:

- VPS có `data/mw_links/current_links.csv` chưa.
- Bot đang chạy đúng thư mục chưa.
- `/status` có trỏ đúng `data/mwplanner.db` chưa.
- Đã restart bot sau khi copy file/import MW links chưa.

### Chat không nhận `min_radius`

Kiểm tra đã copy `scripts/telegram_bot.py` bản mới và restart cả Telegram/NetChat bot.

### Có candidate khi không dùng `min_radius`, nhưng mất khi `min_radius 1`

Với bản mới, `min_radius 1` không được parse nhầm thành `radius 1`. Kiểm tra lại:

```powershell
.\.venv\Scripts\python.exe -c "from scripts.telegram_bot import parse_plan; print(parse_plan('/plan site DN001 16.032 108.221 min_radius 1 height 30').model_dump())"
```

Kết quả đúng phải có:

```text
'radius_km': 30
'min_radius_km': 1
```

### Web không kết nối backend

Kiểm tra backend:

```text
http://127.0.0.1:8000/health
```

Nếu backend chưa chạy, chạy lại mục 2.1.

### Planning báo thiếu GIS

Nếu có Internet, bấm `Download GIS` hoặc để bot tự tải. Nếu chạy offline, copy sẵn file vào:

```text
data/dem/
data/worldcover/
```
