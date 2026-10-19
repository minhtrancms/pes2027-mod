// Native name-atlas fallback, PESmobile 11.1.101 only. These data vtable slots
// are validated before writing; no executable page is modified at runtime.
namespace zjersey {
using LoadFn = void (*)(void*);
using ReadyFn = bool (*)(void*);
using DrawFn = void (*)(void*, void*);
struct NativeString { char16_t* data; int32_t num; int32_t max; };
using AssetFn = void (*)(void*, NativeString*, bool);
using SetupFromPlayerIdFn = void (*)(void* actor, int64_t playerId, void* path, int uniformIndex, void* uniName);
using SetupBackNumberAndNameFn = void (*)(void* actor);

static LoadFn originalLoad;
static ReadyFn originalReady;
static DrawFn originalDraw;
static AssetFn originalAsset;
static SetupFromPlayerIdFn originalSetupFromPlayerId;
static SetupBackNumberAndNameFn originalSetupBackNumberAndName;

static std::mutex mutex;
static std::set<void*> retried, recorded;
static int logBudget = 96;
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
  if (!originalReady(actor)) return false;
  auto p = (uint8_t*)actor;
  // A completed async load with a null primary atlas produces a blank canvas.
  // Retry once with the stock iOS atlas verified in pc0103's directory index.
  // Existing and custom successfully loaded atlases always remain in use.
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
  originalDraw(actor, canvas);
}

static bool isBlankString(const char* s) {
  if (!s || !s[0]) return true;
  for (const char* p = s; *p; ++p) {
    if (!isspace((unsigned char)*p)) return false;
  }
  return true;
}

static std::string formatShirtNameTitleCase(const char* pName) {
  if (!pName || !pName[0]) return "";
  NSString* raw = [NSString stringWithUTF8String:pName];
  if (!raw) return pName;
  NSString* title = [raw capitalizedStringWithLocale:[NSLocale localeWithLocaleIdentifier:@"en_US"]];
  if (!title) return pName;
  NSMutableString* res = [NSMutableString stringWithString:title];
  NSRegularExpression* regex = [NSRegularExpression regularExpressionWithPattern:@"'([a-z])" options:0 error:nil];
  if (regex) {
    NSArray* matches = [regex matchesInString:res options:0 range:NSMakeRange(0, res.length)];
    for (NSTextCheckingResult* m in [matches reverseObjectEnumerator]) {
      NSRange r = [m rangeAtIndex:1];
      NSString* ch = [[res substringWithRange:r] uppercaseString];
      [res replaceCharactersInRange:r withString:ch];
    }
  }
  return res.UTF8String ?: pName;
}

static std::map<void*, int64_t> gActorPlayerId;

static int extractTeamIdFromActor(void* actor) {
  if (!actor) return 0;
  // 1. Check actor + 0xe10 (uint32_t teamId set by SetTeamId)
  uint32_t tid = *(uint32_t*)((uint8_t*)actor + 0xe10);
  if (tid > 0 && tid < 1000000) return (int)tid;

  // 2. Parse uniform kit path at actor + 0x450 (FString containing e.g. u0108_p1)
  const void* rawPtr = *(const void**)((uint8_t*)actor + 0x450);
  int32_t len = *(int32_t*)((uint8_t*)actor + 0x458);
  if (rawPtr && len > 5 && len < 256) {
    NSString* s = [[NSString alloc] initWithCharacters:(const unichar*)rawPtr length:(NSUInteger)(len - 1)];
    if (!s) {
      s = [[NSString alloc] initWithBytes:rawPtr length:(NSUInteger)(len - 1) encoding:NSASCIIStringEncoding];
    }
    if (s) {
      NSRange r = [s rangeOfString:@"u[0-9]{4}" options:NSRegularExpressionSearch];
      if (r.location != NSNotFound && r.length == 5) {
        NSString* numStr = [s substringWithRange:NSMakeRange(r.location + 1, 4)];
        int parsed = [numStr intValue];
        if (parsed > 0) return parsed;
      }
    }
  }
  return 0;
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
        if (name && name[0] && !isBlankString(name)) {
          return name;
        }
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

  // Fallback: check if actor already has non-blank shirt name in std::string at 0x1710
  if (!pName || isBlankString(pName)) {
    const uint8_t* s = (const uint8_t*)actor + 0x1710;
    bool heap = (int8_t)s[23] < 0;
    uint64_t length = heap ? ((const uint64_t*)s)[1] : s[23];
    if (length > 0) {
      const char* text = heap ? *(const char**)s : (const char*)s;
      if (text && text[0] && !isBlankString(text)) pName = text;
    }
  }

  // Enable all Name & LoD flags on actor:
  // - actor + 0x1aaf: BackNumberStep Name LoD enable flag
  // - actor + 0x1aaa, 0x1aab, 0x1aa7: LoD & skeleton enable flags
  // - actor + 0xf10: SetUniformName material parameter visibility flag
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

  if (pName && !isBlankString(pName)) {
    auto setShirt = (void (*)(void*, const char*))(0x10090ef34 + slide);
    if (setShirt) {
      std::string formatted = formatShirtNameTitleCase(pName);
      setShirt(actor, formatted.c_str());
      int uni = *(int32_t*)((uint8_t*)actor + 0x1708);
      ZLog(@"[JERSEY] Set shirt name for actor %p (player %lld, uni %d) -> '%s'",
           actor, (long long)playerId, uni, formatted.c_str());
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
  if (!actor) {
    if (originalSetupBackNumberAndName) originalSetupBackNumberAndName(actor);
    return;
  }

  int64_t playerId = 0;
  {
    std::lock_guard<std::mutex> guard(mutex);
    auto it = gActorPlayerId.find(actor);
    if (it != gActorPlayerId.end()) playerId = it->second;
  }

  int32_t uniNum = *(int32_t*)((uint8_t*)actor + 0x1708);
  if (playerId <= 0 && uniNum > 0) {
    int teamId = extractTeamIdFromActor(actor);
    playerId = zjersey::resolveMatchPlayer(teamId, uniNum);
    if (playerId > 0) {
      std::lock_guard<std::mutex> guard(mutex);
      gActorPlayerId[actor] = playerId;
    }
  }

  // CRITICAL: Configure name string and LoD flags BEFORE Konami's BackNumberStep
  // state machine checks them in step 2 and step 4!
  setActorShirtName(actor, playerId, gSlide);

  if (originalSetupBackNumberAndName) {
    originalSetupBackNumberAndName(actor);
  }

  // Safety post-check: ensure flags remain active throughout the step
  uint8_t* p = (uint8_t*)actor + 0x1000;
  p[0xaa7] = 1;
  p[0xaaa] = 1;
  p[0xaab] = 1;
  p[0xaaf] = 1;
  *(uint8_t*)((uint8_t*)actor + 0xf10) = 1;
}

static void install() {
  intptr_t slide = 0; bool found = false;
  for (uint32_t i = 0; i < _dyld_image_count(); ++i) if (_dyld_get_image_header(i)->filetype == MH_EXECUTE) {
    slide = _dyld_get_image_vmaddr_slide(i); found = true; break;
  }
  if (!found) return;
  gSlide = slide;

  // 1. Install player actor hooks FIRST so actor name setting is never blocked
  // Verified vtable slots in __DATA_CONST:
  // - APlayerActorMobile: SetupFromPlayerId = 0x105f287a0, BackNumberStep = 0x105f28800
  // - APlayerActorMobileHigh: SetupFromPlayerId = 0x105f29178, BackNumberStep = 0x105f291d8
  // - AEfbxActorMobile: SetupFromPlayerId = 0x105f38778, BackNumberStep = 0x105f387d8
  struct ActorVtablePair {
    uintptr_t backNumSlot;
    uintptr_t setupSlot;
  };
  const ActorVtablePair actorVtables[] = {
    {0x105f28800, 0x105f287a0},
    {0x105f291d8, 0x105f29178},
    {0x105f387d8, 0x105f38778},
  };
  const uintptr_t expectedBackNum = 0x10089f3ec;
  const uintptr_t expectedSetup = 0x1008a02f0;
  int hookedCount = 0;
  size_t psize = (size_t)getpagesize();

  for (const auto& pair : actorVtables) {
    uintptr_t curBackNum = *(uintptr_t*)(pair.backNumSlot + slide);
    uintptr_t curSetup = *(uintptr_t*)(pair.setupSlot + slide);
    uintptr_t expBack = expectedBackNum + slide;
    uintptr_t expSetup = expectedSetup + slide;

    bool match = (curBackNum == expBack && curSetup == expSetup) ||
                 ((curBackNum & 0xFFFFFFULL) == (expectedBackNum & 0xFFFFFFULL) &&
                  (curSetup & 0xFFFFFFULL) == (expectedSetup & 0xFFFFFFULL)) ||
                 ((curBackNum & 0x7fffffffffULL) == (expBack & 0x7fffffffffULL) &&
                  (curSetup & 0x7fffffffffULL) == (expSetup & 0x7fffffffffULL));

    if (match) {
      uintptr_t minSlot = std::min(pair.backNumSlot, pair.setupSlot) + slide;
      uintptr_t maxSlot = std::max(pair.backNumSlot, pair.setupSlot) + slide;
      vm_address_t actorPage = minSlot & ~(vm_address_t)(psize - 1);
      vm_size_t actorLength = (((maxSlot + 8) + psize - 1) & ~(vm_address_t)(psize - 1)) - actorPage;

      kern_return_t kr = vm_protect(mach_task_self(), actorPage, actorLength, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY);
      if (kr != KERN_SUCCESS) {
        kr = vm_protect(mach_task_self(), actorPage, actorLength, false, VM_PROT_READ | VM_PROT_WRITE);
      }
      if (kr == KERN_SUCCESS) {
        if (!originalSetupBackNumberAndName) originalSetupBackNumberAndName = (SetupBackNumberAndNameFn)curBackNum;
        if (!originalSetupFromPlayerId) originalSetupFromPlayerId = (SetupFromPlayerIdFn)curSetup;
        *(uintptr_t*)(pair.backNumSlot + slide) = (uintptr_t)hookedSetupBackNumberAndName;
        *(uintptr_t*)(pair.setupSlot + slide) = (uintptr_t)hookedSetupFromPlayerId;
        vm_protect(mach_task_self(), actorPage, actorLength, false, VM_PROT_READ);
        hookedCount++;
      } else {
        ZLog(@"[JERSEY] vm_protect failed on %p (kr=%d)", (void*)actorPage, kr);
      }
    } else {
      ZLog(@"[JERSEY] pair slot=%p curBack=%p (exp=%p) curSetup=%p (exp=%p) mismatch",
           (void*)(pair.backNumSlot + slide), (void*)curBackNum, (void*)expBack,
           (void*)curSetup, (void*)expSetup);
    }
  }
  if (hookedCount > 0) {
    ZLog(@"[JERSEY] player actor shirt name hooks installed successfully on %d vtable(s)", hookedCount);
  } else {
    ZLog(@"[JERSEY] player actor vtable mismatch; name injection skipped");
  }

  // 2. Install atlas fallback hooks independently
  const uintptr_t slots[] = {0x105f177f8, 0x105f17800, 0x105f17808, 0x105f17818};
  const uintptr_t functions[] = {0x100851490, 0x100851894, 0x1008518c0, 0x1008511c8};
  bool atlasMatch = true;
  for (int i = 0; i < 4; ++i) {
    uintptr_t cur = *(uintptr_t*)(slots[i] + slide);
    uintptr_t exp = functions[i] + slide;
    if (cur != exp && ((cur & 0xFFFFFFULL) != (functions[i] & 0xFFFFFFULL)) &&
        ((cur & 0x7fffffffffULL) != (exp & 0x7fffffffffULL))) {
      atlasMatch = false; break;
    }
  }
  if (atlasMatch) {
    vm_address_t page = (slots[0] + slide) & ~(vm_address_t)(psize - 1);
    vm_size_t length = (((slots[3] + slide + 8) + psize - 1) & ~(vm_address_t)(psize - 1)) - page;
    kern_return_t kr = vm_protect(mach_task_self(), page, length, false, VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY);
    if (kr != KERN_SUCCESS) {
      kr = vm_protect(mach_task_self(), page, length, false, VM_PROT_READ | VM_PROT_WRITE);
    }
    if (kr == KERN_SUCCESS) {
      originalLoad = (LoadFn)*(uintptr_t*)(slots[0] + slide);
      originalReady = (ReadyFn)*(uintptr_t*)(slots[1] + slide);
      originalDraw = (DrawFn)*(uintptr_t*)(slots[2] + slide);
      originalAsset = (AssetFn)*(uintptr_t*)(slots[3] + slide);
      *(uintptr_t*)(slots[0] + slide) = (uintptr_t)load;
      *(uintptr_t*)(slots[1] + slide) = (uintptr_t)ready;
      *(uintptr_t*)(slots[2] + slide) = (uintptr_t)draw;
      vm_protect(mach_task_self(), page, length, false, VM_PROT_READ);
      ZLog(@"[JERSEY] native name atlas fallback and diagnostics installed");
    } else {
      ZLog(@"[JERSEY] vtable protection failed for atlas (kr=%d); fallback skipped", kr);
    }
  } else {
    ZLog(@"[JERSEY] atlas vtable mismatch; fallback skipped");
  }
}
}
