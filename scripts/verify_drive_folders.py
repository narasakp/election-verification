"""Verify province names by checking actual Drive folder names via API."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from server import get_google_api_key
import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DRIVE_API = "https://www.googleapis.com/drive/v3"

api_key = get_google_api_key()
mapping = json.load(open(DATA_DIR / "ect_drive_mapping.json", encoding="utf-8"))

print(f"API Key: {api_key[:20]}...")
print(f"Entries to verify: {len(mapping)}\n")

verified = []
for i, entry in enumerate(mapping):
    fid = entry["folder_id"]
    try:
        r = requests.get(
            f"{DRIVE_API}/files/{fid}",
            params={"key": api_key, "fields": "id,name,mimeType"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            real_name = data["name"]
            old_name = entry["province"]
            changed = "✏️" if real_name != old_name else "✅"
            print(f"  {i+1:2d}. {changed} {old_name:25s} → {real_name}")
            entry["province"] = real_name
            entry["drive_folder_name"] = real_name
        else:
            print(f"  {i+1:2d}. ❌ {entry['province']:25s} → HTTP {r.status_code}")
    except Exception as e:
        print(f"  {i+1:2d}. ⚠️ {entry['province']:25s} → {e}")
    
    verified.append(entry)
    time.sleep(0.1)  # rate limit

# Save verified mapping
out_path = DATA_DIR / "ect_drive_mapping.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(verified, f, ensure_ascii=False, indent=2)
print(f"\n💾 Updated {out_path}")
print(f"Total: {len(verified)} provinces")
