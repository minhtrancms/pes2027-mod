// Native name-atlas fallback and jersey rendering, PESmobile 11.1.101 only.
#include <atomic>
#include <mutex>
#include <set>
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

static LoadFn originalLoad;
static ReadyFn originalReady;
static DrawFn originalDraw;
static AssetFn originalAsset;
static SetUniformNumberFn originalSetUniformNumber;
static SetupFromPlayerIdFn originalSetupFromPlayerId;

static std::mutex mutex;
static std::set<void*> retried;
static void asset(void* actor, NativeString* name, bool edit) { originalAsset(actor, name, edit); }
static intptr_t gSlide = 0;

static void load(void* actor) {
  originalLoad(actor);
}

static bool ready(void* actor) {
  if (!originalReady(actor)) return false;
  auto p = (uint8_t*)actor;
  if (!*(void**)(p + 0x2b0)) {
    const uint8_t* s = p + 0x278;
    bool heap = (int8_t)s[23] < 0;
    uint64_t len = heap ? ((const uint64_t*)s)[1] : s[23];
    if (len > 0) {
      bool retry = false;
      {
        std::lock_guard<std::mutex> guard(mutex);
        if (retried.insert(actor).second) retry = true;
      }
      if (retry) {
        static char16_t fallback[] = u"T_EditUni_FontName_00_D";
        NativeString sStr{fallback, (int32_t)(sizeof(fallback) / sizeof(fallback[0])), (int32_t)(sizeof(fallback) / sizeof(fallback[0]))};
        originalAsset(actor, &sStr, true);
        originalLoad(actor);
        return false;
      }
    }
  }
  return true;
}

static void draw(void* actor, void* canvas) {
  originalDraw(actor, canvas);
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

// Executed strictly ONCE upon player actor construction / uniform setup.
// Never called per-frame or inside render ticks.
static void setActorShirtNameOnce(void* actor, int64_t playerId, intptr_t slide) {
  if (!actor) return;

  const char* pName = nullptr;
  if (playerId == 9901397) pName = "ZIDANE";
  else if (playerId == 37576) pName = "RONALDO";
  else if (playerId == 40291) pName = "ÖZIL";
  else if (playerId > 0) {
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
  *(uint8_t*)((uint8_t*)actor + 0x1aaf) = 1;

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
  if (originalSetupFromPlayerId) {
    originalSetupFromPlayerId(actor, playerId, path, uniformIndex, uniName);
  }
  setActorShirtNameOnce(actor, playerId, gSlide);
}

static std::atomic<int> numberLogBudget{10};
static void nativeSetUniformNumber(void* actor, int requested) {
  if (originalSetUniformNumber) originalSetUniformNumber(actor, requested);
  if (!actor) return;
  int actual = *(int32_t*)((uint8_t*)actor + 0x1708);
  if (actual > 0 && actual <= 99) {
    *(uint8_t*)((uint8_t*)actor + 0xf10) = 1;
    *(uint8_t*)((uint8_t*)actor + 0x1aaf) = 1;
  }
}

static void install() {
  intptr_t slide = 0; bool found = false;
  for (uint32_t i = 0; i < _dyld_image_count(); ++i) if (_dyld_get_image_header(i)->filetype == MH_EXECUTE) {
    slide = _dyld_get_image_vmaddr_slide(i); found = true; break;
  }
  if (!found) return;
  gSlide = slide;

  // 1. Hook SetupFromPlayerId at slot 0x106f2dd18 (executed strictly ONCE at actor init, NEVER in match tick)
  const uintptr_t setupSlot = 0x106f2dd18;
  const uintptr_t expectedSetup = 0x1008a02f0;
  if (*(uintptr_t*)(setupSlot + slide) == expectedSetup + slide) {
    vm_address_t actorPage = (setupSlot + slide) & ~(vm_address_t)(vm_page_size - 1);
    if (vm_protect(mach_task_self(), actorPage, vm_page_size, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) == KERN_SUCCESS) {
      originalSetupFromPlayerId = (SetupFromPlayerIdFn)*(uintptr_t*)(setupSlot + slide);
      *(uintptr_t*)(setupSlot + slide) = (uintptr_t)hookedSetupFromPlayerId;
      vm_protect(mach_task_self(), actorPage, vm_page_size, false, VM_PROT_READ);
      ZLog(@"[JERSEY] single-shot actor shirt name hook installed successfully");
    }
  }

  // 2. Install atlas fallback hooks (without per-frame cache invalidation or locks)
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

  // 3. SetUniformNumber hook (lightweight flag activation)
  originalSetUniformNumber = (SetUniformNumberFn)(0x10089f2e8 + slide);
  for (uintptr_t slot : {0x105f286c0ULL, 0x105f29098ULL}) {
    if (*(uintptr_t*)(slot + slide) != (uintptr_t)originalSetUniformNumber) {
      continue;
    }
    vm_address_t p = (slot + slide) & ~(vm_address_t)(vm_page_size - 1);
    if (vm_protect(mach_task_self(), p, vm_page_size, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) == KERN_SUCCESS) {
      *(uintptr_t*)(slot + slide) = (uintptr_t)nativeSetUniformNumber;
      vm_protect(mach_task_self(), p, vm_page_size, false, VM_PROT_READ);
    }
  }
  ZLog(@"[JERSEY_NATIVE] jersey name & uniform number hooks active (zero match overhead)");
}
}
