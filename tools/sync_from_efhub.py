#!/usr/bin/env python3
"""Sync authentic player stats, skills, positions, and card art directly from eFHUB (efhub.com / efimg.com).
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

POS_NAME_MAP = {
    "GK": 1,
    "CB": 2,
    "LB": 3,
    "RB": 4,
    "DMF": 5,
    "CMF": 6,
    "LMF": 7,
    "RMF": 8,
    "AMF": 9,
    "LWF": 10,
    "RWF": 11,
    "SS": 12,
    "CF": 13
}

PLAYING_STYLE_NAME_MAP = {
    "None": 0,
    "Classic No. 10": 9,
    "Goal Poacher": 1,
    "Dummy Runner": 2,
    "Fox in the Box": 3,
    "Target Man": 4,
    "Creative Playmaker": 5,
    "Prolific Winger": 6,
    "Roaming Flank": 7,
    "Cross Specialist": 8,
    "Hole Player": 10,
    "Box-to-Box": 11,
    "Anchor Man": 12,
    "The Destroyer": 13,
    "Orchestrator": 14,
    "Build Up": 15,
    "Extra Frontman": 16,
    "Offensive Full-back": 17,
    "Full-back Finisher": 18,
    "Defensive Full-back": 19,
    "Offensive Goalkeeper": 20,
    "Defensive Goalkeeper": 21,
    "Deep-Lying Forward": 22
}

EFHUB_SKILL_TO_PARAM = {
    "scissorsFeint": 70,
    "doubleTouch": 71,
    "flipFlap": 72,
    "marseilleTurn": 73,
    "sombrero": 74,
    "crossOverTurn": 75,
    "stepOnSkillControl": 75,
    "soleControl": 75,
    "cutBehindTurn": 76,
    "cutBehindAndTurn": 76,
    "scotchMove": 77,
    "heading": 78,
    "longRangeDrive": 79,
    "longRangeShooting": 79,
    "chipShotControl": 80,
    "longRangeCurler": 81,
    "knuckleShot": 82,
    "dippingShot": 83,
    "risingShot": 84,
    "acrobaticFinishing": 85,
    "heelTrick": 86,
    "firstTimeShot": 87,
    "oneTouchPass": 88,
    "throughPassing": 89,
    "weightedPass": 90,
    "pinpointCrossing": 91,
    "outsideCurler": 92,
    "noLookPass": 93,
    "lowLoftedPass": 94,
    "interception": 95,
    "manMarking": 96,
    "blocker": 97,
    "acrobaticClear": 98,
    "slidingTackle": 98,
    "captaincy": 99,
    "superSub": 100,
    "fightingSpirit": 101,
    "gkLowPunt": 107,
    "gkHighPunt": 108,
    "gkPenaltySaver": 109,
    "fortress": 102,
    "momentumDribbling": 103,
    "phenomenalFinishing": 104,
    "visionaryPass": 105,
    "edgeCrossing": 140,
    "gameChangingPass": 141,
    "blitzCurler": 143,
}

PARAM_TO_SKILL_ID = {
    104: 22, 103: 21, 102: 10, 105: 45, 143: 72, 140: 14, 141: 42,
    70: 0, 71: 2, 72: 3, 73: 4, 74: 6, 75: 7, 76: 15, 77: 17, 78: 20,
    79: 26, 80: 27, 81: 28, 82: 31, 83: 33, 84: 34, 85: 36, 86: 37,
    87: 43, 88: 44, 89: 46, 90: 47, 91: 54, 92: 55, 93: 56, 94: 64,
    95: 67, 96: 69, 97: 70, 98: 38, 99: 48, 100: 49, 101: 19
}

def get_defensive_play_style(pos, st1):
    if pos == 1 or (16 <= st1 <= 17): return 33
    if pos == 2: return 30
    if pos in (3, 4): return 28
    if pos in (5, 6): return 25
    if pos in (7, 8): return 27
    if pos == 9: return 23
    if pos in (10, 11): return 23
    if pos in (12, 13): return 26
    if st1 in (1, 2, 3, 13, 22): return 26
    if st1 in (4, 6, 10, 14, 18, 19): return 23
    if st1 in (7, 8, 9, 20): return 25
    if st1 in (11, 12, 15, 21): return 30
    return 27

def fetch_efhub_player(pid: int):
    """Fetch complete authentic stats, skills, positions, and card art from eFHUB."""
    url = f"https://efhub.com/id/players/{pid}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    stats = {}
    skills_list = []
    add_positions = []
    player_data = {}
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
        full_raw = '\n'.join([c.encode().decode('unicode_escape') for c in chunks])

        m_stats = re.search(r'\"baseStats\":(\{.*?\})', full_raw)
        if m_stats:
            try:
                stats = json.loads(m_stats.group(1))
            except Exception:
                pass

        m_skills = re.search(r'\"playerSkills\":(\[.*?\])', full_raw)
        if m_skills:
            try:
                skills_list = json.loads(m_skills.group(1))
            except Exception:
                pass

        m_player = re.search(r'\"player\":(\{\"id\":.*?\"levelCap\":[0-9]+\})', full_raw)
        if m_player:
            try:
                player_data = json.loads(m_player.group(1))
            except Exception:
                pass

        m_add_pos = re.search(r'\"additionalPositions\":(\[.*?\])', full_raw)
        if m_add_pos:
            try:
                add_positions = json.loads(m_add_pos.group(1))
            except Exception:
                pass

        if player_data.get("name"):
            name = player_data["name"]
        if player_data.get("position"):
            position = player_data["position"]

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
        "skills": skills_list,
        "additional_positions": add_positions,
        "player_data": player_data,
        "has_image": has_image,
        "image_file": str(img_dest) if has_image else None
    }

def sync_player_to_game(pid: int):
    """Sync authentic eFHUB player data into ZIRU_PLAYER_RECORDS.json, CmdLogin.json, and ziru_save.db."""
    print(f"\n[SYNC] Fetching Player ID {pid} from eFHUB...")
    info = fetch_efhub_player(pid)
    name = info["name"]
    stats = info["stats"]
    skills = info["skills"]
    pd = info.get("player_data", {})
    pos_name = info["position"]
    pos_id = POS_NAME_MAP.get(pos_name, 13)

    print(f"  -> Found: {name} (Position: {pos_name}, PlayingStyle: {pd.get('playingStyle', 'None')})")
    print(f"  -> Extracted {len(stats)} official base attributes!")
    print(f"  -> Extracted {len(skills)} authentic skills: {skills}")
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

    # 1. Primary Position & Familiarity
    params[0] = pos_id
    for i in range(1, 14):
        params[i] = 2 if i == pos_id else 0

    for ap in info.get("additional_positions", []):
        ap_id = POS_NAME_MAP.get(ap.get("position"))
        if ap_id and 1 <= ap_id <= 13:
            params[ap_id] = int(ap.get("familiarity", 1))

    # 2. Fill official 26 Base Stats exactly
    for stat_key, p_idx in STAT_MAP.items():
        if stat_key in stats:
            params[p_idx] = int(stats[stat_key])
        elif params[p_idx] < 40:
            params[p_idx] = 75

    # 3. Authentic Skills (Reset all skills first, then activate ONLY authentic ones)
    for s_idx in range(70, 121):
        params[s_idx] = 0
    for s_idx in [140, 141, 142, 143]:
        params[s_idx] = 0

    active_param_skills = []
    additional_skill_ids = []
    for s_name in skills:
        if s_name in EFHUB_SKILL_TO_PARAM:
            p_idx = EFHUB_SKILL_TO_PARAM[s_name]
            params[p_idx] = 1
            active_param_skills.append(p_idx)
            if p_idx in PARAM_TO_SKILL_ID:
                additional_skill_ids.append(PARAM_TO_SKILL_ID[p_idx])

    # 4. Physical attributes & Foot
    pref_foot = pd.get("preferredFoot", "Right")
    params[45] = 1 if pref_foot == "Right" else 2
    params[46] = int(pd.get("age", 25))
    params[47] = int(pd.get("height", 180))
    params[48] = int(pd.get("weight", 75))

    # 5. Play Style
    ps_name = pd.get("playingStyle", "None")
    play_style_id = PLAYING_STYLE_NAME_MAP.get(ps_name, 1)
    def_style_id = get_defensive_play_style(pos_id, play_style_id)

    # 6. Booster & Card Type
    booster_id = int(pd.get("boostId", 0))
    has_showtime = any(p in active_param_skills for p in [102, 103, 104, 105, 140, 141, 143])
    if has_showtime:
        card_type = "SHOWTIME"
    elif booster_id > 0:
        card_type = "EPIC"
    else:
        card_type = "HIGHLIGHT" if int(pd.get("overallRating", 80)) >= 85 else "NORMAL"

    booster_list = [booster_id, 136 if booster_id > 0 else 0, 0]
    if len(params) >= 145:
        params[142] = booster_id
        params[143] = 136 if booster_id > 0 else 0
        params[144] = 0

    uniform_num = 10 if pos_id in [9, 10, 11, 12, 13] else 7

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
            "uniform_number": uniform_num,
            "level_info": {"level": 1, "level_limit": int(pd.get("levelCap", 30)), "exp_total": 0, "exp_current_level": 0, "exp_to_next_level": 0, "customize_point": 0},
            "is_lock": "YES",
            "play_style": [play_style_id, def_style_id],
            "initial_base_team_id": int(pd.get("teamId", 0) or 0),
            "initial_base_national_team_id": int(pd.get("countryId", 0) or 0),
            "parameters": params,
            "original_parameters": params,
            "default_rarity": 5,
            "type": card_type,
            "acquisition_date": int(time.time()),
            "initial_booster_id_list": booster_list,
            "additional_skill_id": additional_skill_ids
        }
    }

    # 1. Update ZIRU_PLAYER_RECORDS.json
    records[str(pid)] = updated_record
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print("  -> Saved authentic stats and skills to ZIRU_PLAYER_RECORDS.json")

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

    print(f"[HOAN TAT] Da dong bo chuan xac {name} (ID: {pid}) tu eFHUB vao game!")
    return updated_record

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/sync_from_efhub.py <player_id_1> [player_id_2] ...")
        print("Example: python3 tools/sync_from_efhub.py 89133993205152 162114 133543")
        sys.exit(0)

    for arg in sys.argv[1:]:
        try:
            m = re.search(r'players/(\d+)', arg)
            pid = int(m.group(1)) if m else int(re.findall(r'\d+', arg)[-1])
            sync_player_to_game(pid)
        except Exception as e:
            print(f"Error syncing {arg}: {e}")
