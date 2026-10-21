#!/usr/bin/env python3
"""
Restore PES2027 full data zip, mods, database, and SaveData files to connected iPhone via USB.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.house_arrest import HouseArrestService

from pymobiledevice3.services.installation_proxy import InstallationProxyService

BUNDLE_IDS = [
    "jp.konami.pesactionmobile.WXK53U737T.WXK53U737T.WXK53U737T",
    "jp.konami.pesactionmobile.WXK53U737T.WXK53U737T",
    "jp.konami.pesactionmobile.WXK53U737T",
    "jp.konami.pesactionmobile"
]

REPO_ROOT = Path("/Users/nhatminh/Sites/localhost/MyProject/pes2027-mod")
EXPORT_DIR = REPO_ROOT / "PES2027_Save_Export_20261020_232303"
DATA_ZIP = REPO_ROOT / "web" / "PES2027-data.zip"
DT870_SRC = REPO_ROOT / "build" / "staging" / "Payload" / "PESmobile.app" / "ziru" / "livedata" / "dt870_mobile_and.cpk"
PC8000_DIR = REPO_ROOT / "ziru-extra" / "pak_extra"
RESPONSES_DIR = REPO_ROOT / "ziru-extra" / "responses"
FACES_DIR = REPO_ROOT / "assets_data" / "PES2027-data" / "pak"

async def push_directory_recursive(service, local_dir: Path, remote_dir: str):
    for item in local_dir.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(local_dir)
            target_remote = f"{remote_dir}/{rel_path}".replace("\\", "/")
            parent_remote = "/".join(target_remote.split("/")[:-1])
            try:
                await service.makedirs(parent_remote)
            except Exception:
                pass
            await service.push(str(item), target_remote, progress_bar=False)

async def resolve_pes_bundle_id(lockdown):
    try:
        async with InstallationProxyService(lockdown) as ips:
            apps = await ips.get_apps(application_type="User")
            for app_id in apps.keys():
                if "pesactionmobile" in app_id.lower() or "pes2027" in app_id.lower():
                    try:
                        async with await HouseArrestService.create(lockdown, app_id, documents_only=False):
                            return app_id
                    except Exception:
                        pass
    except Exception:
        pass

    for bid in BUNDLE_IDS:
        try:
            async with await HouseArrestService.create(lockdown, bid, documents_only=False):
                return bid
        except Exception:
            pass
    return None

async def main():
    print("=======================================================")
    print("      RESTORE PES 2027 DATA & DATABASE TO IPHONE")
    print("=======================================================")
    print("Connecting to device via usbmuxd...")

    try:
        lockdown = await create_using_usbmux()
    except Exception as e:
        print(f"[ERROR] Could not connect to iOS device: {e}")
        sys.exit(1)

    print(f"Connected to: {lockdown.display_name} ({lockdown.product_type}, iOS {lockdown.product_version})")

    target_bid = await resolve_pes_bundle_id(lockdown)

    if not target_bid:
        print("[ERROR] PES container not found on device!")
        sys.exit(1)

    print(f"Target Bundle ID: {target_bid}")

    async with await HouseArrestService.create(lockdown, target_bid, documents_only=False) as service:
        # Step 1: Ensure base directories
        for d in ["Documents", "Documents/pak", "Documents/livedata", "Documents/responses", "Library/Application Support/PES2027/Save"]:
            if not await service.exists(d):
                await service.makedirs(d)

        # Step 2: Push database
        save_db = REPO_ROOT / "ziru_save.db"
        if not save_db.exists():
            save_db = EXPORT_DIR / "ziru_save.db"
        if save_db.exists():
            remote_save_folder = "Library/Application Support/PES2027/Save"
            for wal_file in ["ziru_save.db-wal", "ziru_save.db-shm"]:
                wal_remote = f"{remote_save_folder}/{wal_file}"
                if await service.exists(wal_remote):
                    try:
                        await service.rm(wal_remote)
                    except Exception:
                        pass

            remote_db_path = f"{remote_save_folder}/ziru_save.db"
            db_size_mb = save_db.stat().st_size / (1024 * 1024)
            print(f"\n[1/6] Pushing database: {save_db.name} ({db_size_mb:.2f} MB) -> {remote_db_path}...", flush=True)
            t0 = time.time()
            await service.push(str(save_db), remote_db_path, progress_bar=False)
            print(f"  -> Done database in {time.time() - t0:.2f}s!")

        # Step 3: Push SaveData directory
        save_data_dir = EXPORT_DIR / "SaveData"
        if save_data_dir.exists():
            print(f"\n[2/6] Pushing SaveData directory -> Documents/SaveData ...", flush=True)
            t_sd = time.time()
            await push_directory_recursive(service, save_data_dir, "Documents/SaveData")
            print(f"  -> Done SaveData in {time.time() - t_sd:.2f}s!")

        # Step 4: Push responses
        if RESPONSES_DIR.exists():
            print("\n[3/6] Pushing mod responses (box draws, events, banners)...", flush=True)
            t_resp = time.time()
            await push_directory_recursive(service, RESPONSES_DIR, "Documents/responses")
            cmd_login = RESPONSES_DIR / "CmdLogin.json"
            if cmd_login.exists():
                await service.push(str(cmd_login), "Documents/CmdLogin.json", progress_bar=False)
            print(f"  -> Done responses in {time.time() - t_resp:.2f}s!")

        # Step 5: Push updated assets (dt870, pc8000, pc7999, pc3700)
        print("\n[4/6] Pushing real club names, logos & 3D face models...", flush=True)
        if DT870_SRC.exists():
            try:
                await service.push(str(DT870_SRC), "Documents/livedata/dt870_mobile_and.cpk", progress_bar=False)
                await service.push(str(DT870_SRC), "Documents/livedata/dt870_mobile_ios.cpk", progress_bar=False)
                print("  -> Pushed real club names (dt870)")
            except Exception as e:
                print(f"  [WARN] livedata: {e}")

        # Real logos & boots
        for stem in ["pc8000_mobile_ios", "pc7999_mobile_ios"]:
            for ext in ["pak", "ucas", "utoc"]:
                src = PC8000_DIR / f"{stem}.{ext}"
                if src.exists():
                    try:
                        await service.push(str(src), f"Documents/pak/{stem}.{ext}", progress_bar=False)
                        print(f"  -> Pushed {stem}.{ext}")
                    except Exception as e:
                        print(f"  [WARN] {stem}.{ext}: {e}")

        # 3D faces (pc3700, pc0101)
        if FACES_DIR.exists():
            for p_file in ["pc3700_mobile_ios.pak", "pc3700_mobile_ios.ucas", "pc3700_mobile_ios.utoc",
                           "pc3700_mobile_and.pak", "pc3700_mobile_and.ucas", "pc3700_mobile_and.utoc",
                           "pc0101_mobile_ios.pak", "pc0101_mobile_ios.ucas", "pc0101_mobile_ios.utoc",
                           "global_mobile_ios.ucas", "global_mobile_ios.utoc"]:
                f_path = FACES_DIR / p_file
                if f_path.exists():
                    try:
                        await service.push(str(f_path), f"Documents/pak/{p_file}", progress_bar=False)
                        print(f"  -> Pushed face mod: {p_file}")
                    except Exception as e:
                        print(f"  [WARN] face: {p_file}: {e}")

        # Step 6: Push PES2027-data.zip (Heavy data, optional via --full-data)
        push_full_data = "--full-data" in sys.argv
        if push_full_data and DATA_ZIP.exists():
            remote_zip = "Documents/PES2027-data.zip"
            zip_size_mb = DATA_ZIP.stat().st_size / (1024 * 1024)
            print(f"\n[5/6] Pushing heavy data package: {DATA_ZIP.name} ({zip_size_mb:.1f} MB) -> {remote_zip}...", flush=True)
            t_zip = time.time()
            await service.push(str(DATA_ZIP), remote_zip, progress_bar=True)
            elapsed = time.time() - t_zip
            speed = zip_size_mb / elapsed if elapsed > 0 else 0
            print(f"\n  -> Done PES2027-data.zip in {elapsed:.1f}s (~{speed:.1f} MB/s)!", flush=True)
        else:
            print("\n[5/6] Skipping heavy PES2027-data.zip (already on device, use --full-data if re-installing).")

        # Verification
        print("\n=======================================================")
        print("--- VERIFICATION ON IPHONE ---")
        docs = await service.listdir("Documents")
        print(f"Documents contents: {docs}")
        if await service.exists("Library/Application Support/PES2027/Save/ziru_save.db"):
            stat = await service.stat("Library/Application Support/PES2027/Save/ziru_save.db")
            print(f"Database verified: {stat}")
        if push_full_data and await service.exists(remote_zip):
            stat_zip = await service.stat(remote_zip)
            print(f"Data zip verified: {stat_zip}")
        print("=======================================================")
        print("[HOAN TAT] Da chep xong toan bo data va database vao iPhone thanh cong!")

if __name__ == "__main__":
    asyncio.run(main())
