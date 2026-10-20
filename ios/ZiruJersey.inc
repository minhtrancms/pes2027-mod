// Native name-atlas fallback and jersey rendering, PESmobile 11.1.101 only.
#include <atomic>
#include <mutex>
#include <set>
#include <map>
#include <string>
#include <mach-o/dyld.h>
#include <mach/mach.h>

namespace zjersey {
using LoadFn = void (*)(void*);
using ReadyFn = bool (*)(void*);
using DrawFn = void (*)(void*, void*);
struct NativeString { char16_t* data; int32_t num; int32_t max; };
using AssetFn = void (*)(void*, NativeString*, bool);
using SetUniformNumberFn = void (*)(void* actor, int uniformNumber);
using SetupFromPlayerIdFn = void (*)(void* actor, int64_t playerId, void* path, int uniformIndex, void* uniName);
using SetupBackNumberAndNameFn = void (*)(void* actor);

static LoadFn originalLoad;
static ReadyFn originalReady;
static DrawFn originalDraw;
static AssetFn originalAsset;
static SetUniformNumberFn originalSetUniformNumber;
static SetupFromPlayerIdFn originalSetupFromPlayerId;
static SetupBackNumberAndNameFn originalSetupBackNumberAndName;

static std::mutex mutex;
static std::set<void*> retried, recorded;
static std::map<void*, int64_t> gActorPlayerId;
static int logBudget = 96;
static void asset(void* actor, NativeString* name, bool edit) { originalAsset(actor, name, edit); }
static intptr_t gSlide = 0;

static NSString* nameText(void* actor) {
  const uint8_t* s = (const uint8_t*)actor + 0x278;
  bool heap = (int8_t)s[23] < 0;
  uint64_t length = heap ? ((const uint64_t*)s)[1] : s[23];
  const char* text = heap ? *(const char**)s : (const char*)s;
  if (!text || length > 120) return @"<invalid>";
  return [[NSString alloc] initWithBytes:text length:(NSUInteger)length encoding:NSUTF8StringEncoding] ?: @"<invalid UTF-8>";
}

static NSString* assetText(void* actor) {
  auto s = (NativeString*)((uint8_t*)actor + 0x2c0);
  if (!s->data || s->num < 2 || s->num > 512) return @"<empty>";
  return [[NSString alloc] initWithCharacters:(const unichar*)s->data length:s->num - 1];
}

static void load(void* actor) {
  {
    std::lock_guard<std::mutex> guard(mutex);
    retried.erase(actor); recorded.erase(actor);
    if (logBudget > 0) {
      --logBudget;
      ZLog(@"[JERSEY] request name='%@' atlas=%@ scale=%.4f", nameText(actor), assetText(actor), *(float*)((uint8_t*)actor + 0x298));
    }
  }
  originalLoad(actor);
}

static bool ready(void* actor) {
  if (actor) *(uint8_t*)((uint8_t*)actor + 0x290) = 0;
  if (!originalReady(actor)) return false;
  auto p = (uint8_t*)actor;
  bool retry = false;
  if (!*(void**)(p + 0x2b0) && nameText(actor).length > 0) {
    std::lock_guard<std::mutex> guard(mutex);
    if (retried.insert(actor).second) retry = true;
  }
  if (retry) {
    ZLog(@"[JERSEY] missing atlas %@; retry stock iOS name atlas", assetText(actor));
    static char16_t fallback[] = u"T_EditUni_FontName_00_D";
    NativeString s{fallback, (int32_t)(sizeof(fallback) / sizeof(fallback[0])), (int32_t)(sizeof(fallback) / sizeof(fallback[0]))};
    originalAsset(actor, &s, true);
    originalLoad(actor);
    return false;
  }
  return true;
}

static void draw(void* actor, void* canvas) {
  {
    std::lock_guard<std::mutex> guard(mutex);
    if (recorded.insert(actor).second && logBudget > 0) {
      --logBudget;
      ZLog(@"[JERSEY] draw name='%@' atlas=%@ texture=%p scale=%.4f", nameText(actor), assetText(actor),
          *(void**)((uint8_t*)actor + 0x2b0), *(float*)((uint8_t*)actor + 0x298));
    }
  }
  if (actor) *(uint8_t*)((uint8_t*)actor + 0x290) = 0;
  originalDraw(actor, canvas);
}

static NSString* actorName(void* actor) {
  if (!actor) return @"<null>";
  const uint8_t* s = (const uint8_t*)actor + 0x1710;
  bool heap = (int8_t)s[23] < 0;
  uint64_t length = heap ? ((const uint64_t*)s)[1] : s[23];
  const char* text = heap ? *(const char**)s : (const char*)s;
  if (!text || length > 120) return @"<invalid>";
  return [[NSString alloc] initWithBytes:text length:(NSUInteger)length encoding:NSUTF8StringEncoding] ?: @"<invalid UTF-8>";
}

static const char* lookupPlayerShirtName(int64_t playerId, intptr_t slide) {
  if (playerId <= 0) return nullptr;
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
        if (name && name[0]) return name;
      }
    }
  }
  return nullptr;
}

static void setActorShirtName(void* actor, int64_t playerId, intptr_t slide) {
  if (!actor) return;

  const char* pName = nullptr;
  if (playerId > 0) {
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

  // Enable all Name & LoD flags on actor
  uint8_t* p = (uint8_t*)actor + 0x1000;
  p[0xaa7] = 1;
  p[0xaaa] = 1;
  p[0xaab] = 1;
  p[0xaaf] = 1;
  *(uint8_t*)((uint8_t*)actor + 0xf10) = 1;

  // Ensure Scale X, Scale Y, and Font Scale are non-zero (default 1.0f)
  if (*(float*)((uint8_t*)actor + 0xf38) <= 0.01f) *(float*)((uint8_t*)actor + 0xf38) = 1.0f;
  if (*(float*)((uint8_t*)actor + 0xf3c) <= 0.01f) *(float*)((uint8_t*)actor + 0xf3c) = 1.0f;
  if (*(float*)((uint8_t*)actor + 0xf40) <= 0.01f) *(float*)((uint8_t*)actor + 0xf40) = 1.0f;

  if (pName && pName[0]) {
    auto setShirt = (void (*)(void*, const char*))(0x10090ef34 + slide);
    if (setShirt) {
      std::string upper;
      for (const char* cp = pName; *cp; ++cp) upper += (char)toupper((unsigned char)*cp);
      setShirt(actor, upper.c_str());
      int uni = *(int32_t*)((uint8_t*)actor + 0x1708);
      ZLog(@"[JERSEY] Set shirt name for actor %p (player %lld, uni %d) -> '%s'",
           actor, (long long)playerId, uni, upper.c_str());
    }
  }

  void* nameTexActor = *(void**)((uint8_t*)actor + 0x1918);
  if (nameTexActor) {
    auto setNameFn = (void (*)(void*, void*))(0x100851098 + slide);
    if (setNameFn) setNameFn(nameTexActor, (uint8_t*)actor + 0x1710);
    if (*(float*)((uint8_t*)nameTexActor + 0x298) <= 0.01f) {
      *(float*)((uint8_t*)nameTexActor + 0x298) = 1.0f;
    }
  }
}

static void hookedSetupFromPlayerId(void* actor, int64_t playerId, void* path, int uniformIndex, void* uniName) {
  if (actor && playerId > 0) {
    std::lock_guard<std::mutex> guard(mutex);
    gActorPlayerId[actor] = playerId;
  }
  setActorShirtName(actor, playerId, gSlide);
  if (originalSetupFromPlayerId) {
    originalSetupFromPlayerId(actor, playerId, path, uniformIndex, uniName);
  }
  setActorShirtName(actor, playerId, gSlide);
}

static void hookedSetupBackNumberAndName(void* actor) {
  if (originalSetupBackNumberAndName) {
    originalSetupBackNumberAndName(actor);
  }
  if (!actor) return;
  int64_t playerId = 0;
  {
    std::lock_guard<std::mutex> guard(mutex);
    auto it = gActorPlayerId.find(actor);
    if (it != gActorPlayerId.end()) playerId = it->second;
  }
  setActorShirtName(actor, playerId, gSlide);

  uint8_t* p = (uint8_t*)actor + 0x1000;
  p[0xaa7] = 1;
  p[0xaaa] = 1;
  p[0xaab] = 1;
  p[0xaaf] = 1;
  *(uint8_t*)((uint8_t*)actor + 0xf10) = 1;
}

static std::atomic<int> numberLogBudget{96};
static void nativeSetUniformNumber(void* actor, int requested) {
  if (originalSetUniformNumber) originalSetUniformNumber(actor, requested);
  if (!actor) return;
  int actual = *(int32_t*)((uint8_t*)actor + 0x1708);
  if (actual > 0 && actual <= 99) {
    *(uint8_t*)((uint8_t*)actor + 0xf10) = 1;
    *(uint8_t*)((uint8_t*)actor + 0x1aaf) = 1;
  }
  int remaining = numberLogBudget.load(std::memory_order_relaxed);
  while (remaining > 0 && !numberLogBudget.compare_exchange_weak(remaining, remaining - 1, std::memory_order_relaxed)) {}
  if (remaining > 0) {
    ZLog(@"[JERSEY_NATIVE] actor=%p requested=%d stored=%d name='%@' model=%d state=%d",
         actor, requested, actual, actorName(actor),
         *(int32_t*)((uint8_t*)actor + 0x10b8), *(int32_t*)((uint8_t*)actor + 0x1920));
  }
}

static void install() {
  intptr_t slide = 0; bool found = false;
  for (uint32_t i = 0; i < _dyld_image_count(); ++i) if (_dyld_get_image_header(i)->filetype == MH_EXECUTE) {
    slide = _dyld_get_image_vmaddr_slide(i); found = true; break;
  }
  if (!found) return;
  gSlide = slide;

  // 1. Install player actor shirt name & number hooks at verified slots 0x106f2dd08 & 0x106f2dd18
  const uintptr_t actorSlots[] = {0x106f2dd08, 0x106f2dd18};
  const uintptr_t actorFuncs[] = {0x10089f3ec, 0x1008a02f0};
  bool actorVtableMatch = true;
  for (int i = 0; i < 2; ++i) {
    if (*(uintptr_t*)(actorSlots[i] + slide) != actorFuncs[i] + slide) {
      actorVtableMatch = false; break;
    }
  }
  if (actorVtableMatch) {
    vm_address_t actorPage = (actorSlots[0] + slide) & ~(vm_address_t)(vm_page_size - 1);
    vm_size_t actorLength = ((actorSlots[1] + slide + 8 - actorPage + vm_page_size - 1) & ~(vm_page_size - 1));
    if (vm_protect(mach_task_self(), actorPage, actorLength, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) == KERN_SUCCESS) {
      originalSetupBackNumberAndName = (SetupBackNumberAndNameFn)*(uintptr_t*)(actorSlots[0] + slide);
      originalSetupFromPlayerId = (SetupFromPlayerIdFn)*(uintptr_t*)(actorSlots[1] + slide);
      *(uintptr_t*)(actorSlots[0] + slide) = (uintptr_t)hookedSetupBackNumberAndName;
      *(uintptr_t*)(actorSlots[1] + slide) = (uintptr_t)hookedSetupFromPlayerId;
      vm_protect(mach_task_self(), actorPage, actorLength, false, VM_PROT_READ);
      ZLog(@"[JERSEY] player actor shirt name hooks installed successfully");
    } else {
      ZLog(@"[JERSEY] vm_protect failed for player actor vtable");
    }
  } else {
    ZLog(@"[JERSEY] player actor vtable mismatch; name injection skipped");
  }

  // 2. Install atlas fallback hooks
  const uintptr_t slots[] = {0x105f177f8, 0x105f17800, 0x105f17808, 0x105f17818};
  const uintptr_t functions[] = {0x100851490, 0x100851894, 0x1008518c0, 0x1008511c8};
  for (int i = 0; i < 4; ++i) if (*(uintptr_t*)(slots[i] + slide) != functions[i] + slide) {
    ZLog(@"[JERSEY] unsupported native vtable; hooks disabled"); return;
  }
  vm_address_t page = (slots[0] + slide) & ~(vm_address_t)(vm_page_size - 1);
  vm_size_t length = slots[3] + slide + 8 - page;
  if (vm_protect(mach_task_self(), page, length, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) != KERN_SUCCESS) {
    ZLog(@"[JERSEY] vtable protection failed; hooks disabled"); return;
  }
  originalLoad = (LoadFn)*(uintptr_t*)(slots[0] + slide);
  originalReady = (ReadyFn)*(uintptr_t*)(slots[1] + slide);
  originalDraw = (DrawFn)*(uintptr_t*)(slots[2] + slide);
  originalAsset = (AssetFn)*(uintptr_t*)(slots[3] + slide);
  *(uintptr_t*)(slots[0] + slide) = (uintptr_t)load;
  *(uintptr_t*)(slots[1] + slide) = (uintptr_t)ready;
  *(uintptr_t*)(slots[2] + slide) = (uintptr_t)draw;
  *(uintptr_t*)(slots[3] + slide) = (uintptr_t)asset;
  vm_protect(mach_task_self(), page, length, false, VM_PROT_READ);

  // 3. SetUniformNumber hook
  originalSetUniformNumber = (SetUniformNumberFn)(0x10089f2e8 + slide);
  for (uintptr_t slot : {0x105f286c0ULL, 0x105f29098ULL}) {
    if (*(uintptr_t*)(slot + slide) != (uintptr_t)originalSetUniformNumber) {
      ZLog(@"[JERSEY] native number vtable mismatch; leave unchanged"); continue;
    }
    vm_address_t p = (slot + slide) & ~(vm_address_t)(vm_page_size - 1);
    if (vm_protect(mach_task_self(), p, vm_page_size, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) == KERN_SUCCESS) {
      *(uintptr_t*)(slot + slide) = (uintptr_t)nativeSetUniformNumber;
      vm_protect(mach_task_self(), p, vm_page_size, false, VM_PROT_READ);
    }
  }
  ZLog(@"[JERSEY_NATIVE] jersey name & uniform number hooks active");
}
}
