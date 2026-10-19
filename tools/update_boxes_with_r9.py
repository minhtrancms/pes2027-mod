#!/usr/bin/env python3
"""
Add Ronaldo Nazário R9, Zidane, and Özil directly into the featured Box Agent banners and pickup list.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from pymobiledevice3.lockdown import create_using_usbmux
from pymobiledevice3.services.house_arrest import HouseArrestService

BUNDLE_ID = "jp.konami.pesactionmobile.WXK53U737T"
WORKSPACE_ROOT = Path("/Users/nhatminh/Sites/localhost/MyProject/pes2027-mod")

def update_local_files():
    login_path = WORKSPACE_ROOT / "ziru-extra" / "responses" / "CmdLogin.json"
    agentlist_path = WORKSPACE_ROOT / "ziru-extra" / "responses" / "CmdGetMyclubAgentlist.json"
    packs_path = WORKSPACE_ROOT / "ziru-extra" / "responses" / "ZIRU_PACKS_CONFIG.json"

    with open(login_path, "r", encoding="utf-8") as f:
        login = json.load(f)

    with open(agentlist_path, "r", encoding="utf-8") as f:
        agentlist = json.load(f)

    with open(packs_path, "r", encoding="utf-8") as f:
        packs = json.load(f)

    # 1. Extract clean player templates
    p_objs = {}
    for p in login["entry_info"]["gameplayer_list"]:
        gid = p["gameplayer_id"]["id"]
        if gid in [37576, 9901397, 40291]:
            obj = json.loads(json.dumps(p))
            obj["gameplayer_id"]["serial"] = 0
            p_objs[gid] = obj

    r9_obj = p_objs[37576]
    zidane_obj = p_objs[9901397]
    ozil_obj = p_objs[40291]

    # 2. Update Box 1 (agent 1368) in CmdGetMyclubAgentlist.json
    for a in agentlist["agent_list"]:
        if a.get("agent_id") == 1368:
            a["title"] = "ZIRU LEGENDS: RONALDO R9 & ZIDANE"
            a["description"] = "EPIC RONALDO NAZÁRIO R9 (99), ZIDANE (100) & ÖZIL (98)"
            a["pickup_cardtype_list"] = [
                {"id": 37576, "serial": 0},
                {"id": 9901397, "serial": 0},
                {"id": 40291, "serial": 0}
            ]
            a["banner_a_pickup_list"] = [r9_obj, zidane_obj, ozil_obj]
            a["banner_c_pickup_list"] = [r9_obj, zidane_obj, ozil_obj]
            print("[OK] Updated Box 1 (1368) featured pickups: R9 (37576), Zidane (9901397), Ozil (40291)")

        if a.get("agent_id") == 6002: # ELITE FINISHERS
            a["title"] = "ZIRU LEGENDS: ELITE FINISHERS (R9)"
            a["pickup_cardtype_list"][0] = {"id": 37576, "serial": 0}
            if a.get("banner_a_pickup_list"):
                a["banner_a_pickup_list"][0] = r9_obj
            if a.get("banner_c_pickup_list"):
                a["banner_c_pickup_list"][0] = r9_obj
            print("[OK] Updated Box 3 (6002) featured pickup #1: Ronaldo R9 (37576)")

    with open(agentlist_path, "w", encoding="utf-8") as f:
        json.dump(agentlist, f, indent=2, ensure_ascii=False)

    # 3. Update ZIRU_PACKS_CONFIG.json so R9 is #1 pull in Box 1 and Box 3
    for p in packs.get("packs", []):
        if p.get("agent_id") == 1368:
            p_ids = [pid for pid in p["player_ids"] if pid not in [37576, 9901397, 40291]]
            p["player_ids"] = [37576, 9901397, 40291] + p_ids
            p["title"] = "ZIRU LEGENDS: RONALDO R9 & ZIDANE"
            print("[OK] ZIRU_PACKS_CONFIG: Box 1 player_ids starts with R9, Zidane, Ozil")

        if p.get("agent_id") == 6002:
            p_ids = [pid for pid in p["player_ids"] if pid != 37576]
            p["player_ids"] = [37576] + p_ids
            print("[OK] ZIRU_PACKS_CONFIG: Box 3 player_ids starts with R9")

    with open(packs_path, "w", encoding="utf-8") as f:
        json.dump(packs, f, indent=2, ensure_ascii=False)

async def deploy_to_device():
    print(f"\nConnecting to device via usbmuxd (Bundle ID: {BUNDLE_ID})...")
    lockdown = await create_using_usbmux()
    print(f"Connected to {lockdown.display_name} ({lockdown.product_type}, iOS {lockdown.product_version})")

    async with await HouseArrestService.create(lockdown, BUNDLE_ID, documents_only=False) as service:
        # Push CmdGetMyclubAgentlist.json
        agentlist_path = WORKSPACE_ROOT / "ziru-extra" / "responses" / "CmdGetMyclubAgentlist.json"
        print("[PUSH] CmdGetMyclubAgentlist.json -> Documents/responses/CmdGetMyclubAgentlist.json")
        await service.push(str(agentlist_path), "Documents/responses/CmdGetMyclubAgentlist.json", progress_bar=False)

        # Push ZIRU_PACKS_CONFIG.json
        packs_path = WORKSPACE_ROOT / "ziru-extra" / "responses" / "ZIRU_PACKS_CONFIG.json"
        print("[PUSH] ZIRU_PACKS_CONFIG.json -> Documents/responses/ZIRU_PACKS_CONFIG.json")
        await service.push(str(packs_path), "Documents/responses/ZIRU_PACKS_CONFIG.json", progress_bar=False)

        # Reset box counts in prefs_almanac_state.json
        pref_remote = "Library/Application Support/PES2027/Save/prefs_almanac_state.json"
        if await service.exists(pref_remote):
            raw = await service.get_file_contents(pref_remote)
            try:
                prefs = json.loads(raw.decode("utf-8"))
                # Remove remaining counts so fresh pack is loaded
                for k in list(prefs.keys()):
                    if k.startswith("ziru_remaining_"):
                        del prefs[k]
                updated_raw = json.dumps(prefs).encode("utf-8")
                await service.set_file_contents(pref_remote, updated_raw)
                print("[OK] Reset pack counters in prefs_almanac_state.json on device!")
            except Exception as e:
                print(f"[WARN] Failed to patch prefs_almanac_state.json: {e}")

        print("\n=======================================================")
        print("  RONALDO R9 & ZIDANE ADDED TO BOX 1 & BOX 3!  ")
        print("=======================================================")

if __name__ == "__main__":
    update_local_files()
    asyncio.run(deploy_to_device())
