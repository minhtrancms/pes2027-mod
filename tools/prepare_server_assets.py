#!/usr/bin/env python3
"""
Prepare Server Assets for pes.minhgame.com
Generates PES2027-data.zip and version.json for OTA automatic downloading.
"""

import os
import sys
import json
import time
import hashlib
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "assets_data", "PES2027-data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(REPO_ROOT, "PES2027-data")

WEB_DIR = os.path.join(REPO_ROOT, "web")
SERVER_DIR = os.path.join(REPO_ROOT, "build", "server_assets")
MANIFEST_PATH = os.path.join(DATA_DIR, "data-manifest.json")

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def main():
    if not os.path.exists(MANIFEST_PATH):
        print(f"Error: {MANIFEST_PATH} not found. Please ensure assets_data/PES2027-data exists.")
        sys.exit(1)

    os.makedirs(SERVER_DIR, exist_ok=True)
    os.makedirs(WEB_DIR, exist_ok=True)
    out_zip = os.path.join(WEB_DIR, "PES2027-data.zip")
    tmp_zip = out_zip + ".tmp"
    version_json_path = os.path.join(WEB_DIR, "version.json")

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    data_id = manifest.get("data_id", "pes2027-11.1.101-c7d098606d0e")

    print(f"=======================================================")
    print(f"   PREPARING ASSETS FOR SERVER (pes.minhgame.com)")
    print(f"=======================================================")
    print(f"Packaging {DATA_DIR} -> {out_zip} ...")
    t0 = time.time()

    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        print("  Adding data-manifest.json ...")
        z.write(MANIFEST_PATH, "data-manifest.json")

        for i, entry in enumerate(manifest.get("files", []), 1):
            rel_path = entry["path"]
            abs_path = os.path.join(DATA_DIR, rel_path)
            if not os.path.exists(abs_path):
                print(f"  [WARN] Missing file {abs_path}, skipping")
                continue
            size_mb = os.path.getsize(abs_path) / (1024 * 1024)
            if size_mb > 50 or i % 30 == 0:
                print(f"  [{i}/{len(manifest['files'])}] {rel_path} ({size_mb:.1f} MB)")
            z.write(abs_path, rel_path)

    os.replace(tmp_zip, out_zip)
    duration = time.time() - t0
    total_bytes = os.path.getsize(out_zip)
    total_size_gb = total_bytes / (1024 * 1024 * 1024)

    print(f"\nComputing SHA-256 for {out_zip} ...")
    file_hash = sha256_file(out_zip)

    version_data = {
        "version": "2027.1.0",
        "data_id": data_id,
        "data_url": "https://pes.minhgame.com/PES2027-data.zip",
        "size_bytes": total_bytes,
        "size_mb": round(total_bytes / (1024 * 1024), 1),
        "sha256": file_hash,
        "updated_at": int(time.time()),
        "title": "PES 2027 Legends Mod (Zidane, R9, Özil)",
        "notice": "Gói dữ liệu hoàn chỉnh eFootball 2027"
    }

    with open(version_json_path, "w", encoding="utf-8") as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)

    print(f"\n=======================================================")
    print(f"  SUCCESS! SERVER ASSETS CREATED:")
    print(f"  1. {out_zip} ({total_size_gb:.2f} GB)")
    print(f"  2. {version_json_path}")
    print(f"=======================================================")
    print(f"\nHƯỚNG DẪN UPLOAD LÊN SERVER:")
    print(f"Chỉ cần upload 2 file trên vào thư mục web root của pes.minhgame.com sao cho:")
    print(f"  - https://pes.minhgame.com/version.json")
    print(f"  - https://pes.minhgame.com/PES2027-data.zip")
    print(f"Game client trên iPhone sẽ tự động nhận diện và tải về 100% tự động!")

if __name__ == "__main__":
    main()
