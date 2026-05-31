import json
from pathlib import Path
import httpx

BASE = "http://127.0.0.1:8000"

site_csv = "site_code,site_name,latitude,longitude,tower_height_m,available_height_m,status,owner,region,overload,VH\nBDH0297,BDH0297,13.74777,109.19243,15,15,active,Test,Test,0,1\n"

print('=== HEALTH ===')
with httpx.Client(timeout=60.0) as client:
    r = client.get(f"{BASE}/health")
    print(r.status_code, r.text)

    print('\n=== SYSTEM STATUS BEFORE ===')
    r = client.get(f"{BASE}/system/status")
    print(r.status_code, r.text)

    print('\n=== SITE IMPORT ===')
    r = client.post(f"{BASE}/sites/import", files={'file': ('BDH0297.csv', site_csv, 'text/csv')})
    print(r.status_code, r.text)

    print('\n=== SITES AFTER IMPORT ===')
    r = client.get(f"{BASE}/sites?limit=20")
    print(r.status_code, r.text)

    print('\n=== MW LINKS IMPORT ===')
    existing_links_path = Path('data') / 'mw_links' / 'existing_links.csv'
    with existing_links_path.open('rb') as f:
        r = client.post(f"{BASE}/mw-links/import", files={'file': ('existing_links.csv', f, 'text/csv')})
    print(r.status_code, r.text)

    print('\n=== DEM DOWNLOAD ===')
    payload = {'latitude': 13.74777, 'longitude': 109.19243, 'radius_km': 30}
    r = client.post(f"{BASE}/dem/download", json=payload)
    print(r.status_code)
    print(r.text)

    print('\n=== PLAN SINGLE LINK ===')
    payload = {
        'site_name': 'BDH0297',
        'latitude': 13.74777,
        'longitude': 109.19243,
        'tower_height_m': 15,
        'radius_km': 30,
        'band': 'AUTO',
    }
    r = client.post(f"{BASE}/plan/single-link", json=payload)
    print(r.status_code)
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(r.text)
