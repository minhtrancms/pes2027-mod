#!/usr/bin/env python3
"""Package PES2027-data folder into PES2027-data-<data_id>.zip (ZIP_STORED, ZIP64).
"""
import json
import os
import sys
import time
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "PES2027-data")
OUT_DIR = os.path.join(REPO_ROOT, "build", "output")
MANIFEST_PATH = os.path.join(DATA_DIR, "data-manifest.json")

def main():
    if not os.path.exists(MANIFEST_PATH):
        print(f"Error: {MANIFEST_PATH} not found")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    data_id = manifest.get("data_id", "pes2027-11.1.101-c7d098606d0e")
    out_zip = os.path.join(OUT_DIR, f"PES2027-data-{data_id}.zip")
    tmp_zip = out_zip + ".tmp"
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Packaging {DATA_DIR} -> {out_zip} ...")
    total_files = len(manifest["files"]) + 1
    t0 = time.time()

    with zipfile.ZipFile(tmp_zip, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as z:
        # 1. Root data-manifest.json
        print("  Adding data-manifest.json ...")
        z.write(MANIFEST_PATH, "data-manifest.json")

        # 2. Add all data files
        for i, entry in enumerate(manifest["files"], 1):
            rel_path = entry["path"]
            abs_path = os.path.join(DATA_DIR, rel_path)
            if not os.path.exists(abs_path):
                print(f"Error: Missing file {abs_path}")
                sys.exit(1)
            size_mb = os.path.getsize(abs_path) / (1024 * 1024)
            if size_mb > 50 or i % 20 == 0:
                print(f"  [{i}/{len(manifest['files'])}] {rel_path} ({size_mb:.1f} MB)")
            z.write(abs_path, rel_path)

    os.replace(tmp_zip, out_zip)
    duration = time.time() - t0
    total_size_gb = os.path.getsize(out_zip) / (1024 * 1024 * 1024)
    print(f"SUCCESS: Created {out_zip} ({total_size_gb:.2f} GB) in {duration:.1f}s")

if __name__ == "__main__":
    main()
