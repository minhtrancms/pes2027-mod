#!/usr/bin/env python3
"""Build pc8000_mobile_ios.{pak, utoc, ucas} containing authentic high-resolution
emblems for unlicensed clubs: Real Madrid, Man City, Chelsea, Liverpool, Juventus,
Atlético de Madrid, Tottenham, Newcastle, Aston Villa, West Ham, Sevilla, Fiorentina, Roma.
"""
import glob, hashlib, json, os, struct, subprocess, sys, urllib.request, zlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
import tools.make_extra_pak as p
NAME = "pc8000_mobile_ios"
BLOCK = 65536
PC1000_PATH = os.path.join(REPO_ROOT, "PES2027-data", "pak", "pc1000_mobile_ios.utoc")
OUT_DIR = os.path.join(REPO_ROOT, "ziru-extra", "pak_extra")
PNG2BGRA = os.path.join(REPO_ROOT, "build", "png2bgra")

CLUBS = {
    109: ("Real Madrid", 8633),
    173: ("Manchester City", 8456),
    102: ("Chelsea FC", 8455),
    103: ("Liverpool FC", 8650),
    120: ("Juventus FC", 9885),
    172: ("Atlético de Madrid", 9906),
    104: ("Tottenham Hotspur", 8586),
    106: ("Aston Villa", 10252),
    105: ("Newcastle United", 10261),
    107: ("West Ham United", 8654),
    110: ("Sevilla FC", 8302),
    124: ("ACF Fiorentina", 8535),
    125: ("AS Roma", 8686),
    127: ("FC Bayern München", 9823),
    177: ("Everton FC", 8668),
    178: ("Fulham FC", 9879),
    377: ("Brighton & Hove Albion", 10204),
    4180: ("Brentford FC", 9937),
    382: ("Crystal Palace", 9826),
    389: ("Nottingham Forest", 10203),
    208: ("Wolverhampton Wanderers", 8659),
    4071: ("AFC Bournemouth", 8678),
    258: ("Athletic Club Bilbao", 8315),
    2187: ("Girona FC", 7732),
    111: ("Real Betis", 8603),
    112: ("Real Sociedad", 8560),
    113: ("Villarreal CF", 10205),
}

VARIANTS = [
    ("_l", 256, 256, 263192, 1048),
    ("",   128, 128, 66576,  1040),
    ("_s", 64,  64,  17432,  1048),
]

def main():
    print(f"Loading base TOC from {PC1000_PATH}...")
    base_toc = p.Toc(PC1000_PATH)

    os.makedirs("/tmp/club_logos", exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    # 1. Download logos
    png_map = {}
    for tid, (name, fid) in CLUBS.items():
        png_path = f"/tmp/club_logos/{tid}_{fid}.png"
        if not os.path.exists(png_path) or os.path.getsize(png_path) < 1000:
            url = f"https://images.fotmob.com/image_resources/logo/teamlogo/{fid}.png"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            with open(png_path, "wb") as f:
                f.write(data)
            print(f"Downloaded logo for {name} ({len(data)} bytes)")
        png_map[tid] = png_path

    # 2. Extract headers and build patched uassets
    chunks = []
    paths = {}
    entries = []
    pids = []
    mount = "../../../"

    for tid, (name, fid) in CLUBS.items():
        png_path = png_map[tid]
        for suffix, w, h, expected_size, hdr_size in VARIANTS:
            raw_path = f"/tmp/club_logos/{tid}_{w}x{h}.raw"
            cmd = [PNG2BGRA, png_path, str(w), str(h), raw_path]
            subprocess.check_call(cmd)
            raw_tex = open(raw_path, "rb").read()
            assert len(raw_tex) == w * h * 4

            # Read template from base_toc
            orig_rel_path = f"ui/Data/Symbol/Emblem/e_{tid:06d}_f{suffix}.uasset"
            if orig_rel_path not in base_toc.files:
                print(f"Warning: {orig_rel_path} not found in pc1000, skipping")
                continue

            orig_idx = base_toc.files[orig_rel_path]
            orig_data = base_toc.read(orig_idx)
            header = orig_data[:hdr_size]
            patched_data = header + raw_tex
            assert len(patched_data) == expected_size, f"{len(patched_data)} != {expected_size}"

            # Create entry for _f (unlicensed) and _r (licensed)
            for prefix_type in ("f", "r"):
                target_rel_path = f"ui/Data/Symbol/Emblem/e_{tid:06d}_{prefix_type}{suffix}.uasset"
                
                # Derive deterministic chunk ID and package ID
                pid_hash = hashlib.sha1(target_rel_path.lower().encode()).digest()
                pid = struct.unpack("<Q", pid_hash[:8])[0]
                cid_b = struct.pack("<Q", pid) + b"\x00\x00\x00\x02"

                meta = hashlib.sha1(patched_data).digest() + b"\x00" * 13
                ni = len(chunks)
                chunks.append((cid_b, patched_data, meta))
                paths[target_rel_path] = ni
                entries.append((b"\x01\x00\x00\x00\x01\x00\x00\x00", []))
                pids.append(pid)

    print(f"Created {len(paths)} real emblem packages across {len(CLUBS)} clubs.")

    # 3. Assemble IoStore container
    cid = struct.unpack("<Q", hashlib.sha1(NAME.encode()).digest()[:8])[0]
    hb = bytearray(struct.pack("<QI", cid, len(pids)))
    hb += struct.pack("<i", 0)                                   # names
    hb += struct.pack("<i", 8) + struct.pack("<Q", 0xC1640000)  # name hashes
    hb += struct.pack("<i", len(pids)) + struct.pack("<%dQ" % len(pids), *pids)
    st = p.build_store(entries)
    hb += struct.pack("<i", len(st)) + st
    hb += struct.pack("<i", 0) + struct.pack("<i", 0)            # culture package map, package redirects
    hdr_id = struct.pack("<Q", cid) + b"\0\0\0\x0a"
    chunks.append((hdr_id, bytes(hb), hashlib.sha1(bytes(hb)).digest() + b"\0" * 13))

    ucas_path = os.path.join(OUT_DIR, NAME + ".ucas")
    ucas = open(ucas_path, "wb")
    ids, ols, blocks = [], [], []
    voff = 0
    for cid_b, data, meta in chunks:
        ids.append(cid_b)
        ols.append((voff, len(data)))
        for off in range(0, len(data), BLOCK):
            raw = data[off:off + BLOCK]
            comp = zlib.compress(raw, 9)
            pos = ucas.tell()
            if len(comp) < len(raw):
                ucas.write(comp)
                blocks.append((pos, len(comp), len(raw), 1))
            else:
                ucas.write(raw)
                blocks.append((pos, len(raw), len(raw), 0))
        voff += (len(data) + BLOCK - 1) // BLOCK * BLOCK
    ucas.close()

    di = p.dir_index(mount, paths)
    src_raw = base_toc.raw
    hdr = bytearray(src_raw[:base_toc.hs])
    struct.pack_into("<IIIIIIIII", hdr, 20, base_toc.hs, len(ids), len(blocks), 12, 1, 32, BLOCK, len(di), 0)
    struct.pack_into("<Q", hdr, 56, cid)
    hdr[64:80] = b"\0" * 16
    hdr[80] = 1 | 8  # Compressed | Indexed
    toc = bytearray(hdr)
    toc += b"".join(ids)
    toc += b"".join(o.to_bytes(5, "big") + l.to_bytes(5, "big") for o, l in ols)
    toc += b"".join(o.to_bytes(5, "little") + c.to_bytes(3, "little") + u.to_bytes(3, "little") + bytes([m]) for o, c, u, m in blocks)
    toc += b"Zlib".ljust(32, b"\0")
    toc += di
    toc += b"".join(m if len(m) == 33 else (m + b"\0" * 33)[:33] for _, _, m in chunks)

    utoc_path = os.path.join(OUT_DIR, NAME + ".utoc")
    with open(utoc_path, "wb") as f:
        f.write(toc)

    # Empty companion pak
    pak_path = os.path.join(OUT_DIR, NAME + ".pak")
    companion_src = os.path.join(REPO_ROOT, "PES2027-data", "pak", "pc1000_mobile_ios.pak")
    if not os.path.exists(companion_src):
        companion_src = os.path.join(REPO_ROOT, "ziru-extra", "pak_extra", "pc8000_mobile_ios.pak")
    with open(pak_path, "wb") as f:
        f.write(open(companion_src, "rb").read())

    # Self-test: read every package back
    check_toc = p.Toc(utoc_path)
    for i, (cid_b, data, meta) in enumerate(chunks):
        assert check_toc.ids[i] == cid_b and check_toc.read(i) == data, f"Mismatch on chunk {i}"

    print(f"SUCCESS: {NAME} written to {OUT_DIR}")
    print(f"  Files: {len(paths)} packages")
    print(f"  UCAS: {os.path.getsize(ucas_path) / 1024:.1f} KB")
    print(f"  UTOC: {os.path.getsize(utoc_path) / 1024:.1f} KB")

if __name__ == "__main__":
    main()
