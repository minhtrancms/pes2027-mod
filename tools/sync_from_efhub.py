#!/usr/bin/env python3
"""Sync player stats and official card images directly from eFHUB (efhub.com / efimg.com).
"""
import base64
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESPONSES_DIR = REPO_ROOT / "ziru-extra" / "responses"
RECORDS_FILE = RESPONSES_DIR / "ZIRU_PLAYER_RECORDS.json"
THUMBNAILS_DIR = REPO_ROOT / "tools" / "card_editor" / "web" / "thumbnails"
DB_PATH = REPO_ROOT / "ziru_save.db"
CMD_LOGIN_FILE = RESPONSES_DIR / "CmdLogin.json"

STAT_MAP = {
    "offensiveAwareness": 14,
    "ballControl": 15,
    "dribbling": 16,
    "tightPossession": 17,
    "lowPass": 18,
    "loftedPass": 19,
    "finishing": 20,
    "heading": 21,
    "setPieceTaking": 22,
    "curl": 23,
    "speed": 24,
    "acceleration": 25,
    "kickingPower": 26,
    "jump": 27,
    "physicalContact": 28,
    "balance": 29,
    "stamina": 30,
    "defensiveAwareness": 31,
    "ballWinning": 32,
    "aggression": 33,
    "defensiveEngagement": 34,
    "gkAwareness": 35,
    "gkCatching": 36,
    "gkClearing": 37,
    "gkReflexes": 38,
    "gkReach": 39
}

def fetch_efhub_player(pid: int):
    """Fetch official stats and card image URL from eFHUB."""
    url = f"https://efhub.com/id/players/{pid}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    stats = {}
    name = None
    position = "CF"
    card_image_url = f"https://efimg.com/efootballhub22/images/player_cards/{pid}_l.png"
    
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            html = res.read().decode("utf-8")
        
        m_title = re.search(r'<title>([^<\|]+)', html)
        if m_title:
            clean_t = m_title.group(1).split("—")[0].split("-")[0].strip()
            if clean_t and "eFootball" not in clean_t and "eFHUB" not in clean_t:
                name = clean_t

        chunks = re.findall(r'self\.__next_f\.push\(\[1,\"(.*?)\"\]\)', html)
        for c in chunks:
            raw = c.encode().decode("unicode_escape")
            # Look for stats json
            m_stats = re.search(r'\{[^{}]*\"offensiveAwareness\":[0-9]+[^{}]*\}', raw)
            if m_stats:
                try:
                    stats = json.loads(m_stats.group(0))
                except Exception:
                    pass
            # Look for position
            m_pos = re.search(r'\"position\":\"([A-Z]{2,3})\"', raw)
            if m_pos:
                position = m_pos.group(1)
    except Exception as e:
        print(f"  [WARN] Failed to load efhub.com page for ID {pid}: {e}")

    # Fallback name from konami_all_players.json if needed
    if not name:
        k_file = REPO_ROOT / "tools" / "card_editor" / "konami_all_players.json"
        if k_file.exists():
            try:
                with open(k_file, "r", encoding="utf-8") as f:
                    k_list = json.load(f)
                for item in k_list:
                    if item.get("id") == pid:
                        name = item.get("name")
                        break
            except Exception:
                pass
    if not name:
        name = f"Player {pid}"

    # Verify and download card image
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    img_dest = THUMBNAILS_DIR / f"{pid}.png"
    has_image = False
    
    try:
        img_req = urllib.request.Request(card_image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(img_req, timeout=6) as img_res:
            img_data = img_res.read()
            if len(img_data) > 1000:
                with open(img_dest, "wb") as f:
                    f.write(img_data)
                has_image = True
    except Exception as e:
        print(f"  [INFO] Card image not found at default URL for {pid}: {e}")

    return {
        "id": pid,
        "name": name,
        "position": position,
        "stats": stats,
        "has_image": has_image,
        "image_file": str(img_dest) if has_image else None
    }

def sync_player_to_game(pid: int, buff_showtime: bool = True, booster_id: int = 1):
    """Sync an eFHUB player into ZIRU_PLAYER_RECORDS.json, CmdLogin.json, and ziru_save.db."""
    print(f"\n[SYNC] Fetching Player ID {pid} from eFHUB...")
    info = fetch_efhub_player(pid)
    name = info["name"]
    stats = info["stats"]
    print(f"  -> Found: {name} (Position: {info['position']})")
    if stats:
        print(f"  -> Extracted {len(stats)} official attributes from eFHUB!")
    if info["has_image"]:
        print(f"  -> Downloaded official card image to thumbnails/{pid}.png")

    # Load existing records
    records = {}
    if RECORDS_FILE.exists():
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)

    existing = records.get(str(pid), {})
    gp = existing.get("gameplayer", {})
    params = gp.get("parameters", [0] * 147)
    while len(params) < 147:
        params.append(0)

    # Set position
    pos_id_map = {"GK": 1, "CB": 2, "LB": 3, "RB": 4, "DMF": 5, "CMF": 6, "LMF": 7, "RMF": 8, "AMF": 9, "LWF": 10, "RWF": 11, "SS": 12, "CF": 13}
    pos_id = pos_id_map.get(info["position"], params[0] or 13)
    params[0] = pos_id
    for i in range(1, 14):
        params[i] = 2 if i == pos_id else 0

    # Fill official stats
    for stat_key, p_idx in STAT_MAP.items():
        if stat_key in stats:
            params[p_idx] = int(stats[stat_key])
        elif params[p_idx] < 40:
            params[p_idx] = 75

    # Optional ShowTime buff
    add_skills = [22, 21, 10, 45, 72] if buff_showtime else []
    if buff_showtime:
        for idx in [70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 140, 141, 142, 143]:
            if idx < len(params):
                params[idx] = 1

    booster_list = [booster_id, 136 if booster_id > 0 else 0, 0]
    if len(params) >= 145:
        params[142] = booster_id
        params[143] = 136 if booster_id > 0 else 0
        params[144] = 0

    serial = 359042717000000000 + pid
    updated_record = {
        "name": name,
        "gameplayer": {
            "gameplayer_id": {"id": pid, "serial": serial},
            "games": 0,
            "goal": 0,
            "assist": 0,
            "red_card": 0,
            "sell_gp": 100000,
            "sell_item_list": [{"item": {"item_type": "LEVEL_TRAINING", "grade": 4, "effect": 10000}, "present_num": 1}],
            "uniform_number": 10 if pos_id in [9, 10, 12, 13] else 7,
            "level_info": {"level": 1, "level_limit": 1, "exp_total": 0, "exp_current_level": 0, "exp_to_next_level": 0, "customize_point": 0},
            "is_lock": "YES",
            "play_style": [1, 1],
            "initial_base_team_id": 0,
            "initial_base_national_team_id": 0,
            "parameters": params,
            "original_parameters": params,
            "default_rarity": 5,
            "type": "SHOWTIME" if buff_showtime else "EPIC",
            "acquisition_date": int(time.time()),
            "initial_booster_id_list": booster_list,
            "additional_skill_id": add_skills
        }
    }

    # 1. Update ZIRU_PLAYER_RECORDS.json
    records[str(pid)] = updated_record
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print("  -> Saved to ZIRU_PLAYER_RECORDS.json")

    # 2. Update CmdLogin.json
    if CMD_LOGIN_FILE.exists():
        with open(CMD_LOGIN_FILE, "r", encoding="utf-8") as f:
            cl = json.load(f)
        gp_list = cl.get("entry_info", {}).get("gameplayer_list", [])
        found = False
        for item in gp_list:
            if item.get("gameplayer_id", {}).get("id") == pid:
                item.update(updated_record["gameplayer"])
                found = True
                break
        if not found:
            gp_list.append(updated_record["gameplayer"])
        with open(CMD_LOGIN_FILE, "w", encoding="utf-8") as f:
            json.dump(cl, f, ensure_ascii=False)
        print("  -> Synced into CmdLogin.json (My Team owned squad)")

    # 3. Update SQLite ziru_save.db
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO players (serial, player_id, player_json, updated_at) VALUES (?, ?, ?, ?)",
                  (serial, pid, json.dumps(updated_record["gameplayer"]), int(time.time() * 1000)))
        conn.commit()
        conn.close()
        print("  -> Inserted into ziru_save.db (players table)")

    print(f"[HOAN TAT] Da dong bo thanh cong {name} (ID: {pid}) vao game!")
    return updated_record

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/sync_from_efhub.py <player_id_1> [player_id_2] ...")
        print("Example: python3 tools/sync_from_efhub.py 162114 133543 132933")
        sys.exit(0)

    for arg in sys.argv[1:]:
        try:
            pid = int(arg)
            sync_player_to_game(pid)
        except Exception as e:
            print(f"Error syncing {arg}: {e}")
