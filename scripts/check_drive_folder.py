"""Check what's inside the กกต. Google Drive folder."""
import sys
sys.path.insert(0, ".")
from server import get_google_api_key, _drive_api_list_files

FOLDER_ID = "1fPkBLx7rwoK9f6QRl6gwFxLzXYYpPSb8"
api_key = get_google_api_key()
print(f"API Key: {api_key[:20]}...")
print(f"Folder: {FOLDER_ID}\n")

# List all items (folders + files)
try:
    items = _drive_api_list_files(FOLDER_ID, api_key)
    folders = [f for f in items if f["mimeType"] == "application/vnd.google-apps.folder"]
    files = [f for f in items if f["mimeType"] != "application/vnd.google-apps.folder"]
    
    print(f"=== Subfolders ({len(folders)}) ===")
    for f in sorted(folders, key=lambda x: x["name"]):
        print(f"  📁 {f['name']}  (id: {f['id']})")
    
    print(f"\n=== Files ({len(files)}) ===")
    for f in sorted(files, key=lambda x: x["name"])[:20]:
        size = f.get("size", "?")
        print(f"  📄 {f['name']}  ({size} bytes)")
    if len(files) > 20:
        print(f"  ... and {len(files) - 20} more files")
        
except Exception as e:
    print(f"Error: {e}")
