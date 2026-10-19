#pragma once
#include <cstdint>
#include <string>
#include <map>
#include <mutex>
#include <utility>

namespace zjersey {

inline std::mutex& registryMutex() {
  static std::mutex m;
  return m;
}

inline std::map<std::pair<int, int>, int64_t>& teamUniformMap() {
  static std::map<std::pair<int, int>, int64_t> m;
  return m;
}

inline std::map<std::pair<int, int>, int64_t>& sideUniformMap() {
  static std::map<std::pair<int, int>, int64_t> m;
  return m;
}

inline std::map<int, int64_t>& uniformMap() {
  static std::map<int, int64_t> m;
  return m;
}

inline int& homeTeamId() {
  static int h = 0;
  return h;
}

inline int& awayTeamId() {
  static int a = 0;
  return a;
}

inline void clearMatchPlayers() {
  std::lock_guard<std::mutex> g(registryMutex());
  teamUniformMap().clear();
  sideUniformMap().clear();
  uniformMap().clear();
  homeTeamId() = 0;
  awayTeamId() = 0;
}

inline void registerMatchPlayer(int side, int teamId, int uniformNumber, int64_t playerId) {
  std::lock_guard<std::mutex> g(registryMutex());
  if (side == 0 && teamId > 0) homeTeamId() = teamId;
  if (side == 1 && teamId > 0) awayTeamId() = teamId;

  if (teamId > 0 && uniformNumber > 0) {
    teamUniformMap()[{teamId, uniformNumber}] = playerId;
  }
  if (uniformNumber > 0) {
    sideUniformMap()[{side, uniformNumber}] = playerId;
    if (uniformMap().find(uniformNumber) == uniformMap().end() || side == 0) {
      uniformMap()[uniformNumber] = playerId;
    }
  }
}

inline int64_t resolveMatchPlayer(int teamId, int uniformNumber) {
  std::lock_guard<std::mutex> g(registryMutex());
  if (teamId > 0 && uniformNumber > 0) {
    auto it = teamUniformMap().find({teamId, uniformNumber});
    if (it != teamUniformMap().end()) return it->second;
    if (teamId == homeTeamId()) {
      auto it2 = sideUniformMap().find({0, uniformNumber});
      if (it2 != sideUniformMap().end()) return it2->second;
    } else if (teamId == awayTeamId()) {
      auto it2 = sideUniformMap().find({1, uniformNumber});
      if (it2 != sideUniformMap().end()) return it2->second;
    }
  }
  if (uniformNumber > 0) {
    auto it = uniformMap().find(uniformNumber);
    if (it != uniformMap().end()) return it->second;
  }
  return 0;
}

} // namespace zjersey
