#!/usr/bin/env python3
"""
PES2027 Card Mod Tool - Local Web Server & API
Provides full GUI for creating, editing, customizing player cards,
importing custom card art, adding to gacha boxes / active squads,
and 1-click deploying directly to connected iPhone over USB.
"""

import os
import sys
import json
import time
import base64
import sqlite3
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESPONSES_DIR = REPO_ROOT / "ziru-extra" / "responses"
RECORDS_FILE = RESPONSES_DIR / "ZIRU_PLAYER_RECORDS.json"
AGENTLIST_FILE = RESPONSES_DIR / "CmdGetMyclubAgentlist.json"
PACKS_CONFIG_FILE = RESPONSES_DIR / "ZIRU_PACKS_CONFIG.json"
WEB_DIR = Path(__file__).resolve().parent / "web"
THUMBNAIL_DIR = RESPONSES_DIR / "cdn" / "prd" / "banner" / "player"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

# Try importing PIL
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try importing pymobiledevice3
try:
    import asyncio
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.house_arrest import HouseArrestService
    HAS_DEVICE = True
except ImportError:
    HAS_DEVICE = False

BUNDLE_ID = "jp.konami.pesactionmobile.WXK53U737T"

# Position Map
POS_MAP = {
    1: "GK", 2: "CB", 3: "LB", 4: "RB", 5: "DMF",
    6: "CMF", 7: "LMF", 8: "RMF", 9: "AMF",
    10: "LWF", 11: "RWF", 12: "SS", 13: "CF"
}
REV_POS_MAP = {v: k for k, v in POS_MAP.items()}

# Play Style Map
PLAY_STYLE_MAP = {
    0: "None / Classic",
    1: "Goal Poacher",
    2: "Dummy Runner",
    3: "Fox in the Box",
    4: "Target Man",
    5: "Creative Playmaker",
    6: "Prolific Winger",
    7: "Roaming Flank",
    8: "Cross Specialist",
    9: "Classic No. 10",
    10: "Hole Player",
    11: "Box-to-Box",
    12: "Anchor Man",
    13: "The Destroyer",
    14: "Orchestrator",
    15: "Build Up",
    16: "Extra Frontman",
    17: "Offensive Full-back",
    18: "Full-back Finisher",
    19: "Defensive Full-back",
    20: "Offensive Goalkeeper",
    21: "Defensive Goalkeeper",
    22: "Deep-Lying Forward"
}

DEFENSIVE_PLAY_STYLE_MAP = {
    0: "Auto / Default",
    23: "Press Back",
    24: "Counter Target",
    25: "Cover Shadow",
    26: "Outlet Forward",
    27: "Hard Worker",
    28: "Lane Blocker",
    29: "Wide Stopper",
    30: "Line Controller",
    31: "Zone Anchor",
    32: "Last Line",
    33: "Sweeper GK"
}

def get_defensive_play_style(pos, st1):
    if pos == 0 or (16 <= st1 <= 17): return 33
    if pos == 1: return 30
    if pos in (2, 3): return 28
    if pos in (4, 5): return 25
    if pos in (6, 7): return 27
    if pos == 8: return 23
    if pos in (9, 10): return 23
    if pos in (11, 12): return 26
    if st1 in (1, 2, 3, 13, 22): return 26
    if st1 in (4, 6, 10, 14, 18, 19): return 23
    if st1 in (7, 8, 9, 20): return 25
    if st1 in (11, 12, 15, 21): return 30
    return 27

# Skill definitions (index in parameters[70..100])
SKILLS_LIST = [
    (70, "Scissors Feint"),
    (71, "Double Touch"),
    (72, "Flip Flap"),
    (73, "Marseille Turn"),
    (74, "Sombrero"),
    (75, "Cross Over Turn"),
    (76, "Cut Behind & Turn"),
    (77, "Scotch Move"),
    (78, "Heading"),
    (79, "Long Range Shooting"),
    (80, "Chip Shot Control"),
    (81, "Long Range Curler"),
    (82, "Knuckle Shot"),
    (83, "Dipping Shot"),
    (84, "Rising Shot"),
    (85, "Acrobatic Finishing"),
    (86, "Heel Trick"),
    (87, "First-time Shot"),
    (88, "One-touch Pass"),
    (89, "Through Passing"),
    (90, "Weighted Pass"),
    (91, "Pinpoint Crossing"),
    (92, "Outside Curler"),
    (93, "No Look Pass"),
    (94, "Low Lofted Pass"),
    (95, "Interception"),
    (96, "Man Marking"),
    (97, "Blocker"),
    (98, "Acrobatic Clear"),
    (99, "Captaincy"),
    (100, "Super-sub"),
    (101, "Fighting Spirit"),
    (102, "Fortress (Show Time)"),
    (103, "Momentum Dribbling (Show Time)"),
    (104, "Phenomenal Finishing (Show Time)"),
    (105, "Visionary Pass (Show Time)")
]

def load_records():
    if not RECORDS_FILE.exists():
        return {}
    try:
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_records(records):
    with open(RECORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def get_player_summary(pid, item):
    gp = item.get("gameplayer", {})
    params = gp.get("parameters", [])
    pos_id = params[0] if len(params) > 0 else 13
    pos_name = POS_MAP.get(pos_id, "CF")
    
    # Calculate simple OVR from key stats
    ovr = 90
    if len(params) >= 30:
        if pos_name == "GK":
            ovr = int((params[15] + params[24] + params[27] + params[28]) / 4)
        elif pos_name in ["CB", "LB", "RB", "DMF"]:
            ovr = int((params[14] + params[20] + params[24] + params[27] + params[28]) / 5)
        else:
            ovr = int((params[14] + params[15] + params[16] + params[20] + params[24] + params[25]) / 6)
        ovr = max(60, min(105, ovr + 8))

    name = item.get("name") or gp.get("name") or f"Player {pid}"
    if pid == "37576": name = "RONALDO R9"
    elif pid == "9901397": name = "ZINEDINE ZIDANE"
    elif pid == "40291": name = "MESUT ÖZIL"

    thumb_url = f"/api/player/image?id={pid}"
    return {
        "id": pid,
        "name": name,
        "position": pos_name,
        "uniform_number": gp.get("uniform_number", 9),
        "ovr": ovr,
        "rarity": gp.get("default_rarity", 5),
        "card_type": gp.get("type", "EPIC"),
        "thumbnail": thumb_url
    }

class CardEditorHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.serve_file(WEB_DIR / "index.html", "text/html")
        elif path.startswith("/assets/"):
            rel = path[len("/assets/"):]
            self.serve_file(WEB_DIR / rel)
        elif path == "/api/device/status":
            self.api_device_status()
        elif path == "/api/players":
            self.api_list_players(query)
        elif path == "/api/player":
            self.api_get_player(query.get("id", [None])[0])
        elif path == "/api/player/image":
            self.api_get_player_image(query.get("id", [None])[0])
        elif path == "/api/boxes":
            self.api_list_boxes()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""
        
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        if path == "/api/player/save":
            self.api_save_player(data)
        elif path == "/api/player/upload_image":
            self.api_upload_player_image(data)
        elif path == "/api/boxes/add_player":
            self.api_add_player_to_box(data)
        elif path == "/api/squad/add_starter":
            self.api_add_to_squad(data)
        elif path == "/api/device/sync":
            self.api_sync_device()
        else:
            self.send_response(404)
            self.end_headers()

    def serve_file(self, file_path: Path, mime=None):
        if not file_path.exists():
            self.send_response(404)
            self.end_headers()
            return
        if not mime:
            ext = file_path.suffix.lower()
            mimes = {
                ".html": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".json": "application/json",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".svg": "image/svg+xml"
            }
            mime = mimes.get(ext, "application/octet-stream")
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def json_response(self, obj, status=200):
        res = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(res)))
        self.end_headers()
        self.wfile.write(res)

    def api_device_status(self):
        connected = False
        device_name = "Not Connected"
        if HAS_DEVICE:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                lockdown = loop.run_until_complete(create_using_usbmux())
                connected = True
                device_name = f"{lockdown.display_name} ({lockdown.product_type}, iOS {lockdown.product_version})"
            except Exception:
                connected = False
        self.json_response({
            "connected": connected,
            "device": device_name,
            "bundle_id": BUNDLE_ID
        })

    def api_list_players(self, query):
        records = load_records()
        q = query.get("q", [""])[0].lower()
        items = []
        for pid, val in records.items():
            if not isinstance(val, dict): continue
            item = get_player_summary(pid, val)
            if q and q not in item["name"].lower() and q not in str(pid):
                continue
            items.append(item)
        
        # Sort custom/mod legends first
        pinned = ["37576", "9901397", "40291"]
        items.sort(key=lambda x: (0 if str(x["id"]) in pinned else 1, x["name"]))
        self.json_response({"players": items[:150], "total": len(records)})

    def api_get_player(self, pid):
        if not pid:
            self.json_response({"error": "Missing player ID"}, 400)
            return
        records = load_records()
        record = records.get(str(pid))
        if not record:
            self.json_response({"error": "Player not found"}, 404)
            return

        gp = record.get("gameplayer", {})
        params = gp.get("parameters", [0] * 147)
        while len(params) < 147:
            params.append(0)

        # Parse stats into high-level dict
        stats = {
            "offensive_awareness": params[14],
            "ball_control": params[15],
            "dribbling": params[16],
            "tight_possession": params[17],
            "low_pass": params[18],
            "lofted_pass": params[19],
            "finishing": params[20],
            "heading": params[21],
            "place_kicking": params[22],
            "curl": params[23],
            "speed": params[24],
            "acceleration": params[25],
            "kicking_power": params[26],
            "jump": params[27],
            "physical_contact": params[28],
            "balance": params[29],
            "stamina": params[30],
            "defensive_awareness": params[31],
            "tackling": params[32],
            "aggression": params[33],
            "defensive_engagement": params[34],
            "gk_awareness": params[35] if len(params) > 35 else 40,
            "gk_catching": params[36] if len(params) > 36 else 40,
            "gk_parrying": params[37] if len(params) > 37 else 40,
            "gk_reflexes": params[38] if len(params) > 38 else 40,
            "gk_reach": params[39] if len(params) > 39 else 40,
        }

        # Parse skills
        skills = {}
        for idx, skill_name in SKILLS_LIST:
            val = params[idx] if idx < len(params) else 0
            skills[str(idx)] = (val > 0)

        name = record.get("name") or gp.get("name") or f"Player {pid}"
        if str(pid) == "37576": name = "RONALDO R9"
        elif str(pid) == "9901397": name = "ZINEDINE ZIDANE"
        elif str(pid) == "40291": name = "MESUT ÖZIL"

        ps_list = gp.get("play_style", [1, 0])
        st1 = ps_list[0] if (isinstance(ps_list, list) and len(ps_list) > 0) else 1
        st2 = ps_list[1] if (isinstance(ps_list, list) and len(ps_list) > 1 and ps_list[1] > 0) else get_defensive_play_style(params[0] or 0, st1)

        summary = get_player_summary(str(pid), record)
        self.json_response({
            "id": str(pid),
            "name": name,
            "position_id": params[0] or 13,
            "position": POS_MAP.get(params[0] or 13, "CF"),
            "uniform_number": gp.get("uniform_number", 9),
            "play_style": st1,
            "defensive_play_style": st2,
            "rarity": gp.get("default_rarity", 5),
            "card_type": gp.get("type", "EPIC"),
            "age": params[46] or 25,
            "height": params[47] or 180,
            "weight": params[48] or 75,
            "preferred_foot": params[49] or 1,
            "ovr": summary["ovr"],
            "stats": stats,
            "skills": skills,
            "thumbnail": summary["thumbnail"],
            "booster_id": gp.get("initial_booster_id_list", [0, 0, 0])[0]
        })

    def api_get_player_image(self, pid):
        if not pid or pid == "blank":
            self.serve_fallback_svg()
            return
        img_file = THUMBNAIL_DIR / f"{pid}.png"
        if not img_file.exists():
            img_file = REPO_ROOT / "ziru-extra" / "responses" / "ziru_blank.png"
        if not img_file.exists():
            self.serve_fallback_svg()
            return
        self.serve_file(img_file, "image/png")

    def serve_fallback_svg(self):
        svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
            <rect width="200" height="200" fill="#141824"/>
            <circle cx="100" cy="75" r="38" fill="#2d3748"/>
            <path d="M40 180 C40 135, 70 120, 100 120 C130 120, 160 135, 160 180 Z" fill="#2d3748"/>
            <text x="100" y="195" font-family="sans-serif" font-size="12" fill="#718096" text-anchor="middle">eFootball Mod</text>
        </svg>""".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(svg)))
        self.end_headers()
        self.wfile.write(svg)

    def api_upload_player_image(self, data):
        pid = data.get("id")
        b64 = data.get("image")
        if not pid or not b64:
            self.json_response({"error": "Missing player id or image data"}, 400)
            return

        try:
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64)
            img_path = THUMBNAIL_DIR / f"{pid}.png"
            img_path.write_bytes(raw_bytes)

            if HAS_PIL:
                # Resize to standard thumbnail 256x256
                im = Image.open(img_path)
                im = im.convert("RGBA")
                im.thumbnail((512, 512), Image.Resampling.LANCZOS)
                im.save(img_path, format="PNG")

            self.json_response({"success": True, "thumbnail": f"/api/player/image?id={pid}&t={int(time.time())}"})
        except Exception as e:
            self.json_response({"error": f"Image processing failed: {str(e)}"}, 500)

    def api_save_player(self, data):
        pid = str(data.get("id", "")).strip()
        name = str(data.get("name", "")).strip()
        if not pid:
            self.json_response({"error": "Player ID is required"}, 400)
            return
        if not name:
            name = f"Player {pid}"

        records = load_records()
        existing = records.get(pid, {})
        gp = existing.get("gameplayer", {})

        # Build 147 parameters
        params = gp.get("parameters", [0] * 147)
        while len(params) < 147: params.append(0)

        # Position
        pos_id = int(data.get("position_id", params[0] or 13))
        params[0] = pos_id
        for i in range(1, 14): params[i] = 2 if i == pos_id else 0

        # Core Stats
        stats = data.get("stats", {})
        stat_keys = [
            ("offensive_awareness", 14), ("ball_control", 15), ("dribbling", 16),
            ("tight_possession", 17), ("low_pass", 18), ("lofted_pass", 19),
            ("finishing", 20), ("heading", 21), ("place_kicking", 22),
            ("curl", 23), ("speed", 24), ("acceleration", 25),
            ("kicking_power", 26), ("jump", 27), ("physical_contact", 28),
            ("balance", 29), ("stamina", 30), ("defensive_awareness", 31),
            ("tackling", 32), ("aggression", 33), ("defensive_engagement", 34),
            ("gk_awareness", 35), ("gk_catching", 36), ("gk_parrying", 37),
            ("gk_reflexes", 38), ("gk_reach", 39)
        ]
        for key, idx in stat_keys:
            if key in stats:
                params[idx] = max(40, min(105, int(stats[key])))

        # Attributes
        params[46] = int(data.get("age", params[46] or 25))
        params[47] = int(data.get("height", params[47] or 180))
        params[48] = int(data.get("weight", params[48] or 75))
        params[49] = int(data.get("preferred_foot", params[49] or 1))

        # Skills
        skills = data.get("skills", {})
        for idx, _ in SKILLS_LIST:
            params[idx] = 1 if skills.get(str(idx)) else 0

        serial = gp.get("gameplayer_id", {}).get("serial") or (359042717000000000 + int(pid) % 1000000)
        uniform_num = int(data.get("uniform_number", gp.get("uniform_number", 9)))
        card_type = data.get("card_type", gp.get("type", "EPIC"))
        rarity = int(data.get("rarity", gp.get("default_rarity", 5)))
        play_style = int(data.get("play_style", 1))
        def_play_style = int(data.get("defensive_play_style", 0))
        if def_play_style <= 0:
            def_play_style = get_defensive_play_style(params[0] or 0, play_style)
        if len(params) >= 70:
            params[61] = play_style
            params[62] = def_play_style
        booster_id = int(data.get("booster_id", 0))

        updated_record = {
            "name": name,
            "gameplayer": {
                "gameplayer_id": {"id": int(pid), "serial": serial},
                "games": gp.get("games", 0),
                "goal": gp.get("goal", 0),
                "assist": gp.get("assist", 0),
                "red_card": 0,
                "sell_gp": 100000,
                "sell_item_list": [{"item": {"item_type": "LEVEL_TRAINING", "grade": 4, "effect": 10000}, "present_num": 1}],
                "uniform_number": uniform_num,
                "level_info": {
                    "level": 1,
                    "level_limit": 1,
                    "exp_total": 0,
                    "exp_current_level": 0,
                    "exp_to_next_level": 0,
                    "customize_point": 0
                },
                "is_lock": "YES",
                "play_style": [play_style, def_play_style],
                "initial_base_team_id": 0,
                "initial_base_national_team_id": gp.get("initial_base_national_team_id", 0),
                "parameters": params,
                "original_parameters": params,
                "default_rarity": rarity,
                "type": card_type,
                "acquisition_date": int(time.time()),
                "initial_booster_id_list": [booster_id, 0, 0]
            }
        }
        records[pid] = updated_record
        save_records(records)
        self.json_response({"success": True, "player": get_player_summary(pid, updated_record)})

    def api_list_boxes(self):
        if not AGENTLIST_FILE.exists():
            self.json_response({"boxes": []}); return
        try:
            with open(AGENTLIST_FILE, "r") as f:
                d = json.load(f)
            boxes = []
            for b in d.get("agent_list", []):
                boxes.append({
                    "id": b.get("agent_id"),
                    "title": b.get("name") or b.get("title") or f"Agent {b.get('agent_id')}",
                    "count": len(b.get("player_list", [])),
                    "players": [p.get("id") for p in b.get("player_list", [])]
                })
            self.json_response({"boxes": boxes})
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def api_add_player_to_box(self, data):
        pid = int(data.get("player_id", 0))
        box_id = int(data.get("box_id", 7001))
        if pid <= 0:
            self.json_response({"error": "Invalid player ID"}, 400)
            return

        try:
            with open(AGENTLIST_FILE, "r") as f:
                d = json.load(f)
            for b in d.get("agent_list", []):
                if b.get("agent_id") == box_id:
                    plist = b.setdefault("player_list", [])
                    if not any(p.get("id") == pid for p in plist):
                        plist.append({"id": pid, "serial": 359042717000000000 + pid})
                    b["total_count"] = len(plist)
                    break
            with open(AGENTLIST_FILE, "w") as f:
                json.dump(d, f, indent=2)

            self.json_response({"success": True, "message": f"Added player {pid} to box {box_id}"})
        except Exception as e:
            self.json_response({"error": str(e)}, 500)

    def api_add_to_squad(self, data):
        pid = int(data.get("player_id", 0))
        uni = int(data.get("uniform_number", 9))
        slot = int(data.get("slot", 3)) # Default CF slot 3
        if pid <= 0:
            self.json_response({"error": "Invalid player ID"}, 400)
            return

        serial = 359042717000000000 + pid
        # We can update ziru_save.db directly if it exists or trigger deploy
        db_path = REPO_ROOT / "ziru_save.db"
        if not db_path.exists():
            db_path = Path("/tmp/ziru_save_device.db")

        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT squad_json FROM squads WHERE squad_id = 9")
                row = c.fetchone()
                if row:
                    sq = json.loads(row[0])
                    plist = sq.get("player_list", [])
                    if slot < len(plist):
                        plist[slot] = {"gameplayer_id": {"id": pid, "serial": serial}, "uniform_number": uni}
                    sq["player_list"] = plist
                    c.execute("UPDATE squads SET squad_json = ?, updated_at = ? WHERE squad_id = 9", (json.dumps(sq), int(time.time()*1000)))
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"[WARN] Local DB squad update failed: {e}")

        self.json_response({"success": True, "message": f"Assigned player {pid} (No. {uni}) to Squad 9 Starter #{slot}"})

    def api_sync_device(self):
        if not HAS_DEVICE:
            self.json_response({"error": "pymobiledevice3 not installed in this environment"}, 500)
            return

        try:
            # Run deploy_to_device.py directly
            import subprocess
            py_bin = sys.executable
            deploy_script = REPO_ROOT / "tools" / "deploy_to_device.py"
            res = subprocess.run([py_bin, str(deploy_script)], capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                self.json_response({"success": True, "log": res.stdout})
            else:
                self.json_response({"error": f"Deploy failed with code {res.returncode}", "log": res.stderr or res.stdout}, 500)
        except Exception as e:
            self.json_response({"error": f"Sync failed: {str(e)}"}, 500)

def main():
    port = 8899
    server = HTTPServer(("127.0.0.1", port), CardEditorHandler)
    print(f"\n=======================================================")
    print(f"  PES2027 CARD MOD STUDIO - LOCAL WEB SERVER")
    print(f"  Address: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.server_close()

if __name__ == "__main__":
    main()
