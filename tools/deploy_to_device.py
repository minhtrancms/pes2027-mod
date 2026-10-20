#!/usr/bin/env python3
"""
Deploy mod data, 3D faces, card textures, and starting squad directly to connected iPhone via USB.
"""

import asyncio
import os
import sys
import time
import json
import sqlite3
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.house_arrest import HouseArrestService

BUNDLE_ID = "jp.konami.pesactionmobile.WXK53U737T"
WORKSPACE_ROOT = Path("/Users/nhatminh/Sites/localhost/MyProject/pes2027-mod")

async def push_file_safe(service, local_path: Path, remote_path: str):
    if not local_path.exists():
        print(f"[SKIP] Local file not found: {local_path}")
        return
    size_mb = local_path.stat().st_size / (1024 * 1024)
    print(f"[PUSH] {local_path.name} ({size_mb:.2f} MB) -> {remote_path}...", flush=True)
    t0 = time.time()
    await service.push(str(local_path), remote_path, progress_bar=False)
    elapsed = time.time() - t0
    speed = (size_mb / elapsed) if elapsed > 0 else 0
    print(f"       -> Done in {elapsed:.1f}s ({speed:.1f} MB/s)", flush=True)

def prepare_updated_db(db_path: Path) -> Path:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT squad_json FROM squads WHERE squad_id = 9")
    row = c.fetchone()
    if not row:
        print("[DB] Warning: squad 9 not found in database!")
        conn.close()
        return db_path
    
    squad = json.loads(row[0])
    player_list = squad.get("player_list", [])
    
    # Target starters
    r9 = {"gameplayer_id": {"id": 37576, "serial": 359042717000000991}, "uniform_number": 9}
    zidane = {"gameplayer_id": {"id": 9901397, "serial": 359042717000000990}, "uniform_number": 10}
    ozil = {"gameplayer_id": {"id": 40291, "serial": 359042717000000992}, "uniform_number": 11}
    
    old_3 = player_list[3]
    old_8 = player_list[8]
    old_9 = player_list[9]
    
    player_list[3] = r9
    player_list[8] = zidane
    player_list[9] = ozil
    
    existing_serials = {p["gameplayer_id"]["serial"] for p in player_list[:11]}
    for i in range(11, len(player_list)):
        if player_list[i]["gameplayer_id"]["serial"] in [359042717000000990, 359042717000000991, 359042717000000992]:
            if old_3["gameplayer_id"]["serial"] not in existing_serials:
                player_list[i] = old_3
                existing_serials.add(old_3["gameplayer_id"]["serial"])
            elif old_8["gameplayer_id"]["serial"] not in existing_serials:
                player_list[i] = old_8
                existing_serials.add(old_8["gameplayer_id"]["serial"])
            elif old_9["gameplayer_id"]["serial"] not in existing_serials:
                player_list[i] = old_9
                existing_serials.add(old_9["gameplayer_id"]["serial"])
                
    squad["player_list"] = player_list
    now_ms = int(time.time() * 1000)
    c.execute("UPDATE squads SET squad_json = ?, updated_at = ? WHERE squad_id = 9", (json.dumps(squad), now_ms))
    conn.commit()
    conn.close()
    print("[DB] Squad 9 updated: Zidane (No. 10), Ronaldo R9 (No. 9), Özil (No. 11) in starting lineup!")
    return db_path

async def main():
    print(f"Connecting to device via usbmuxd (Bundle ID: {BUNDLE_ID})...")
    lockdown = await create_using_usbmux()
    print(f"Connected to {lockdown.display_name} ({lockdown.product_type}, iOS {lockdown.product_version})")

    async with await HouseArrestService.create(lockdown, BUNDLE_ID, documents_only=False) as service:
        # Step 1: Update starting squad in ziru_save.db
        print("\n--- 1. Updating squad starting lineup in ziru_save.db ---")
        db_remote = "Library/Application Support/PES2027/Save/ziru_save.db"
        local_db = Path("/tmp/ziru_save_device.db")
        if await service.exists(db_remote):
            content = await service.get_file_contents(db_remote)
            local_db.write_bytes(content)
            prepare_updated_db(local_db)
            await push_file_safe(service, local_db, db_remote)
        else:
            print("[WARN] Remote ziru_save.db not found, skipping DB edit.")

        # Step 2: Push responses directory
        print("\n--- 2. Pushing mod responses (Box draws, direct sign config, events, banners) ---")
        responses_src = WORKSPACE_ROOT / "ziru-extra" / "responses"
        await service.push(str(responses_src), "Documents", progress_bar=False)
        print("       -> Successfully synced Documents/responses!")
        
        # Also copy CmdLogin.json to Documents root
        cmd_login = responses_src / "CmdLogin.json"
        if cmd_login.exists():
            await push_file_safe(service, cmd_login, "Documents/CmdLogin.json")

        # Step 3: Push 3D face models & mod texture packs
        print("\n--- 3. Pushing 3D face models & mod texture packs into Documents/pak ---")
        pak_source = WORKSPACE_ROOT / "assets_data" / "PES2027-data" / "pak"
        pak_files_to_push = [
            (pak_source / "pc3700_mobile_ios.pak", "Documents/pak/pc3700_mobile_ios.pak"),
            (pak_source / "pc3700_mobile_ios.utoc", "Documents/pak/pc3700_mobile_ios.utoc"),
            (pak_source / "pc3700_mobile_ios.ucas", "Documents/pak/pc3700_mobile_ios.ucas"),
            (pak_source / "pc3700_mobile_and.pak", "Documents/pak/pc3700_mobile_and.pak"),
            (pak_source / "pc3700_mobile_and.utoc", "Documents/pak/pc3700_mobile_and.utoc"),
            (pak_source / "pc3700_mobile_and.ucas", "Documents/pak/pc3700_mobile_and.ucas"),
            (pak_source / "pc0101_mobile_ios.pak", "Documents/pak/pc0101_mobile_ios.pak"),
            (pak_source / "pc0101_mobile_ios.utoc", "Documents/pak/pc0101_mobile_ios.utoc"),
            (pak_source / "pc0101_mobile_ios.ucas", "Documents/pak/pc0101_mobile_ios.ucas"),
            (pak_source / "global_mobile_ios.utoc", "Documents/pak/global_mobile_ios.utoc"),
            (pak_source / "global_mobile_ios.ucas", "Documents/pak/global_mobile_ios.ucas"),
            (WORKSPACE_ROOT / "ziru-extra/pak_extra/pc7999_mobile_ios.pak", "Documents/pak/pc7999_mobile_ios.pak"),
            (WORKSPACE_ROOT / "ziru-extra/pak_extra/pc7999_mobile_ios.utoc", "Documents/pak/pc7999_mobile_ios.utoc"),
            (WORKSPACE_ROOT / "ziru-extra/pak_extra/pc7999_mobile_ios.ucas", "Documents/pak/pc7999_mobile_ios.ucas"),
            (WORKSPACE_ROOT / "ziru-extra/pak_extra/pc8000_mobile_ios.pak", "Documents/pak/pc8000_mobile_ios.pak"),
            (WORKSPACE_ROOT / "ziru-extra/pak_extra/pc8000_mobile_ios.utoc", "Documents/pak/pc8000_mobile_ios.utoc"),
            (WORKSPACE_ROOT / "ziru-extra/pak_extra/pc8000_mobile_ios.ucas", "Documents/pak/pc8000_mobile_ios.ucas"),
        ]
        for lp, rp in pak_files_to_push:
            if not lp.exists():
                continue
            if await service.exists(rp):
                st = await service.stat(rp)
                if st.get("st_size") == lp.stat().st_size:
                    print(f"[SKIP] {lp.name} already exists on device with matching size ({lp.stat().st_size} bytes).")
                    continue
                else:
                    try:
                        await service.rm(rp)
                    except Exception:
                        pass
            await push_file_safe(service, lp, rp)

        print("\n=======================================================")
        print("  DEVICES SYNC COMPLETED SUCCESSFULLY!  ")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(main())
