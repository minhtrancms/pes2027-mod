// Native name and jersey rendering, PESmobile 11.1.101 only.
#include <atomic>
#include <mutex>
#include <set>
#include <string>
#include <unordered_map>
#include <mach-o/dyld.h>
#include <mach/mach.h>
#include <unistd.h>

namespace zjersey {
using SetUniformNumberFn = void (*)(void* actor, int uniformNumber);
using SetupFromPlayerIdFn = void (*)(void* actor, int64_t playerId, void* path, int uniformIndex, void* uniName);

static SetUniformNumberFn originalSetUniformNumber;
static SetupFromPlayerIdFn originalSetupFromPlayerId;
static intptr_t gSlide = 0;

static std::unordered_map<int64_t, std::string> gNameCache;
static std::mutex gCacheMu;

static const char* lookupPlayerShirtName(int64_t playerId, intptr_t slide) {
  if (playerId <= 0) return nullptr;
  {
    std::lock_guard<std::mutex> g(gCacheMu);
    auto it = gNameCache.find(playerId);
    if (it != gNameCache.end()) return it->second.c_str();
  }
  auto getMgr = (void* (*)())(0x104bba084 + slide);
  auto findRec = (void* (*)(void*, int, int64_t))(0x104b9588c + slide);
  auto getName = (const char* (*)(void*))(0x104bc2460 + slide);
  if (!getMgr || !findRec) return nullptr;

  void* mgr = getMgr();
  if (!mgr) return nullptr;

  const int64_t idsToTry[] = {
    playerId,
    (int64_t)(uint32_t)playerId,
    (int64_t)(playerId & 0xFFFFFFLL)
  };

  void* databases[] = {
    *(void**)((uint8_t*)mgr + 0x40),
    *(void**)((uint8_t*)mgr + 0x48),
    mgr
  };

  for (void* db : databases) {
    if (!db) continue;
    for (int64_t pid : idsToTry) {
      if (pid <= 0) continue;
      void* rec = findRec(db, 0, pid);
      if (rec) {
        const char* name = getName ? getName(rec) : nullptr;
        if (!name || !name[0]) {
          name = (const char*)((uint8_t*)rec + 0x89);
        }
        if (name && name[0]) {
          std::lock_guard<std::mutex> g(gCacheMu);
          gNameCache[playerId] = name;
          return gNameCache[playerId].c_str();
        }
      }
    }
  }
  return nullptr;
}

// Executed strictly ONCE upon player actor construction / uniform setup.
// Sets shirt name string without modifying actor internal LOD/material flags.
static void setActorShirtNameOnce(void* actor, int64_t playerId, intptr_t slide) {
  if (!actor || playerId <= 0) return;

  const char* pName = nullptr;
  if (playerId == 9901397) { pName = "ZIDANE"; }
  else if (playerId == 37576) { pName = "RONALDO"; }
  else if (playerId == 40291) { pName = "ÖZIL"; }
  else {
    pName = lookupPlayerShirtName(playerId, slide);
  }

  // Fallback: check if actor already has non-blank shirt name at 0x1710
  if (!pName || !pName[0]) {
    const uint8_t* s = (const uint8_t*)actor + 0x1710;
    bool heap = (int8_t)s[23] < 0;
    uint64_t length = heap ? ((const uint64_t*)s)[1] : s[23];
    if (length > 0) {
      const char* text = heap ? *(const char**)s : (const char*)s;
      if (text && text[0]) pName = text;
    }
  }

  if (pName && pName[0]) {
    auto setShirt = (void (*)(void*, const char*))(0x10090ef34 + slide);
    if (setShirt) {
      std::string upper;
      for (const char* cp = pName; *cp; ++cp) upper += (char)toupper((unsigned char)*cp);
      setShirt(actor, upper.c_str());
    }
  }
}

static void hookedSetupFromPlayerId(void* actor, int64_t playerId, void* path, int uniformIndex, void* uniName) {
  if (originalSetupFromPlayerId) {
    originalSetupFromPlayerId(actor, playerId, path, uniformIndex, uniName);
  }
  setActorShirtNameOnce(actor, playerId, gSlide);
}

static void install() {
  intptr_t slide = 0; bool found = false;
  for (uint32_t i = 0; i < _dyld_image_count(); ++i) if (_dyld_get_image_header(i)->filetype == MH_EXECUTE) {
    slide = _dyld_get_image_vmaddr_slide(i); found = true; break;
  }
  if (!found) return;
  gSlide = slide;
  size_t psize = (size_t)getpagesize();

  // Hook SetupFromPlayerId at real vtable slots (APlayerActorMobile & APlayerActorMobileHigh)
  // to ensure player shirt names (including custom legends) are populated cleanly.
  const uintptr_t setupSlots[] = {0x105f287a0ULL, 0x105f29178ULL};
  const uintptr_t expectedSetup = 0x1008a02f0ULL;
  for (uintptr_t slot : setupSlots) {
    uintptr_t cur = *(uintptr_t*)(slot + slide);
    uintptr_t unslid = (cur >= (uintptr_t)slide) ? (cur - (uintptr_t)slide) : cur;
    if (cur == expectedSetup + slide || (unslid & 0xFFFFFFULL) == (expectedSetup & 0xFFFFFFULL)) {
      vm_address_t page = (slot + slide) & ~(vm_address_t)(psize - 1);
      if (vm_protect(mach_task_self(), page, psize, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) == KERN_SUCCESS ||
          vm_protect(mach_task_self(), page, psize, false, VM_PROT_READ | VM_PROT_WRITE) == KERN_SUCCESS) {
        if (!originalSetupFromPlayerId) originalSetupFromPlayerId = (SetupFromPlayerIdFn)cur;
        *(uintptr_t*)(slot + slide) = (uintptr_t)hookedSetupFromPlayerId;
        vm_protect(mach_task_self(), page, psize, false, VM_PROT_READ);
      }
    }
  }
  ZLog(@"[JERSEY_NATIVE] jersey name hooks active (native uniform pipeline preserved)");
}
}

