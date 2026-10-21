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

# Skill definitions (index in parameters[70..143])
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
    (105, "Visionary Pass (Show Time)"),
    (140, "Edge Crossing (Show Time)"),
    (141, "Game-Changing Pass (Show Time)"),
    (143, "Blitz Curler (Show Time)")
]

# Boosters list: (Booster ID, Name & Effect)
BOOSTERS_LIST = [
    (0, "Không dùng Booster"),
    (70, "Striker Sense (+3 Nhận thức TC, Dứt điểm)"),
    (12, "Shooting (+3 Dứt điểm, Lực sút)"),
    (15, "Technique (+3 Kiểm soát bóng, Rê bóng)"),
    (76, "Fantasista (+3 Rê bóng, Giữ bóng hẹp)"),
    (187, "Ball Carrying (+3 Tốc độ, Rê bóng)"),
    (28, "Agility (+3 Tốc độ, Tăng tốc)"),
    (16, "Passing (+3 Chuyền sệt, Chuyền bổng)"),
    (71, "Duel (+3 Tì đè tranh chấp, Xoạc bóng)"),
    (19, "Defending (+3 Nhận thức PN, Xoạc bóng)"),
    (20, "Physical Contact (+3 Tì đè, Bật nhảy)"),
    (170, "Showtime Special (+3 Tốc độ, Dứt điểm, Tăng tốc)"),
    (96, "Phenomenal Finisher (+3 Dứt điểm, Kiểm soát)"),
    (136, "Epic Legend Slot (+3 Toàn diện)")
]
BOOSTERS_MAP = dict(BOOSTERS_LIST)

# Map from parameter index to Konami SkillCard ID
PARAM_TO_SKILL_ID = {
    104: 22,  # Phenomenal Finishing
    103: 21,  # Momentum Dribbling
    102: 10,  # Fortress
    105: 45,  # Visionary Pass
    143: 72,  # Blitz Curler
    140: 14,  # Edge Crossing
    141: 42,  # Game-Changing Pass
    70: 0,    # Scissors Feint
    71: 2,    # Double Touch
    72: 3,    # Flip Flap
    73: 4,    # Marseille Turn
    74: 6,    # Sombrero
    75: 7,    # Cross Over Turn
    76: 15,   # Cut Behind & Turn
    77: 17,   # Scotch Move
    78: 20,   # Heading
    79: 26,   # Long Range Shooting
    80: 27,   # Chip Shot Control
    81: 28,   # Long Range Curler
    82: 31,   # Knuckle Shot
    83: 33,   # Dipping Shot
    84: 34,   # Rising Shot
    85: 36,   # Acrobatic Finishing
    86: 37,   # Heel Trick
    87: 43,   # First-time Shot
    88: 44,   # One-touch Pass
    89: 46,   # Through Passing
    90: 47,   # Weighted Pass
    91: 54,   # Pinpoint Crossing
    92: 55,   # Outside Curler
    93: 56,   # No Look Pass
    94: 64,   # Low Lofted Pass
    95: 67,   # Interception
    96: 69,   # Man Marking
    97: 70,   # Blocker
    98: 38,   # Acrobatic Clear
    99: 48,   # Captaincy
    100: 49,  # Super-sub
    101: 19   # Fighting Spirit
}

# Team Names mapping from ZIRU_2027_TEAM_NAMES.json
TEAMS_FILE = RESPONSES_DIR / "ZIRU_2027_TEAM_NAMES.json"
TEAMS_MAP = {}
if TEAMS_FILE.exists():
    try:
        with open(TEAMS_FILE, "r", encoding="utf-8") as f:
            TEAMS_MAP = json.load(f)
    except Exception:
        TEAMS_MAP = {}

# Featured & Famous Card Direct ID Map
KNOWN_PLAYERS = {
    "37576": "RONALDO R9",
    "9901397": "ZINEDINE ZIDANE",
    "40291": "MESUT ÖZIL",
    "88032334054874": "LIONEL MESSI",
    "88029649706260": "ROBERT LEWANDOWSKI",
    "88040387117922": "NEYMAR JR",
    "88040387251711": "LAMINE YAMAL",
    "87963883146703": "PEDRI",
    "88030992010723": "GAVI",
    "88044145253792": "FRENKIE DE JONG",
    "88039581945323": "ALEJANDRO BALDE",
    "89129429769559": "MARC-ANDRÉ TER STEGEN",
    "89129966765504": "RONALD ARAÚJO",
    "88029918174624": "F. DE JONG (CB)",
    "88030455139819": "JULES KOUNDÉ",
    "88036360589289": "JOHAN CRUYFF",
    "88032334188027": "IKER CASILLAS",
    "88036360723168": "PAOLO MALDINI",
    "88040387251641": "ROBERTO CARLOS",
    "89071179308448": "RUUD GULLIT",
    "88040387180670": "PATRICK VIEIRA",
    "89133456301399": "DIEGO MARADONA",
}

# Base Player IDs to Real Names Map
KNOWN_BASE_PLAYERS = {
    # Legends & Icons
    4073: "JOHAN CRUYFF",
    812: "RUUD GULLIT",
    820: "PATRICK VIEIRA",
    852: "PAOLO MALDINI",
    866: "ALESSANDRO NESTA",
    867: "KAKÁ",
    982: "ANDREA PIRLO",
    983: "GENNARO GATTUSO",
    1004: "DAVID BECKHAM",
    1005: "PAUL SCHOLES",
    1021: "STEVEN GERRARD",
    1022: "MICHAEL OWEN",
    1046: "FRANK LAMPARD",
    1047: "DIDIER DROGBA",
    1089: "THIERRY HENRY",
    1183: "ROBERTO CARLOS",
    1202: "RIVALDO",
    1203: "ROMÁRIO",
    1204: "BEBETO",
    2379: "MANUEL NEUER",
    3214: "RONALDINHO GAÚCHO",
    37576: "RONALDO R9",
    9901397: "ZINEDINE ZIDANE",
    40291: "MESUT ÖZIL",
    134577: "PATRICK VIEIRA",
    134616: "FRANZ BECKENBAUER",
    134617: "K. RUMMENIGGE",
    134620: "FRANK RIJKAARD",
    134624: "CAFU",
    134631: "DENNIS BERGKAMP",
    134632: "MARCO VAN BASTEN",
    134633: "CLARENCE SEEDORF",
    134634: "RUUD GULLIT",
    134639: "DIEGO MARADONA",
    134640: "GABRIEL BATISTUTA",
    134641: "JAVIER ZANETTI",
    134648: "DECO",
    134649: "CARLES PUYOL",
    134650: "XAVI HERNÁNDEZ",
    134651: "ANDRÉS INIESTA",
    134652: "IKER CASILLAS",
    134653: "PETR CECH",

    # Modern Superstars & POTW Highlights
    4522: "CRISTIANO RONALDO",
    7511: "LIONEL MESSI",
    16346: "CASEMIRO",
    16362: "THIBAUT COURTOIS",
    33185: "LUKA MODRIĆ",
    33702: "TONI KROOS",
    34881: "SERGIO RAMOS",
    35496: "ROBERT LEWANDOWSKI",
    40240: "NEYMAR JR",
    40352: "LUIS SUÁREZ",
    41126: "ANTOINE GRIEZMANN",
    44379: "KEVIN DE BRUYNE",
    45097: "SON HEUNG-MIN",
    45993: "HARRY KANE",
    57123: "MOHAMED SALAH",
    104677: "BRUNO FERNANDES",
    104717: "MARCUS RASHFORD",
    108959: "RODRI",
    109941: "BERNARDO SILVA",
    110718: "OUSMANE DEMBÉLÉ",
    113960: "KYLIAN MBAPPÉ",
    114105: "LAUTARO MARTÍNEZ",
    115881: "ACHRAF HAKIMI",
    116543: "VINÍCIUS JÚNIOR",
    129369: "JUDE BELLINGHAM",
    132933: "RODRI",
    133543: "ERLING HAALAND",
    134589: "BUKAYO SAKA",
    134594: "MARTIN ØDEGAARD",
    134595: "DECLAN RICE",
    134604: "PHIL FODEN",
    134605: "BERNARDO SILVA",
    134608: "RÚBEN DIAS",
    137962: "MOHAMED SALAH",
    137990: "VIRGIL VAN DIJK",
    138000: "ALISSON BECKER",
    138392: "T. ALEXANDER-ARNOLD",
    139679: "FEDERICO VALVERDE",
    141308: "THEO HERNÁNDEZ",
    160577: "EDUARDO CAMAVINGA",
    166176: "AURÉLIEN TCHOUAMÉNI",
}

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

def get_player_name(pid_str, item, pos_name):
    # 1. Direct card match
    if pid_str in KNOWN_PLAYERS:
        return KNOWN_PLAYERS[pid_str]

    # 2. Base ID match
    try:
        base_id = int(pid_str) & 0xFFFFFF
        if base_id in KNOWN_BASE_PLAYERS:
            return KNOWN_BASE_PLAYERS[base_id]
    except Exception:
        pass

    # 3. Check explicit name in record
    gp = item.get("gameplayer", {})
    if item.get("name"):
        return item["name"]
    if gp.get("name"):
        return gp["name"]

    # 4. Construct descriptive title using Team & Position
    tid = str(gp.get("initial_base_team_id", 0))
    nid = str(gp.get("initial_base_national_team_id", 0))
    tinfo = TEAMS_MAP.get(tid) or TEAMS_MAP.get(nid) or {}
    tname = tinfo.get("name") or tinfo.get("short") or ""
    uni = gp.get("uniform_number") or 0

    if tname:
        if uni > 0:
            return f"{pos_name} • {tname} #{uni}"
        return f"{pos_name} • {tname}"

    return f"{pos_name} • ID {pid_str[-6:]}"

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

    pid_str = str(pid)
    name = get_player_name(pid_str, item, pos_name)

    tid = str(gp.get("initial_base_team_id", 0))
    nid = str(gp.get("initial_base_national_team_id", 0))
    tinfo = TEAMS_MAP.get(tid) or TEAMS_MAP.get(nid) or {}
    team_name = tinfo.get("name") or "Free Agent"
    team_short = tinfo.get("short") or "PES"

    thumb_url = f"/api/player/image?id={pid}"
    return {
        "id": pid_str,
        "name": name,
        "team": team_name,
        "team_short": team_short,
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
            "booster_id": gp.get("initial_booster_id_list", [0, 0, 0])[0],
            "additional_skill_id": gp.get("additional_skill_id", []),
            "boosters_list": [{"id": b[0], "name": b[1]} for b in BOOSTERS_LIST]
        })

    def api_get_player_image(self, pid):
        if not pid or pid == "blank":
            self.serve_fallback_svg()
            return
        img_file = THUMBNAIL_DIR / f"{pid}.png"
        if img_file.exists():
            self.serve_file(img_file, "image/png")
            return
        
        # Check base id image if available
        try:
            base_id = int(pid) & 0xFFFFFF
            base_img = THUMBNAIL_DIR / f"{base_id}.png"
            if base_img.exists():
                self.serve_file(base_img, "image/png")
                return
        except Exception:
            pass

        # Dynamically render aesthetic eFootball-styled SVG card
        self.serve_player_card_svg(str(pid))

    def serve_player_card_svg(self, pid):
        records = load_records()
        record = records.get(pid, {})
        summary = get_player_summary(pid, record) if record else {
            "name": f"Player {pid[-6:]}",
            "position": "CF",
            "ovr": 90,
            "team_short": "PES",
            "card_type": "EPIC"
        }

        pos = summary.get("position", "CF")
        ovr = summary.get("ovr", 90)
        card_type = summary.get("card_type", "EPIC")
        team_short = summary.get("team_short", "PES")
        name = summary.get("name", "PLAYER")
        
        # Determine position color
        if pos in ["CF", "SS", "LWF", "RWF"]:
            pos_color = "#ff4757"  # Red / Coral for Attackers
        elif pos in ["AMF", "CMF", "LMF", "RMF"]:
            pos_color = "#00e5ff"  # Cyan for Midfielders
        elif pos == "DMF":
            pos_color = "#2ed573"  # Emerald Green for DMF
        elif pos in ["CB", "LB", "RB"]:
            pos_color = "#ffa502"  # Amber Orange for Defenders
        else:
            pos_color = "#3b82f6"  # Blue for GK

        # Initials
        words = [w for w in name.replace("•", " ").split() if not w.startswith("#")]
        initials = "".join(w[0] for w in words[:2]).upper() if words else pos

        # Display name shortened for card
        display_name = name.split("•")[0].strip() if "•" in name else name
        if len(display_name) > 16:
            display_name = display_name[:14] + ".."

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="200" height="240">
  <defs>
    <linearGradient id="cardBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#191d30"/>
      <stop offset="100%" stop-color="#090b14"/>
    </linearGradient>
    <linearGradient id="glowGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{pos_color}" stop-opacity="0.3"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="196" height="236" rx="14" fill="url(#cardBg)" stroke="{pos_color}" stroke-opacity="0.6" stroke-width="2"/>
  <rect x="2" y="2" width="196" height="80" rx="14" fill="url(#glowGrad)"/>
  
  <text x="16" y="40" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-weight="900" font-size="28" fill="#ffffff">{ovr}</text>
  <rect x="16" y="48" width="44" height="18" rx="5" fill="{pos_color}"/>
  <text x="38" y="61" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-weight="800" font-size="11" fill="#000000" text-anchor="middle">{pos}</text>
  
  <text x="184" y="30" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-weight="700" font-size="9" fill="#94a3b8" text-anchor="end">{card_type}</text>
  <text x="184" y="46" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-weight="800" font-size="11" fill="{pos_color}" text-anchor="end">{team_short}</text>
  
  <circle cx="100" cy="115" r="32" fill="#222842" stroke="{pos_color}" stroke-opacity="0.4" stroke-width="1.5"/>
  <path d="M56 185 C56 150, 78 138, 100 138 C122 138, 144 150, 144 185 Z" fill="#222842"/>
  <text x="100" y="122" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-weight="900" font-size="16" fill="#f8fafc" text-anchor="middle">{initials}</text>
  
  <rect x="8" y="196" width="184" height="32" rx="7" fill="rgba(10, 12, 22, 0.85)" stroke="{pos_color}" stroke-opacity="0.3" stroke-width="1"/>
  <text x="100" y="217" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-weight="800" font-size="11" fill="#ffffff" text-anchor="middle">{display_name}</text>
</svg>""".encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(svg)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(svg)

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

        # Collect additional_skill_id (prioritize ShowTime skills first)
        add_skills = []
        st_priority = [22, 21, 10, 45, 72, 14, 42]
        for p_idx, s_id in PARAM_TO_SKILL_ID.items():
            if skills.get(str(p_idx)):
                if s_id not in add_skills:
                    add_skills.append(s_id)
        add_skills.sort(key=lambda x: 0 if x in st_priority else 1)
        add_skills = add_skills[:5]

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
        booster_list = [booster_id, 136 if booster_id > 0 else 0, 0]
        if len(params) >= 145:
            params[142] = booster_id
            params[143] = 136 if booster_id > 0 else 0
            params[144] = 0

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
                "initial_base_team_id": gp.get("initial_base_team_id", 0),
                "initial_base_national_team_id": gp.get("initial_base_national_team_id", 0),
                "parameters": params,
                "original_parameters": params,
                "default_rarity": rarity,
                "type": card_type,
                "acquisition_date": int(time.time()),
                "initial_booster_id_list": booster_list,
                "additional_skill_id": add_skills
            }
        }
        records[pid] = updated_record
        save_records(records)

        # 1. Update SQLite ziru_save.db table 'players'
        try:
            db_path = REPO_ROOT / "ziru_save.db"
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                now_ts = int(time.time() * 1000)
                c.execute("INSERT OR REPLACE INTO players (serial, player_id, player_json, updated_at) VALUES (?, ?, ?, ?)",
                          (serial, int(pid), json.dumps(updated_record["gameplayer"]), now_ts))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"[WARN] Failed to write player to ziru_save.db: {e}")

        # 2. Update CmdLogin.json if player is in owned squad
        try:
            cmd_login_file = RESPONSES_DIR / "CmdLogin.json"
            if cmd_login_file.exists():
                with open(cmd_login_file, "r", encoding="utf-8") as f:
                    cl_data = json.load(f)
                gp_list = cl_data.get("entry_info", {}).get("gameplayer_list", [])
                found_cl = False
                for item in gp_list:
                    if item.get("gameplayer_id", {}).get("id") == int(pid):
                        item["parameters"] = params
                        item["original_parameters"] = params
                        item["initial_booster_id_list"] = booster_list
                        item["additional_skill_id"] = add_skills
                        item["type"] = card_type
                        found_cl = True
                        break
                if found_cl:
                    with open(cmd_login_file, "w", encoding="utf-8") as f:
                        json.dump(cl_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Failed to update CmdLogin.json: {e}")

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
        try:
            import subprocess
            pipx_py = Path("/Users/nhatminh/.local/pipx/.cache/26d7aa47311ea6b/bin/python3")
            py_bin = str(pipx_py) if pipx_py.exists() else sys.executable
            deploy_script = REPO_ROOT / "tools" / "restore_all_to_device.py"
            res = subprocess.run([py_bin, str(deploy_script)], capture_output=True, text=True, timeout=180)
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
