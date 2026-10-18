// C++ port of com.offline.server.OfflineServer (Ziru eFootball offline server, classes5.dex).
// Method names follow the original bytecode so behaviour can be diffed against the JVM oracle.
#pragma once
#include <fstream>
#include "zipread.hpp"
#include <sys/stat.h>
#include <dirent.h>

#include <algorithm>
#include <cstring>
#include <functional>
#include <cstdint>
#include <map>
#include <unordered_map>
#include <memory>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "codec.hpp"
#include "jvalue.hpp"
#include "store.hpp"
#include "ios_compat.hpp"

namespace zsv {
using namespace zj;
using Bytes = zc::Bytes;
using JStr = std::optional<std::string>;

struct NPE : std::runtime_error { NPE() : std::runtime_error("java.lang.NullPointerException") {} };
struct IOEx : std::runtime_error { explicit IOEx(const std::string& m) : std::runtime_error(m) {} };
struct IllegalArg : std::runtime_error { explicit IllegalArg(const std::string& m) : std::runtime_error(m) {} };
struct IllegalState : std::runtime_error { explicit IllegalState(const std::string& m) : std::runtime_error(m) {} };
struct NumberFormat : std::runtime_error { explicit NumberFormat(const std::string& m) : std::runtime_error(m) {} };

template <class T>
inline const std::shared_ptr<T>& nn(const std::shared_ptr<T>& p) { if (!p) throw NPE(); return p; }
inline const std::string& nn(const JStr& s) { if (!s) throw NPE(); return *s; }

// Java helpers
int32_t parseInt(const std::string& s);                // Integer.parseInt / valueOf
int64_t parseLong(const std::string& s);               // Long.parseLong
std::vector<std::string> split(const std::string& s, char sep);  // String.split(",")
inline bool contains(const std::string& s, const std::string& sub) { return s.find(sub) != std::string::npos; }
inline bool startsWith(const std::string& s, const std::string& p) { return s.rfind(p, 0) == 0; }
inline bool endsWith(const std::string& s, const std::string& p) { return s.size() >= p.size() && s.compare(s.size() - p.size(), p.size(), p) == 0; }
std::string replaceAll(std::string s, const std::string& from, const std::string& to);  // String.replace(CharSequence,..)
std::string toUpperUS(std::string s);
std::string str(const Value& v);         // String.valueOf(Object)
inline std::string str(int64_t v) { return std::to_string(v); }
inline std::string str(int32_t v) { return std::to_string(v); }
inline std::string str(const ObjP& o) { return o ? o->toString() : "null"; }
inline std::string str(const ArrP& a) { return a ? a->toString() : "null"; }
inline std::string str(const std::string& s) { return s; }
inline std::string str(const char* s) { return s; }
inline std::string str(bool b) { return b ? "true" : "false"; }

struct Request {
  std::string method = "POST";
  std::string uri;                          // NanoHTTPD getUri(): path, decoded, no query
  std::map<std::string, std::string> headers;  // lower-case keys
  Bytes body;
  size_t readPos = 0;                       // getInputStream() consumption
  size_t read(uint8_t* out, size_t n);      // InputStream.read semantics (0 = EOF)
};

struct Response {
  int status = 200;
  std::string mime = "application/x-msgpack";
  Bytes body;
  std::map<std::string, std::string> headers;
};

struct Config {
  std::string assetsDir;    // contains responses/, livedata/
  std::string livedataDir;  // optional separate livedata root (imported data pack)
  std::string livedataBaseUrl = "https://127.0.0.1:8085/livedata/";
  std::string dataDir;      // ziru_save.db, prefs, Download/
  std::string logFile;      // offline_server.log ("" = disabled)
  bool dropAndroidLivedata = false;
  bool iosPlayerLayout = false;  // 11.1.1 wire parameters; saves remain in Ziru format
  std::string downloadDir;   // where the game keeps downloaded files (commentary); "" = dataDir + "/Download"
  bool iosCommentary = false;  // commentary list from the installed file: real size/SHA-256, or empty when absent  // iOS: Ziru's livedata are Android paks (*_mobile_and.pak) the iOS client cannot apply
};

#include "appearance_presets_gen.inc"
#include "known_teams_gen.inc"

class OfflineServer {
 public:
  explicit OfflineServer(const Config& cfg);
  Response serve(Request& r);          // synchronized in Java
  static std::string redirectUrl(const std::string& url);
  // Ziru startServer() side effects that do not need NanoHTTPD
  void startupAudit();

  Config cfg;
  zs::Assets assets;
  std::unique_ptr<zs::ZiruDb> ziruDb;
  std::map<std::string, std::unique_ptr<zs::Prefs>> prefs;
  std::recursive_mutex mu;

  zs::Prefs& sp(const std::string& name);

  // ---- fields (same names as Java) ----
  int32_t ziruAbilityId = 0;
  int32_t ziruCareerOverall = 0;
  ArrP ziruCareerParameters;
  int64_t ziruCareerPlayerId = 0;
  ObjP ziruCareerProgression;
  int64_t ziruCareerRqid = 0;
  int64_t ziruCareerSerial = 0;
  int32_t ziruCareerSpent = 0;
  bool ziruIsAuto = false;
  JStr ziruItemType;
  int64_t ziruLastAgentId = 0;
  int32_t ziruLastCount = 0;
  std::optional<Bytes> ziruLastRequestBody;
  int32_t ziruLevelEffect = 0;
  int64_t ziruPlayerDataId = 0;
  int64_t ziruPlayerDataRqid = 0;
  int64_t ziruPlayerDataSerial = 0;
  ObjP ziruPlayerRecordsCache;
  JStr ziruSkillCategory;
  int32_t ziruSkillCategoryCode = 0;
  int32_t ziruSkillItemEffect = 0;
  int32_t ziruSkillItemGrade = 0;
  int64_t ziruSquadRqid = 0;
  int64_t ziruTargetPlayerId = 0;
  int64_t ziruTargetSerial = 0;
  int32_t ziruTrainingIndex = 0;

  // ---- helpers for Android APIs ----
  std::string readAsset(const std::string& name);      // throws IOEx
  Response newFixed(int status, const std::string& mime, Bytes body);
  Response newFixedText(int status, const std::string& text);
  Bytes encodeClientResponse(const Value& value) {
    if (!cfg.iosPlayerLayout) return zc::encodeResponse(value);
    Value wire = value;
    if (value.t == Value::OBJ) wire = Value(Object::parse(value.o->toString()));
    else if (value.t == Value::ARR) wire = Value(Array::parse(value.a->toString()));
    adaptIosPlayerData(wire, true);
    return zc::encodeResponse(wire);
  }
  void logRequest(const std::string& a, const std::string& b);
  static JStr dbLoad(bool ok, std::string& s) { if (ok) return s; return std::nullopt; }
  JStr loadMeta(const std::string& k) { std::string s; return dbLoad(ziruDb->loadMeta(k, s), s); }
  JStr loadPlayer(int64_t serial) { std::string s; return dbLoad(ziruDb->loadPlayer(serial, s), s); }
  JStr loadProgression(int64_t serial) { std::string s; return dbLoad(ziruDb->loadProgression(serial, s), s); }
  JStr loadSquad(int32_t id) { std::string s; return dbLoad(ziruDb->loadSquad(id, s), s); }
  void saveSquad(int32_t id, const std::string& s) { ziruDb->saveSquad(id, s); }

  static int64_t z27RestorePlayerId(const ObjP& cur, int64_t currentId, int64_t serial = 0, int64_t templatePid = 0) {
    int32_t bid = (int32_t)(currentId & 0xFFFFFF);
    if (currentId > 0xFFFFFF) return currentId;
    if (templatePid > 0xFFFFFF && (templatePid & 0xFFFFFF) == bid) return templatePid;

    if (bid == 40352) {
      if (serial == 359042717000000364LL || serial == 359042717000000400LL) return 106652627934624LL;
      if (serial == 359042717000000430LL || serial == 359042717000000450LL) return 105627472928160LL;
      if (serial == 359042717000000537LL || serial == 359042717000000500LL) return 88029918174624LL;

      if (cur) {
        ArrP params = cur->optJSONArray("parameters");
        if (!params) {
          ObjP gp = cur->optJSONObject("gameplayer");
          if (gp) params = gp->optJSONArray("parameters");
        }
        int h = (params && params->length() > 47) ? params->optInt(47, 0) : 0;
        int p0 = (params && params->length() > 0) ? params->optInt(0, 0) : 0;
        int tid = cur->optInt("initial_base_team_id", cur->optInt("team_id", 0));
        if (!tid) {
          ObjP gp = cur->optJSONObject("gameplayer");
          if (gp) tid = gp->optInt("initial_base_team_id", gp->optInt("team_id", 0));
        }
        if (h == 180 || (tid == 108 && p0 == 11 && cur->optInt("uniform_number", 0) == 9)) {
          return 17592454614507LL;
        }

        ArrP ib = cur->optJSONArray("initial_booster_id_list");
        if (!ib) {
          ObjP gp = cur->optJSONObject("gameplayer");
          if (gp) ib = gp->optJSONArray("initial_booster_id_list");
        }
        int b0 = ib ? ib->optInt(0, 0) : 0;
        int b1 = ib ? ib->optInt(1, 0) : 0;

        if (b0 == 194 && b1 == 504) return 106788187839904LL; // Epic
        if (b0 == 31 && b1 == 136)  return 88044145253792LL;  // Showtime
        if (b0 == 17 && b1 == 0)    return 88029918174624LL;  // Santos CF
        if (b0 == 144 && b1 == 136) return 89133993205152LL;
        if (b0 == 188 && b1 == 136) return 106770471099808LL;
        if (b0 == 27 && b1 == 136)  return 88039044980128LL;
        if (b0 == 170 && b1 == 136) return 106755438714272LL;
        if (b0 == 20 && b1 == 136)  return 88033139400096LL;
        if (b0 == 17 && b1 == 136)  return 88032870964640LL;
        if (b0 == 16 && b1 == 0)    return 88030723480992LL;

        if (tid == 108) return 89071179308448LL;
        if (tid == 1254) return 88029918174624LL;

        ObjP li = cur->optJSONObject("level_info");
        if (!li) {
          ObjP gp = cur->optJSONObject("gameplayer");
          if (gp) li = gp->optJSONObject("level_info");
        }
        int ll = li ? li->optInt("level_limit", 0) : 0;
        if (ll == 21 || p0 == 11) return 106652627934624LL;
        if (ll == 19) return 89061784067488LL;
        if (ll == 34) return 106788187839904LL;
        if (ll == 36) return 88029918174624LL;
        if (ll == 31) return 88044145253792LL;
      }
      return 88029918174624LL;
    }

    if (bid == 44379) {
      if (serial == 359042717000000534LL) return 105639552527707LL;
      if (cur) {
        ArrP ib = cur->optJSONArray("initial_booster_id_list");
        if (!ib) {
          ObjP gp = cur->optJSONObject("gameplayer");
          if (gp) ib = gp->optJSONArray("initial_booster_id_list");
        }
        int b0 = ib ? ib->optInt(0, 0) : 0;
        int b1 = ib ? ib->optInt(1, 0) : 0;
        if (b0 == 186 && b1 == 506) return 106788187843931LL;
        if (b0 == 26 && b1 == 136)  return 106766981442907LL;
        if (b0 == 147 && b1 == 136) return 106743090687323LL;
        ObjP li = cur->optJSONObject("level_info");
        if (!li) {
          ObjP gp = cur->optJSONObject("gameplayer");
          if (gp) li = gp->optJSONObject("level_info");
        }
        int ll = li ? li->optInt("level_limit", 0) : 0;
        if (ll == 28) return 106655312293211LL;
      }
      return 106788187843931LL;
    }

    return currentId;
  }

#include "srv_myclub.inc"
#include "srv_league.inc"
#include "srv_myleague.inc"
#include "srv_part4.inc"
#include "srv_part5.inc"
#include "srv_part6.inc"
#include "srv_z27.inc"
#include "srv_serve.inc"
};

}  // namespace zsv
