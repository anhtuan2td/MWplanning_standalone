import httpx
import json

BASE = 'http://127.0.0.1:8000'

with httpx.Client(timeout=120.0) as client:
    print('=== GIS DOWNLOAD ===')
    payload = {'latitude': 13.74777, 'longitude': 109.19243, 'radius_km': 30}
    r = client.post(f'{BASE}/gis/download', json=payload)
    print(r.status_code)
    print(r.text[:2000])

    print('\n=== PLAN SINGLE LINK ===')
    payload = {
        'site_name': 'BDH0297',
        'latitude': 13.74777,
        'longitude': 109.19243,
        'tower_height_m': 15,
        'radius_km': 30,
        'band': 'AUTO',
    }
    r = client.post(f'{BASE}/plan/single-link', json=payload)
    print(r.status_code)
    if r.status_code == 200:
        data = r.json()
        summary = data.get('summary', {})
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        print('best_candidate present:', bool(data.get('best_candidate')))
    else:
        print(r.text)
