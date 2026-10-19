#!/usr/bin/env python3
"""Integrate Zidane, Ronaldo Nazario, and Mesut Ozil mod resources into pes2027-mod.
"""
import copy
import hashlib
import json
import os
import shutil
import struct
import sys
import zipfile
import zlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from tools.repair_ios_tables import utf_table, unpack_wesys

ZIDANE_MOD_CPK = os.path.join(REPO_ROOT, "build", "zidane_mod", "files", "embedded-gateway", "custom-resources", "legends-v10", "dt870_mobile_and.cpk")
ZIDANE_MOD_DIR = os.path.dirname(ZIDANE_MOD_CPK)
APK_PATH = os.path.join(REPO_ROOT, "build", "ziru_assets.apk")
PAK_EXTRA_DIR = os.path.join(REPO_ROOT, "ziru-extra", "pak_extra")
DATA_DIR = os.path.join(REPO_ROOT, "PES2027-data")

# Legends definitions
ZIDANE_PARAMS = [8, 2, 2, 2, 2, 2, 0, 0, 1, 1, 0, 0, 0, 0, 86, 55, 40, 90, 92, 94, 84, 93, 91, 75, 55, 63, 60, 88, 87, 40, 40, 40, 40, 1, 77, 83, 88, 87, 78, 76, 84, 2, 1, 0, 0, 1, 29, 185, 80, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
R9_PARAMS = [12, 2, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 94, 45, 40, 94, 90, 91, 95, 80, 72, 81, 43, 65, 46, 76, 83, 40, 40, 40, 40, 2, 95, 84, 91, 92, 96, 77, 85, 1, 2, 0, 0, 1, 21, 183, 82, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
OZIL_PARAMS = [8, 2, 2, 2, 2, 2, 0, 0, 1, 1, 0, 0, 0, 0, 82, 50, 40, 89, 94, 96, 84, 96, 94, 78, 52, 60, 58, 88, 86, 40, 40, 40, 40, 1, 76, 83, 86, 85, 78, 76, 84, 2, 1, 0, 0, 1, 28, 180, 76, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

ZIDANE_SELL_ITEMS = [{"item": {"item_type": "LEVEL_TRAINING", "grade": 4, "effect": 10000}, "present_num": 1}]

def build_player_record(pid, serial, uniform, play_style, nation, params, name=""):
    return {
        "gameplayer_id": {"id": pid, "serial": serial},
        "games": 0,
        "goal": 0,
        "assist": 0,
        "red_card": 0,
        "sell_gp": 100000,
        "sell_item_list": ZIDANE_SELL_ITEMS,
        "uniform_number": uniform,
        "level_info": {
            "level": 1,
            "level_limit": 1,
            "exp_total": 0,
            "exp_current_level": 0,
            "exp_to_next_level": 0,
            "customize_point": 0
        },
        "is_lock": "YES",
        "play_style": play_style,
        "initial_base_team_id": 0,
        "initial_base_national_team_id": nation,
        "parameters": copy.deepcopy(params),
        "original_parameters": copy.deepcopy(params),
        "default_rarity": 5,
        "type": "NORMAL",
        "acquisition_date": 1792410000,
        "initial_booster_id_list": [0, 0, 0]
    }

def update_dt870():
    print(f"Reading base CPK from {ZIDANE_MOD_CPK} ...")
    with open(ZIDANE_MOD_CPK, "rb") as f:
        data = bytearray(f.read())

    header = utf_table(data[16:0x800])[0]
    toc = header["TocOffset"]
    length = struct.unpack_from("<Q", data, toc + 8)[0]
    rows = utf_table(data[toc + 16:toc + 16 + length])

    # 1. Update Player.bin
    player_row = [r for r in rows if r.get("FileName") == "Player.bin"][0]
    offset = min(toc, header["ContentOffset"]) + player_row["FileOffset"]
    size = player_row["FileSize"]
    raw_player = bytearray(unpack_wesys(data[offset:offset+size]))
    print(f"Player.bin: {len(raw_player)} bytes ({len(raw_player)//400} records)")

    # Verify Zidane and Ronaldo exist
    z_pos = raw_player.find(struct.pack("<I", 9901397))
    r_pos = raw_player.find(struct.pack("<I", 37576))
    print(f"Zidane found at offset {z_pos}, Ronaldo found at offset {r_pos}")
    assert z_pos != -1 and r_pos != -1

    # Check if Ozil already exists
    o_pos = raw_player.find(struct.pack("<I", 40291))
    if o_pos == -1:
        print("Injecting Mesut Ozil (ID 40291) into Player.bin ...")
        z_rec = bytes(raw_player[10957600:10957600+400])
        ozil_rec = bytearray(z_rec)
        struct.pack_into("<I", ozil_rec, 8, 40291)
        ozil_rec[88:400] = b"\x00" * (400 - 88)

        def write_str(buf, off, text):
            tb = text.encode("utf-8")
            buf[off:off+len(tb)] = tb

        write_str(ozil_rec, 88, "メスト エジル")
        write_str(ozil_rec, 149, "M. ÖZIL")
        write_str(ozil_rec, 210, "厄齐尔")
        write_str(ozil_rec, 271, "M. ÖZIL")
        write_str(ozil_rec, 332, "Mesut Özil")
        raw_player.extend(ozil_rec)

    comp = zlib.compress(raw_player, 9)
    packed = b"\x00\x01\x01WESYS" + struct.pack("<II", len(comp), len(raw_player)) + comp
    assert len(packed) <= size, f"Player.bin overflow: {len(packed)} > {size}"
    data[offset:offset+size] = packed.ljust(size, b"\x00")
    print(f"Player.bin repacked: {len(packed)} bytes (free space: {size - len(packed)})")

    # 2. Update PlayerAppearance.bin
    app_row = [r for r in rows if r.get("FileName") == "PlayerAppearance.bin"][0]
    a_offset = min(toc, header["ContentOffset"]) + app_row["FileOffset"]
    a_size = app_row["FileSize"]
    raw_app = bytearray(unpack_wesys(data[a_offset:a_offset+a_size]))
    print(f"PlayerAppearance.bin: {len(raw_app)} bytes ({len(raw_app)//64} records)")

    ao_pos = raw_app.find(struct.pack("<I", 40291))
    if ao_pos == -1:
        print("Injecting Mesut Ozil appearance (ID 40291) ...")
        z_app = raw_app[1753216:1753216+64]
        ozil_app = bytearray(z_app)
        struct.pack_into("<I", ozil_app, 0, 40291)
        raw_app.extend(ozil_app)

    a_comp = zlib.compress(raw_app, 9)
    a_packed = b"\x00\x01\x01WESYS" + struct.pack("<II", len(a_comp), len(raw_app)) + a_comp
    assert len(a_packed) <= a_size, f"PlayerAppearance.bin overflow: {len(a_packed)} > {a_size}"
    data[a_offset:a_offset+a_size] = a_packed.ljust(a_size, b"\x00")
    print(f"PlayerAppearance.bin repacked: {len(a_packed)} bytes (free space: {a_size - len(a_packed)})")

    out_cpk = os.path.join(REPO_ROOT, "build", "dt870_mobile_and.cpk")
    with open(out_cpk, "wb") as f:
        f.write(data)
    print(f"Wrote updated CPK to {out_cpk} ({len(data)} bytes)")
    return out_cpk

def update_apk_and_data(out_cpk):
    print(f"Updating {APK_PATH} ...")
    tmp_apk = APK_PATH + ".tmp"

    p_zidane = build_player_record(9901397, 359042717000000990, 10, [6, 0], 208, ZIDANE_PARAMS, "Zidane")
    p_r9 = build_player_record(37576, 359042717000000991, 9, [3, 0], 146, R9_PARAMS, "Ronaldo")
    p_ozil = build_player_record(40291, 359042717000000992, 10, [6, 0], 11, OZIL_PARAMS, "Ozil")

    with zipfile.ZipFile(APK_PATH, "r") as zin, zipfile.ZipFile(tmp_apk, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            fn = item.filename
            if fn == "assets/livedata/dt870_mobile_and.cpk":
                print("Replacing assets/livedata/dt870_mobile_and.cpk in APK ...")
                zout.write(out_cpk, fn)
            elif fn in ("assets/responses/ZIRU_PLAYER_RECORDS.json", "assets/responses/ZIRU_PLAYER_RECORDS_DEFAULT.json"):
                print(f"Updating {fn} with Zidane, Ronaldo, Ozil ...")
                recs = json.loads(zin.read(fn))
                recs["9901397"] = {"gameplayer": p_zidane}
                recs["37576"] = {"gameplayer": p_r9}
                recs["40291"] = {"gameplayer": p_ozil}
                zout.writestr(fn, json.dumps(recs, ensure_ascii=False, indent=2))
            elif fn in ("assets/responses/CmdLogin.json", "assets/responses/CmdGetMyclubEntryInfo.json"):
                print(f"Adding Zidane, Ronaldo, Ozil to owned squad in {fn} ...")
                data = json.loads(zin.read(fn))
                gpl = data.get("entry_info", {}).get("gameplayer_list", [])
                # Remove any existing instances with same IDs
                gpl = [p for p in gpl if p.get("gameplayer_id", {}).get("id") not in (9901397, 37576, 40291)]
                # Insert at top of squad
                gpl.insert(0, p_ozil)
                gpl.insert(0, p_r9)
                gpl.insert(0, p_zidane)
                data["entry_info"]["gameplayer_list"] = gpl
                data["entry_info"]["total_get_player_num"] = len(gpl)
                zout.writestr(fn, json.dumps(data, ensure_ascii=False, indent=2))
            elif fn == "assets/responses/ZIRU_PACKS_CONFIG.json":
                print("Configuring POTW and Legends in ZIRU_PACKS_CONFIG.json ...")
                cfg = json.loads(zin.read(fn))
                potw_titles = {
                    1374: "POTW: EUROPEAN CLUB CHAMPIONSHIPS",
                    6201: "POTW: WORLDWIDE",
                    6202: "POTW: ELITE FINISHERS",
                    6203: "POTW: DEFENSIVE WALL",
                    6204: "POTW: RISING STARS",
                }
                for pack in cfg.get("packs", []):
                    aid = pack.get("agent_id")
                    if aid in potw_titles:
                        pack["title"] = potw_titles[aid]
                        pack["category"] = "potw"
                    elif pack.get("category") == "epic" or "epic" in pack.get("pack_id", ""):
                        pids = pack.get("player_ids", [])
                        for pid in (9901397, 37576, 40291):
                            if pid not in pids:
                                pids.insert(0, pid)
                        pack["player_ids"] = pids
                zout.writestr(fn, json.dumps(cfg, ensure_ascii=False, indent=2))
                # Also save to ziru-extra/responses/
                extra_packs_path = os.path.join(REPO_ROOT, "ziru-extra", "responses", "ZIRU_PACKS_CONFIG.json")
                with open(extra_packs_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            elif fn == "assets/responses/CmdGetMyclubAgentlist.json":
                print("Configuring POTW boxes in CmdGetMyclubAgentlist.json ...")
                al = json.loads(zin.read(fn))
                potw_agent_map = {
                    1374: ("POTW: EUROPEAN CLUB CHAMPIONSHIPS", "/banner/agent/001358/357a37bfd61acdd735dc84f19e43c1eb76813080b3487c01665411ac1ff5f430", "/banner/agent/001358/968514e0f6c5aa3b86282d9bf526993656980e6c55f74e3a38df8eb5dbbb258c"),
                    6201: ("POTW: WORLDWIDE", "/banner/agent/001396/42d232530744a547f5d654c5880f79d5367f3693bd2422d693d7c5cd0c8d5afd", "/banner/agent/001396/558e9931438395e08b9c187dd586e81d3619df062c8f9c7d110a172db55324e6"),
                    6202: ("POTW: ELITE FINISHERS", "/banner/agent/001397/308aa700b860dc6e275bf3343bd7a2c34ef9842b09d3b4280676ccb4f62f625d", "/banner/agent/001397/638c7ea4f1ed97bbb184a2e4588c4a6204ca4cb7663659eb166bec2962395e10"),
                    6203: ("POTW: DEFENSIVE WALL", "/banner/agent/001358/357a37bfd61acdd735dc84f19e43c1eb76813080b3487c01665411ac1ff5f430", "/banner/agent/001358/968514e0f6c5aa3b86282d9bf526993656980e6c55f74e3a38df8eb5dbbb258c"),
                    6204: ("POTW: RISING STARS", "/banner/agent/001396/42d232530744a547f5d654c5880f79d5367f3693bd2422d693d7c5cd0c8d5afd", "/banner/agent/001396/558e9931438395e08b9c187dd586e81d3619df062c8f9c7d110a172db55324e6"),
                }
                for ag in al.get("agent_list", []):
                    aid = ag.get("agent_id")
                    if aid in potw_agent_map:
                        title, bnc, bnd = potw_agent_map[aid]
                        ag["title"] = title
                        ag["subcategory"] = "POTW"
                        ag["description"] = "Cầu thủ xuất sắc nhất tuần (POTW) với chỉ số và phong độ vượt trội!"
                        ag["banner_file_c_name"] = bnc
                        ag["banner_file_d_name"] = bnd
                zout.writestr(fn, json.dumps(al, ensure_ascii=False, indent=2))
                # Also save to ziru-extra/responses/
                extra_agent_path = os.path.join(REPO_ROOT, "ziru-extra", "responses", "CmdGetMyclubAgentlist.json")
                with open(extra_agent_path, "w", encoding="utf-8") as f:
                    json.dump(al, f, ensure_ascii=False, indent=2)
            else:
                zout.writestr(item, zin.read(fn))

    os.replace(tmp_apk, APK_PATH)
    print("Updated APK successfully!")

    # Also update ziru-extra/responses/CmdLogin.json since ziru-extra overrides APK
    extra_login_path = os.path.join(REPO_ROOT, "ziru-extra", "responses", "CmdLogin.json")
    if os.path.exists(extra_login_path):
        with open(extra_login_path, "r", encoding="utf-8") as f:
            el = json.load(f)
        egpl = el.get("entry_info", {}).get("gameplayer_list", [])
        egpl = [p for p in egpl if p.get("gameplayer_id", {}).get("id") not in (9901397, 37576, 40291)]
        egpl.insert(0, p_ozil)
        egpl.insert(0, p_r9)
        egpl.insert(0, p_zidane)
        el["entry_info"]["gameplayer_list"] = egpl
        el["entry_info"]["total_get_player_num"] = len(egpl)
        with open(extra_login_path, "w", encoding="utf-8") as f:
            json.dump(el, f, ensure_ascii=False, indent=2)
        print(f"Updated {extra_login_path} with {len(egpl)} players")

    # Copy real face pak into ziru-extra/pak_extra/
    os.makedirs(PAK_EXTRA_DIR, exist_ok=True)
    for ext in ("pak", "utoc", "ucas"):
        src = os.path.join(ZIDANE_MOD_DIR, f"pc3700_mobile_and.{ext}")
        if os.path.exists(src):
            # Write both _mobile_ios and _mobile_and versions
            dst_ios = os.path.join(PAK_EXTRA_DIR, f"pc3700_mobile_ios.{ext}")
            dst_and = os.path.join(PAK_EXTRA_DIR, f"pc3700_mobile_and.{ext}")
            print(f"Copying {src} -> {dst_ios} and {dst_and} ...")
            shutil.copy2(src, dst_ios)
            shutil.copy2(src, dst_and)

            # Also update PES2027-data/pak/
            data_pak_dst = os.path.join(DATA_DIR, "pak", f"pc3700_mobile_ios.{ext}")
            print(f"Updating data pack: {data_pak_dst} ...")
            shutil.copy2(src, data_pak_dst)

    # Update PES2027-data/livedata/dt870_mobile_and.cpk
    data_cpk_dst = os.path.join(DATA_DIR, "livedata", "dt870_mobile_and.cpk")
    shutil.copy2(out_cpk, data_cpk_dst)
    print(f"Updated {data_cpk_dst}")

def main():
    out_cpk = update_dt870()
    update_apk_and_data(out_cpk)
    print("\nALL MOD INTEGRATION COMPLETE!")

if __name__ == "__main__":
    main()
