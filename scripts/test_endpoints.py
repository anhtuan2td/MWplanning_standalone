import httpx
from pathlib import Path

base = "http://127.0.0.1:8000"
client = httpx.Client(timeout=60.0)

print('=== calloff rules ===')
print(client.get(f"{base}/calloff/rules").text)

print('\n=== sites before ===')
print(client.get(f"{base}/sites?limit=5").text)

print('\n=== import sites ===')
with open(Path('data') / 'sites' / 'sample_sites.csv', 'rb') as f:
    r = client.post(f"{base}/sites/import", files={'file': ('sample_sites.csv', f, 'text/csv')})
    print(r.status_code, r.text)

print('\n=== sites after ===')
print(client.get(f"{base}/sites?limit=5").text)

print('\n=== import mw links ===')
with open(Path('data') / 'mw_links' / 'existing_links.csv', 'rb') as f:
    r = client.post(f"{base}/mw-links/import", files={'file': ('existing_links.csv', f, 'text/csv')})
    print(r.status_code, r.text)

print('\n=== plan single link ===')
payload = {
    "site_name": "TEST_SITE",
    "latitude": 13.76232,
    "longitude": 109.21494,
    "tower_height_m": 30,
    "radius_km": 30,
    "band": "AUTO",
}
r = client.post(f"{base}/plan/single-link", json=payload)
print(r.status_code)
print(r.text)
