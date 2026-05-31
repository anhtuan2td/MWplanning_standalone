# Huong dan su dung MW Pre-planning Lite

Tai lieu nay huong dan su dung tu dau voi gia dinh mac dinh la may moi chua co du lieu: chua co site, chua co MW links, chua co DEM.

## 1. Cac che do su dung

### Che do Internet

Dung khi may tinh co Internet.

- Co the bam `Download GIS` tren UI de tai GIS du lieu tu nguon online (DEM + WorldCover).
- Phu hop cho may ca nhan, may test, hoac moi truong duoc phep truy cap Internet.
- Basemap co the dung OpenStreetMap neu cau hinh frontend cho phep truy cap Internet.

### Che do Intranet

Dung khi may tinh nam trong mang noi bo, khong co Internet.

- Khong dung nut `Download GIS` neu mang noi bo khong cho truy cap nguon GIS online.
- Can copy san file DEM `.tif` vao thu muc `data\dem` nam canh file EXE.
- Neu can ban do nen cau hinh tile server noi bo; neu khong co, app van chay duoc voi grid/background co ban.
- Du lieu site va MW links duoc import tu file CSV noi bo.

## 2. Thu muc can chuyen sang may khac

Khuyen nghi copy ca thu muc:

```text
dist\
```

Toi thieu can co:

```text
dist\MWPreplanning.exe
```

Neu muon giu du lieu da import, copy kem:

```text
dist\data\mwplanner.db
dist\data\mw_links\current_links.csv
```

GIS du lieu co the tai lai neu may co Internet. Neu dung Intranet thi copy du lieu vao:

```text
 dist\data\dem\
 dist\data\worldcover\
```

## 3. Mo va tat phan mem

1. Chay:

```text
dist\MWPreplanning.exe
```

2. Trinh duyet mo:

```text
http://127.0.0.1:8000
```

3. De tat app dung nut `Exit app` tren UI.

Luu y: dong tab trinh duyet khong dong server nen nen dung `Exit app`. Phan mem da chan mo nhieu lan; neu mo lan thu hai, app se dua ve phien dang chay hoac thoat.

## 4. Trang thai ban dau khi chua co du lieu

Khi moi mo app tren may sach:

- `Imported sites` = 0
- `MW links` = 0, tru khi co file MW links mac dinh/da copy
- `DEM tiles` = 0
- `DEM regions` = `-`
- Bang candidate rong
- Ban do va terrain chua co ket qua

## 5. Import site CSV

1. Bam `Import site CSV`.
2. Chon file site inventory CSV.
3. Doi thong bao:

```text
CSV imported: ... inserted, ... updated, ... skipped
```

Cot toi thieu:

```text
site_code,latitude,longitude
```

Cot khuyen nghi:

```text
site_code,site_name,latitude,longitude,tower_height_m,available_height_m,status,owner,region,overload,VH
```

Ghi chu:

- `site_code`, `latitude`, `longitude` la bat buoc.
- `ground_elevation_m` khong bat buoc. Neu co DEM, app se lay elevation tu DEM; neu khong co DEM thi fallback ve `0`.
- `status` nen la `active` de site duoc dua vao scan.
- `overload` la so canh bao tai site.
- `VH=1` danh dau diverse routing.

## 6. Import MW links

1. Bam `Import MW links`.
2. Chon file MW route hien huu.
3. Doi thong bao:

```text
MW links imported: ...
```

File import se duoc luu tai:

```text
dist\data\mw_links\current_links.csv
```

MW links duoc dung de:

- dem so link hien huu tren candidate;
- canh bao `Overlink`;
- kiem tra High/Low side conflict;
- goi y duong kinh antenna theo lich su;
- chon chieu cao root site khong vuot qua chieu cao thap nhat dang dung.

## 7. Nhap thong tin new site

Dien cac truong ben trai:

- `Site name`: ma site moi.
- `Latitude`: vi do dang decimal.
- `Longitude`: kinh do dang decimal.
- `Tower m`: chieu cao antenna/treo du kien tai site moi.
- `Radius km`: ban kinh quet candidate.
- `Band`: de `AUTO`.

## 8. Chuan bi DEM

### Neu dung Internet

1. Nhap dung latitude/longitude/radius cua site moi.
2. Bam `Download GIS`.
3. Doi thong bao:

```text
DEM tiles: ... downloaded, ... existing, ... failed
```

Sau khi tai xong, app tu dong clear cache DEM va dung DEM moi cho tinh terrain/elevation.

### Neu dung Intranet

1. Chuan bi file DEM GeoTIFF `.tif` theo tile SRTM/Skadi.
2. Copy vao:

```text
dist\data\dem\
```

3. Mo app hoac bam `Refresh`.

Neu khong co DEM, app van scan duoc nhung elevation mac dinh co the ve `0`, ket qua LOS/Fresnel khong dang tin cho danh gia thuc dia.

## 9. Kiem tra DEM status

Status hien:

- `DEM tiles`: so tile DEM co trong thu muc runtime.
- `DEM regions`: cac tinh nam trong nhung tile DEM da co.

Mot tile DEM co the chua nhieu tinh. Neu tile co Lam Dong va Dak Lak/Khanh Hoa/Gia Lai thi status se hien tat ca tinh lien quan.

## 10. Chay scan

1. Kiem tra da import site.
2. Kiem tra da import MW links neu can rule operational/calloff.
3. Kiem tra DEM neu can terrain chinh xac.
4. Bam `Run planning`.
5. Co the bam `Stop scan` neu can huy.

Ket qua summary gom:

- `Total`
- `Accepted`
- `Rejected`
- `Best link`
- `Imported sites`
- `MW links`
- `DEM tiles`
- `Avg sec/link`
- `Total sec`

## 11. Doc bang candidate

Moi dong candidate co:

- `Rank`: thu hang.
- `Candidate`: ma site hien huu.
- `Distance`: khoang cach link.
- `Site status`: trang thai site.
- `LOS`: pass/fail line-of-sight.
- `Fresnel`: ty le clearance.
- `Band`: band duoc chon tu rule AUTO.
- `Score`: diem tong hop.
- `Status`: `ACCEPTED`, `RISKY`, `DANGER`, `OVERLINK`, hoac `REJECTED`.
- `Notes`: ly do/canh bao.

Mot so note quan trong:

- `Danger - Overload N`: site co overload.
- `Overlink`: site da co nhieu link MW.
- `RRU keo dai`: site code dang extended RRU/small cell.
- `Band side conflict`: High/Low side trong band group da bi dung het.

## 12. Xem map va terrain

Click vao mot dong candidate:

- Map highlight link duoc chon.
- Terrain profile hien terrain elevation, duong LOS va marker antenna dau xa.
- Neu terrain dang phang bat thuong hoac elevation = 0, kiem tra lai DEM.

## 13. Export ket qua

### Export calloff

1. Chon link khong bi `REJECTED`.
2. Bam `Export calloff XLS`.
3. Mo file `.xls` bang Excel.

File calloff gom:

- line name;
- frequency;
- distance;
- A/B end;
- High/Low side;
- antenna diameter;
- antenna height;
- azimuth;
- tilt.

### Export raw

Neu can debug hoac luu ket qua day du:

1. Tick `Show raw exports`.
2. Chon `Export JSON` hoac `Export CSV`.

## 14. Refresh

Bam `Refresh` de:

- xoa ket qua scan hien tai tren UI;
- xoa candidate dang chon;
- reload status site/MW links/DEM;
- giu nguyen du lieu da import.

## 15. Quy trinh khuyen nghi tu may sach

1. Copy `dist\` vao may.
2. Chay `MWPreplanning.exe`.
3. Import site CSV.
4. Import MW links CSV.
5. Nhap new site latitude/longitude/radius.
6. Internet: bam `Download GIS`.
7. Intranet: copy DEM `.tif` vao `dist\data\dem`, sau do bam `Refresh`.
8. Bam `Run planning`.
9. Chon candidate phu hop.
10. Xem map/terrain.
11. Export calloff XLS.
12. Bam `Exit app` khi ket thuc.

## 16. Su co thuong gap

### DEM regions khong hien tinh mong muon

- Bam `Refresh`.
- Kiem tra file `.tif` co nam trong `dist\data\dem`.
- Neu tile moi chua co mapping tinh trong app, can cap nhat bang tile-region trong backend.

### Elevation = 0

- Chua co DEM cho khu vuc link.
- DEM nam sai thu muc.
- File DEM khong phai GeoTIFF hop le.
- Da tai/copy DEM nhung chua refresh hoac app dang chay phien cu.

### Mo app lan hai khong thay gi

Phan mem chi cho chay mot instance. Neu app da chay nen, mo lan hai se khong tao server moi. Mo:

```text
http://127.0.0.1:8000
```

### Khong build/deploy duoc vi EXE dang chay

Tat app bang `Exit app`. Neu can dung PowerShell:

```powershell
Get-Process | Where-Object { $_.Path -like '*MWPreplanning.exe' } | Stop-Process
```
