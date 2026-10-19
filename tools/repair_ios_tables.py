"""Convert legacy named Playstyle/PlayerSkill tables to iOS 11.1.1 records.

Only these tables change; every other CPK byte is preserved. Layout evidence:
pesdb::Manager record-size table at 0x105784d38, entries 42 and 43 = 4;
LinkPesdb::ImportPlayStyleData at 0x104ba1048 advances the source by 4.
Input and output are local user-owned assets, never repository fixtures.
"""
import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path
try:
    from cpk_toc import utf_table
except ImportError:
    from tools.cpk_toc import utf_table


def unpack_wesys(data):
    if data[3:8] != b"WESYS":
        raise ValueError("not WESYS")
    compressed, size = struct.unpack_from("<II", data, 8)
    payload = bytearray(data[16:16 + compressed])
    if len(payload) != compressed:
        raise ValueError("truncated WESYS")
    if data[2] & 2:
        if data[1] & 15 != 2:
            raise ValueError("unsupported WESYS crypt version")
        # sys::File::PostProcessMainFunc, iOS 11.1.1 0x104b7b4e4..588.
        x, y, z = 0xed5b2960, 0x4a523b4e, 0xf3a31bad
        w = (compressed | size << 16) & 0xffffffff
        for p in range(0, compressed // 4 * 4, 4):
            t = (x ^ x << 11) & 0xffffffff
            x, y, z = y, z, w
            w = (w ^ w >> 19 ^ t ^ t >> 8) & 0xffffffff
            struct.pack_into("<I", payload, p, struct.unpack_from("<I", payload, p)[0] ^ w)
    raw = zlib.decompress(payload) if data[2] & 1 else bytes(payload)
    if len(raw) != size:
        raise ValueError("WESYS size mismatch")
    return raw


def compact_table(raw):
    # Legacy records contain a 4-byte bitfield followed by localized names.
    # Playstyle.bin has 168 bytes per record (36 records).
    # PlayerSkill.bin has 104 bytes per record (72 records).
    # Both tables use 4-byte records on iOS 11.1.1 (pesdb::Manager entries 42 and 43).
    if not raw:
        return raw
    candidate_matched = False
    for stride in (168, 104):
        if len(raw) % stride == 0:
            count = len(raw) // stride
            if 30 <= count <= 100:
                candidate_matched = True
                records = [raw[i * stride:(i + 1) * stride] for i in range(count)]
                ids63 = [struct.unpack_from("<I", r)[0] & 63 for r in records]
                ids127 = [struct.unpack_from("<I", r)[0] & 127 for r in records]
                ids255 = [struct.unpack_from("<I", r)[0] & 255 for r in records]
                target = list(range(count))
                if ids63 == target or ids127 == target or ids255 == target:
                    return b"".join(r[:4] for r in records)
    if candidate_matched:
        raise ValueError("unrecognized legacy table IDs")
    return raw


def to_title_case(s):
    # Normalize Turkish dotted I before capitalizing/lowercasing
    s_clean = s.replace('\u0130', 'I').replace('\u0131', 'i')
    parts = re.split(r"(\s+|-|\.|\x27)", s_clean)
    res = []
    for p in parts:
        if p and (p.isalpha() or any(c.isalpha() for c in p)):
            res.append(p.capitalize())
        else:
            res.append(p)
    out = "".join(res)
    return re.sub(r"'([a-z])", lambda m: "'" + m.group(1).upper(), out)


def convert_player_names_title_case(raw_bytes):
    raw = bytearray(raw_bytes)
    for m in re.finditer(rb'([A-Za-z\x80-\xff][A-Za-z0-9\x80-\xff .\x27-]{1,60})\x00', raw):
        name_bytes = m.group(1)
        try:
            name_str = name_bytes.decode("utf-8")
        except Exception:
            continue
        if any(c.isdigit() or c in "/\\_#@$%^*+=<>{}[]()~`|" for c in name_str):
            continue
        if name_str.isupper() and len(name_str) >= 2 and any(c.isalpha() for c in name_str):
            new_name = to_title_case(name_str)
            new_bytes = new_name.encode("utf-8")
            if len(new_bytes) <= len(name_bytes):
                start = m.start(1)
                raw[start:start + len(new_bytes)] = new_bytes
                if len(new_bytes) < len(name_bytes):
                    raw[start + len(new_bytes):start + len(name_bytes)] = b'\x00' * (len(name_bytes) - len(new_bytes))
    return bytes(raw)


REAL_TEAM_MAP = {
    "Madrid Chamartin B": "Real Madrid",
    "Madrid Rosas RB": "Atletico Madrid",
    "Manchester B": "Manchester City",
    "Liverpool R": "Liverpool FC",
    "Chelsea B": "Chelsea FC",
    "Piemonte BN": "Juventus",
    "Tottenham WB": "Tottenham Hotspur",
    "Newcastle WB": "Newcastle United",
    "Aston RB": "Aston Villa",
    "Everton B": "Everton FC",
    "Valencia BN": "Valencia CF",
    "West Ham RB": "West Ham United",
    "Sevilla Triana VB": "Real Betis",
    "Leicester B": "Leicester City",
    "Brighton WB": "Brighton & Hove Albion",
    "Bologna RB": "Bologna FC",
    "Cagliari RB": "Cagliari Calcio",
    "Genova RB": "Genoa CFC",
    "Mallorca RN": "RCD Mallorca",
    "Schalke BW": "FC Schalke 04",
    "Lombardia NA": "Inter Milan",
    "Milano RN": "AC Milan",
    "Vasco Da Gama": "Vasco da Gama",
}


def fix_real_team_names(raw_bytes):
    raw = bytearray(raw_bytes)
    rec_size = 1600
    count = len(raw) // rec_size
    for i in range(count):
        offset = i * rec_size + 396
        end = raw.find(b"\x00", offset)
        if end != -1 and end < offset + 70:
            name = raw[offset:end].decode("utf-8", errors="ignore")
            if name in REAL_TEAM_MAP:
                new_name = REAL_TEAM_MAP[name].encode("utf-8")
                raw[offset:offset + len(new_name)] = new_name
                raw[offset + len(new_name):offset + 70] = b"\x00" * (70 - len(new_name))
    return bytes(raw)


def repair_cpk_bytes(data):
    result = bytearray(data)
    header = utf_table(data[16:0x800])[0]
    toc = header["TocOffset"]
    length = struct.unpack_from("<Q", data, toc + 8)[0]
    rows = utf_table(data[toc + 16:toc + 16 + length])
    changes = []
    for row in rows:
        fn = row.get("FileName")
        if fn not in ("Playstyle.bin", "PlayerSkill.bin", "Player.bin"):
            continue
        offset = min(toc, header["ContentOffset"]) + row["FileOffset"]
        size = row["FileSize"]
        if size != row["ExtractSize"]:
            raise ValueError("CPK-compressed table unsupported")
        old = unpack_wesys(data[offset:offset + size])
        if fn == "Player.bin":
            new = convert_player_names_title_case(old)
            divisor = 240
        else:
            new = compact_table(old)
            divisor = 4
        if new == old:
            continue
        payload = zlib.compress(new, 9)
        # Native WESYS explicitly supports compressed, unencrypted payloads.
        packed = b"\x00\x01\x01WESYS" + struct.pack("<II", len(payload), len(new)) + payload
        if len(packed) > size:
            raise ValueError("replacement exceeds table allocation")
        result[offset:offset + size] = packed.ljust(size, b"\0")
        changes.append({"table": fn, "before": len(old), "after": len(new), "records": len(new) // divisor})
    return bytes(result), changes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    original = args.input.read_bytes()
    fixed, changes = repair_cpk_bytes(original)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.resolve() == args.input.resolve():
        raise SystemExit("use a separate output path")
    args.output.write_bytes(fixed)
    print(json.dumps({"changes": changes, "sha256": hashlib.sha256(fixed).hexdigest()}, indent=2))
