import json, time, hashlib, os, requests
from pathlib import Path
CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "HerEvidence-hackathon/1.0 (educational project)", "Accept": "application/json"}

def get_json(url, params=None, retries=3, pause=0.3):
    """GET with disk cache + retries. Returns parsed JSON, or None on 404 / refusal / repeated failure.
    4xx refusals are printed with the server's own message and are NOT retried."""
    key = hashlib.md5((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=30, headers=HEADERS)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                print("  ! rate limited (429), waiting..."); time.sleep(3 * (i + 1)); continue
            if r.status_code in (400, 401, 403):
                print(f"  ! HTTP {r.status_code} from {url.split('?')[0]}: {r.text[:200].strip()}")
                return None
            r.raise_for_status()
            data = r.json()
            f.write_text(json.dumps(data))
            time.sleep(pause)
            return data
        except requests.RequestException as e:
            print(f"  ! request failed ({e}); retry {i + 1}/{retries}")
            time.sleep(1.5 * (i + 1))
    return None
