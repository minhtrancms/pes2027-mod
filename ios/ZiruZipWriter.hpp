#pragma once
#include <cstdint>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include <zlib.h>

namespace zzip {

struct Entry {
  std::string nameInZip;
  std::string diskPath;
  std::vector<uint8_t> memoryData;
};

static inline uint16_t dosTime() {
  return (uint16_t)((12 << 11) | (0 << 5) | (0 >> 1));
}
static inline uint16_t dosDate() {
  return (uint16_t)(((2026 - 1980) << 9) | (10 << 5) | 21);
}

inline bool writeZip(const std::string& outPath, const std::vector<Entry>& entries) {
  std::ofstream out(outPath, std::ios::binary);
  if (!out) return false;

  struct CDRecord {
    std::string name;
    uint32_t crc = 0;
    uint32_t compSize = 0;
    uint32_t uncompSize = 0;
    uint32_t localOffset = 0;
    uint16_t method = 0;
  };
  std::vector<CDRecord> cds;

  for (const auto& e : entries) {
    std::vector<uint8_t> raw;
    if (!e.diskPath.empty()) {
      std::ifstream f(e.diskPath, std::ios::binary);
      if (!f) continue;
      raw.assign((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    } else {
      raw = e.memoryData;
    }

    CDRecord cd;
    cd.name = e.nameInZip;
    cd.uncompSize = (uint32_t)raw.size();
    cd.crc = (uint32_t)crc32(0L, raw.data(), (uInt)raw.size());
    cd.localOffset = (uint32_t)out.tellp();

    std::vector<uint8_t> comp;
    if (!raw.empty()) {
      z_stream zs;
      memset(&zs, 0, sizeof(zs));
      if (deflateInit2(&zs, Z_DEFAULT_COMPRESSION, Z_DEFLATED, -MAX_WBITS, 8, Z_DEFAULT_STRATEGY) == Z_OK) {
        comp.resize(raw.size() + 256);
        zs.next_in = (Bytef*)raw.data();
        zs.avail_in = (uInt)raw.size();
        zs.next_out = comp.data();
        zs.avail_out = (uInt)comp.size();
        deflate(&zs, Z_FINISH);
        comp.resize(zs.total_out);
        deflateEnd(&zs);
      }
    }

    if (!comp.empty() && comp.size() < raw.size()) {
      cd.method = 8; // Deflated
      cd.compSize = (uint32_t)comp.size();
    } else {
      cd.method = 0; // Stored
      cd.compSize = cd.uncompSize;
    }

    // Local Header (30 bytes)
    uint8_t lh[30];
    memset(lh, 0, sizeof(lh));
    lh[0] = 0x50; lh[1] = 0x4b; lh[2] = 0x03; lh[3] = 0x04;
    lh[4] = 20; lh[5] = 0;
    lh[6] = 0x00; lh[7] = 0x08; // UTF-8
    lh[8] = (uint8_t)(cd.method & 0xFF); lh[9] = (uint8_t)(cd.method >> 8);
    uint16_t dt = dosTime(), dd = dosDate();
    lh[10] = (uint8_t)(dt & 0xFF); lh[11] = (uint8_t)(dt >> 8);
    lh[12] = (uint8_t)(dd & 0xFF); lh[13] = (uint8_t)(dd >> 8);
    memcpy(&lh[14], &cd.crc, 4);
    memcpy(&lh[18], &cd.compSize, 4);
    memcpy(&lh[22], &cd.uncompSize, 4);
    uint16_t nlen = (uint16_t)cd.name.size();
    memcpy(&lh[26], &nlen, 2);

    out.write((char*)lh, 30);
    out.write(cd.name.data(), nlen);

    if (cd.method == 8) {
      out.write((char*)comp.data(), cd.compSize);
    } else if (cd.uncompSize > 0) {
      out.write((char*)raw.data(), cd.uncompSize);
    }
    cds.push_back(cd);
  }

  uint32_t cdStart = (uint32_t)out.tellp();
  for (const auto& cd : cds) {
    uint8_t cdh[46];
    memset(cdh, 0, sizeof(cdh));
    cdh[0] = 0x50; cdh[1] = 0x4b; cdh[2] = 0x01; cdh[3] = 0x02;
    cdh[4] = 20; cdh[5] = 3; // UNIX
    cdh[6] = 20; cdh[7] = 0;
    cdh[8] = 0x00; cdh[9] = 0x08; // UTF-8
    cdh[10] = (uint8_t)(cd.method & 0xFF); cdh[11] = (uint8_t)(cd.method >> 8);
    uint16_t dt = dosTime(), dd = dosDate();
    cdh[12] = (uint8_t)(dt & 0xFF); cdh[13] = (uint8_t)(dt >> 8);
    cdh[14] = (uint8_t)(dd & 0xFF); cdh[15] = (uint8_t)(dd >> 8);
    memcpy(&cdh[16], &cd.crc, 4);
    memcpy(&cdh[20], &cd.compSize, 4);
    memcpy(&cdh[24], &cd.uncompSize, 4);
    uint16_t nlen = (uint16_t)cd.name.size();
    memcpy(&cdh[28], &nlen, 2);
    uint32_t extAttr = 0644 << 16;
    memcpy(&cdh[38], &extAttr, 4);
    memcpy(&cdh[42], &cd.localOffset, 4);

    out.write((char*)cdh, 46);
    out.write(cd.name.data(), nlen);
  }

  uint32_t cdEnd = (uint32_t)out.tellp();
  uint32_t cdSize = cdEnd - cdStart;

  // EOCD (22 bytes)
  uint8_t eocd[22];
  memset(eocd, 0, sizeof(eocd));
  eocd[0] = 0x50; eocd[1] = 0x4b; eocd[2] = 0x05; eocd[3] = 0x06;
  uint16_t count = (uint16_t)cds.size();
  memcpy(&eocd[8], &count, 2);
  memcpy(&eocd[10], &count, 2);
  memcpy(&eocd[12], &cdSize, 4);
  memcpy(&eocd[16], &cdStart, 4);
  out.write((char*)eocd, 22);

  return true;
}

} // namespace zzip
