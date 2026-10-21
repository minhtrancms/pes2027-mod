#!/usr/bin/env python3
"""
Import save database and SaveData files from export directory to connected iPhone.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.house_arrest import HouseArrestService

BUNDLE_IDS = [
    "jp.konami.pesactionmobile.WXK53U737T.WXK53U737T.WXK53U737T",
    "jp.konami.pesactionmobile.WXK53U737T.WXK53U737T",
    "jp.konami.pesactionmobile.WXK53U737T",
    "jp.konami.pesactionmobile"
]
EXPORT_DIR = Path("/Users/nhatminh/Sites/localhost/MyProject/pes2027-mod/PES2027_Save_Export_20261020_232303")

async def push_directory_recursive(service, local_dir: Path, remote_dir: str):
    for item in local_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(local_dir)
            target_remote = f"{remote_dir}/{rel_path}".replace("\\", "/")
            # Ensure parent remote directory exists or push directly
            parent_remote = "/".join(target_remote.split("/")[:-1])
            try:
                await service.shell.mkdir(parent_remote)
            except Exception:
                pass
            
            size_kb = item.stat().st_size / 1024
            print(f"[PUSH FILE] {item.name} ({size_kb:.1f} KB) -> {target_remote}...", flush=True)
            await service.push(str(item), target_remote, progress_bar=False)

async def main():
    if not EXPORT_DIR.exists():
        print(f"[ERROR] Export directory does not exist: {EXPORT_DIR}")
        sys.exit(1)

    save_db = EXPORT_DIR / "ziru_save.db"
    save_data_dir = EXPORT_DIR / "SaveData"

    if not save_db.exists():
        print(f"[ERROR] Database file not found: {save_db}")
        sys.exit(1)

    print("Connecting to device via usbmuxd...")
    lockdown = await create_using_usbmux()
    print(f"Connected to: {lockdown.display_name} ({lockdown.product_type}, iOS {lockdown.product_version})")

    target_bid = None
    for bid in BUNDLE_IDS:
        try:
            async with await HouseArrestService.create(lockdown, bid, documents_only=False):
                target_bid = bid
                break
        except Exception:
            pass

    if not target_bid:
        print("[ERROR] Không tìm thấy PES container trên thiết bị.")
        sys.exit(1)

    print(f"Target Bundle ID: {target_bid}")
    async with await HouseArrestService.create(lockdown, target_bid, documents_only=False) as service:
        # Step 1: Clean up any WAL/SHM locks if present
        remote_save_folder = "Library/Application Support/PES2027/Save"
        try:
            await service.shell.mkdir(remote_save_folder)
        except Exception:
            pass

        for wal_file in ["ziru_save.db-wal", "ziru_save.db-shm"]:
            wal_remote = f"{remote_save_folder}/{wal_file}"
            if await service.exists(wal_remote):
                print(f"[CLEANUP] Removing stale lock {wal_remote}...")
                try:
                    await service.shell.rm(wal_remote)
                except Exception as e:
                    print(f"  Warning removing {wal_file}: {e}")

        # Step 2: Push ziru_save.db
        remote_db_path = f"{remote_save_folder}/ziru_save.db"
        db_size_mb = save_db.stat().st_size / (1024 * 1024)
        print(f"\n[PUSH DB] {save_db.name} ({db_size_mb:.2f} MB) -> {remote_db_path}...", flush=True)
        t0 = time.time()
        await service.push(str(save_db), remote_db_path, progress_bar=False)
        print(f"  -> DB push finished in {time.time() - t0:.2f}s", flush=True)

        # Step 3: Push SaveData files
        if save_data_dir.exists():
            print(f"\n[PUSH SAVEDATA] Pushing contents of {save_data_dir.name} -> Documents/SaveData ...")
            try:
                await service.shell.mkdir("Documents/SaveData")
            except Exception:
                pass
            await push_directory_recursive(service, save_data_dir, "Documents/SaveData")

        # Step 4: Verification
        print("\n--- Verification ---")
        if await service.exists(remote_db_path):
            stat = await service.stat(remote_db_path)
            remote_size = stat.get('st_size') or stat.get('size') if isinstance(stat, dict) else getattr(stat, 'st_size', None)
            print(f"[OK] {remote_db_path} exists on device! Remote size: {remote_size} bytes (Local: {save_db.stat().st_size} bytes)")
        else:
            print(f"[FAIL] {remote_db_path} not found on device!")

    print("\n[SUCCESS] Save data and database imported successfully!")
    print("Vui long vuot dong (kill) app tren iPhone va mo lai de load save moi.")

if __name__ == "__main__":
    asyncio.run(main())
