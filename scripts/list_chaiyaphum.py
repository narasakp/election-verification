# -*- coding: utf-8 -*-
import os, json

base = r'D:\Code\Election69\election-verification\downloads\ss518'
# Find the Chaiyaphum folder (could be Thai name)
for d in os.listdir(base):
    full = os.path.join(base, d)
    if os.path.isdir(full) and ('ชัยภูมิ' in d or 'chaiyaphum' in d.lower()):
        print(f"Found folder: {d}")
        # Walk and collect all files
        all_files = []
        for dp, dn, fn in os.walk(full):
            for f in fn:
                fp = os.path.join(dp, f)
                rel = os.path.relpath(fp, full)
                size = os.path.getsize(fp)
                all_files.append({"path": rel, "full": fp, "size": size})
        
        print(f"Total files: {len(all_files)}")
        print(f"\nDirectory structure:")
        # Show subdirs
        for dp, dn, fn in os.walk(full):
            rel = os.path.relpath(dp, full)
            indent = "  " * rel.count(os.sep)
            print(f"{indent}{os.path.basename(dp)}/ ({len(fn)} files)")
        
        print(f"\nFirst 30 files:")
        for i, f in enumerate(all_files[:30]):
            ext = os.path.splitext(f["path"])[1]
            print(f"  [{i+1}] {f['path']} ({f['size']:,} bytes) {ext}")
        
        # Save file list as JSON
        out = os.path.join(r'D:\Code\Election69\election-verification\data', 'chaiyaphum_files.json')
        with open(out, 'w', encoding='utf-8') as fh:
            json.dump(all_files, fh, ensure_ascii=False, indent=2, default=str)
        print(f"\nSaved file list to: {out}")
        break
else:
    print("Chaiyaphum folder not found!")
    print(f"Available folders: {os.listdir(base)}")
