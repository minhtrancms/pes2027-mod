// In-game Mod & Cloud Database Manager for PES 2027
// Supports 6-digit Cloud Save sync with pes.minhgame.com, local file import/export, and stadium mods.

#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

#include "ZiruZipWriter.hpp"
#include "../core/zipread.hpp"

static NSString* const kCloudApiBase = @"https://pes.minhgame.com/api/save.php";
static NSString* const kCloudRecentCodesKey = @"pes2027_recent_save_codes";

@interface ZiruModVC : UIViewController <UIDocumentPickerDelegate, UITextFieldDelegate>
@property(nonatomic, strong) UISegmentedControl* tabs;
@property(nonatomic, strong) UIScrollView* scrollView;
@property(nonatomic, strong) UIView* cloudContainer;
@property(nonatomic, strong) UIView* localContainer;
@property(nonatomic, strong) UIView* modContainer;

// Cloud views
@property(nonatomic, strong) UIButton* btnCloudExport;
@property(nonatomic, strong) UITextField* txtCloudCode;
@property(nonatomic, strong) UIButton* btnCloudImport;
@property(nonatomic, strong) UILabel* lblRecentCodes;
@property(nonatomic, strong) UIActivityIndicatorView* spinner;
@property(nonatomic, strong) UILabel* lblCloudStatus;

// Local views
@property(nonatomic, strong) UIButton* btnLocalExport;
@property(nonatomic, strong) UIButton* btnLocalImport;
@property(nonatomic, strong) UILabel* lblLocalStatus;

// Mod views
@property(nonatomic, strong) UIButton* pickMod;
@property(nonatomic, strong) UITextView* inventory;

@end

static NSString* modInventory() {
  NSFileManager* fm = NSFileManager.defaultManager;
  NSMutableString* text = [NSMutableString stringWithString:@"Sân đã có đủ bộ file trên máy:\n"];
  NSString* dl = [gDocs stringByAppendingPathComponent:@"Download"];
  int count = 0;
  for (NSString* n in [[fm contentsOfDirectoryAtPath:dl error:nil] sortedArrayUsingSelector:@selector(compare:)]) {
    if (!zm::stadiumName(n.UTF8String) || ![n hasSuffix:@"_mobile_ios.pak"]) continue;
    NSString* stem = n.stringByDeletingPathExtension;
    BOOL complete = YES;
    for (NSString* ext in @[@"pak", @"ucas", @"utoc"]) {
      NSString* p = [dl stringByAppendingPathComponent:[stem stringByAppendingPathExtension:ext]];
      NSDictionary* a = [fm attributesOfItemAtPath:p.stringByResolvingSymlinksInPath error:nil];
      if ([a[NSFileSize] unsignedLongLongValue] == 0) complete = NO;
    }
    [text appendFormat:@"• %@ — %@\n", stem, complete ? @"đủ 3 file" : @"thiếu file đi kèm"];
    ++count;
  }
  if (!count) [text appendString:@"Chưa có bộ sân iOS trong Download.\n"];
  NSArray* batches = [fm contentsOfDirectoryAtPath:[gSupport stringByAppendingPathComponent:@"PendingMods"] error:nil];
  for (NSString* b in batches) if (![b hasPrefix:@"."]) [text appendFormat:@"\nMod chờ khởi động lại: %@", b];
  [text appendString:@"\n\nChọn ZIP có file .pak/.ucas/.utoc/.cpk, đặt trực tiếp hoặc trong pak, cpk, Download, livedata. Sân pc3xxx cần đủ cả 3 file trong cùng ZIP.\n\nSau khi nhập xong, đóng hẳn game rồi mở lại."];
  return text;
}

// Helper: Collect all current save files and compress into a temporary ZIP archive
static NSString* buildLocalSaveArchive(NSString** outError) {
  NSFileManager* fm = NSFileManager.defaultManager;
  NSString* saveDir = [gSupport stringByAppendingPathComponent:@"Save"];
  NSString* dbFile = [saveDir stringByAppendingPathComponent:@"ziru_save.db"];

  if (![fm fileExistsAtPath:dbFile]) {
    if (outError) *outError = @"Không tìm thấy file database ziru_save.db trên máy.";
    return nil;
  }

  std::vector<zzip::Entry> entries;

  // 1. Database file
  zzip::Entry eDb;
  eDb.nameInZip = "ziru_save.db";
  eDb.diskPath = dbFile.fileSystemRepresentation;
  entries.push_back(eDb);

  // 2. Prefs JSON files (e.g. prefs_myclub.json)
  NSArray* saveItems = [fm contentsOfDirectoryAtPath:saveDir error:nil];
  for (NSString* item in saveItems) {
    if ([item hasPrefix:@"prefs_"] && [item hasSuffix:@".json"]) {
      zzip::Entry ePref;
      ePref.nameInZip = item.UTF8String;
      ePref.diskPath = [saveDir stringByAppendingPathComponent:item].fileSystemRepresentation;
      entries.push_back(ePref);
    }
  }

  // 3. SaveData files (SYSTEM000, online_user_id_data)
  NSString* sdDir = [gDocs stringByAppendingPathComponent:@"SaveData"];
  if ([fm fileExistsAtPath:sdDir]) {
    NSDirectoryEnumerator* enumerator = [fm enumeratorAtPath:sdDir];
    NSString* subPath = nil;
    while ((subPath = [enumerator nextObject])) {
      NSString* fullP = [sdDir stringByAppendingPathComponent:subPath];
      BOOL isDir = NO;
      if ([fm fileExistsAtPath:fullP isDirectory:&isDir] && !isDir) {
        zzip::Entry eSd;
        eSd.nameInZip = [NSString stringWithFormat:@"SaveData/%@", subPath].UTF8String;
        eSd.diskPath = fullP.fileSystemRepresentation;
        entries.push_back(eSd);
      }
    }
  }

  // 4. Manifest metadata
  NSString* ver = NSBundle.mainBundle.infoDictionary[@"CFBundleShortVersionString"] ?: @"11.1.101";
  NSString* manifestJson = [NSString stringWithFormat:@"{\"app\":\"PES2027\",\"version\":\"%@\",\"timestamp\":%ld}", ver, (long)[[NSDate date] timeIntervalSince1970]];
  zzip::Entry eMf;
  eMf.nameInZip = "manifest.json";
  eMf.memoryData = std::vector<uint8_t>(manifestJson.UTF8String, manifestJson.UTF8String + strlen(manifestJson.UTF8String));
  entries.push_back(eMf);

  NSString* tmpZip = [NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"pes2027_save_%ld.zip", (long)[[NSDate date] timeIntervalSince1970]]];
  [fm removeItemAtPath:tmpZip error:nil];

  if (!zzip::writeZip(tmpZip.fileSystemRepresentation, entries)) {
    if (outError) *outError = @"Không thể tạo file nén dữ liệu.";
    return nil;
  }
  return tmpZip;
}

// Helper: Restore save files from a ZIP archive
static BOOL extractAndRestoreSaveArchive(NSString* zipPath, NSString** outError) {
  zz::Reader reader;
  std::string err;
  if (!reader.open(zipPath.fileSystemRepresentation, err)) {
    if (outError) *outError = [NSString stringWithFormat:@"Không thể đọc file zip: %s", err.c_str()];
    return NO;
  }

  NSFileManager* fm = NSFileManager.defaultManager;
  NSString* saveDir = [gSupport stringByAppendingPathComponent:@"Save"];
  [fm createDirectoryAtPath:saveDir withIntermediateDirectories:YES attributes:nil error:nil];

  // Auto-backup current save before overwriting
  NSString* backupDir = [gSupport stringByAppendingPathComponent:@"SaveBackups"];
  [fm createDirectoryAtPath:backupDir withIntermediateDirectories:YES attributes:nil error:nil];
  NSString* curDb = [saveDir stringByAppendingPathComponent:@"ziru_save.db"];
  if ([fm fileExistsAtPath:curDb]) {
    NSString* bFile = [backupDir stringByAppendingPathComponent:[NSString stringWithFormat:@"auto_pre_restore_%ld.db", (long)[[NSDate date] timeIntervalSince1970]]];
    [fm copyItemAtPath:curDb toPath:bFile error:nil];
  }

  // Remove stale WAL/SHM locks
  [fm removeItemAtPath:[saveDir stringByAppendingPathComponent:@"ziru_save.db-wal"] error:nil];
  [fm removeItemAtPath:[saveDir stringByAppendingPathComponent:@"ziru_save.db-shm"] error:nil];

  BOOL foundDb = NO;
  for (const auto& e : reader.entries()) {
    if (e.isDir()) continue;
    NSString* name = [NSString stringWithUTF8String:e.name.c_str()];
    NSString* targetPath = nil;

    if ([name isEqualToString:@"ziru_save.db"] || [name hasSuffix:@"/ziru_save.db"] || [name hasSuffix:@".db"]) {
      targetPath = [saveDir stringByAppendingPathComponent:@"ziru_save.db"];
      foundDb = YES;
    } else if ([name hasPrefix:@"prefs_"] && [name hasSuffix:@".json"]) {
      targetPath = [saveDir stringByAppendingPathComponent:name.lastPathComponent];
    } else if ([name hasPrefix:@"SaveData/"]) {
      NSString* rel = [name substringFromIndex:@"SaveData/".length];
      targetPath = [[gDocs stringByAppendingPathComponent:@"SaveData"] stringByAppendingPathComponent:rel];
      [fm createDirectoryAtPath:targetPath.stringByDeletingLastPathComponent withIntermediateDirectories:YES attributes:nil error:nil];
    }

    if (targetPath) {
      std::string sha;
      if (!reader.extract(e, targetPath.fileSystemRepresentation, sha, err)) {
        if (outError) *outError = [NSString stringWithFormat:@"Lỗi giải nén %@: %s", name, err.c_str()];
        return NO;
      }
    }
  }

  if (!foundDb) {
    if (outError) *outError = @"File zip không chứa database ziru_save.db hợp lệ.";
    return NO;
  }
  return YES;
}

@implementation ZiruModVC

- (void)viewDidLoad {
  [super viewDidLoad];
  self.title = @"PES 2027 • Dữ Liệu & Mod";
  self.view.backgroundColor = PESNight();

  self.navigationItem.rightBarButtonItem = [[UIBarButtonItem alloc] initWithTitle:@"Đóng" style:UIBarButtonItemStyleDone target:self action:@selector(closeMods)];

  // Top Tabs
  self.tabs = [[UISegmentedControl alloc] initWithItems:@[@"☁️ Save Cloud (6 số)", @"💾 Tệp Máy", @"🏟️ Mod Sân"]];
  self.tabs.selectedSegmentIndex = 0;
  self.tabs.backgroundColor = [UIColor colorWithWhite:0.12 alpha:0.9];
  self.tabs.selectedSegmentTintColor = PESLime();
  [self.tabs setTitleTextAttributes:@{NSForegroundColorAttributeName: PESNight(), NSFontAttributeName: [UIFont systemFontOfSize:13 weight:UIFontWeightBold]} forState:UIControlStateSelected];
  [self.tabs setTitleTextAttributes:@{NSForegroundColorAttributeName: UIColor.whiteColor, NSFontAttributeName: [UIFont systemFontOfSize:13 weight:UIFontWeightMedium]} forState:UIControlStateNormal];
  [self.tabs addTarget:self action:@selector(tabChanged:) forControlEvents:UIControlEventValueChanged];

  self.scrollView = [UIScrollView new];
  self.scrollView.alwaysBounceVertical = YES;
  self.scrollView.keyboardDismissMode = UIScrollViewKeyboardDismissModeOnDrag;

  [self setupCloudViews];
  [self setupLocalViews];
  [self setupModViews];

  for (UIView* v in @[self.tabs, self.scrollView]) {
    v.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:v];
  }

  UILayoutGuide* g = self.view.safeAreaLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [self.tabs.topAnchor constraintEqualToAnchor:g.topAnchor constant:10],
    [self.tabs.leadingAnchor constraintEqualToAnchor:g.leadingAnchor constant:16],
    [self.tabs.trailingAnchor constraintEqualToAnchor:g.trailingAnchor constant:-16],
    [self.tabs.heightAnchor constraintEqualToConstant:34],

    [self.scrollView.topAnchor constraintEqualToAnchor:self.tabs.bottomAnchor constant:12],
    [self.scrollView.leadingAnchor constraintEqualToAnchor:g.leadingAnchor constant:16],
    [self.scrollView.trailingAnchor constraintEqualToAnchor:g.trailingAnchor constant:-16],
    [self.scrollView.bottomAnchor constraintEqualToAnchor:g.bottomAnchor constant:-10]
  ]];

  [self updateTabVisibility];
  [self refreshRecentCodesList];
}

- (void)setupCloudViews {
  self.cloudContainer = [UIView new];
  self.cloudContainer.translatesAutoresizingMaskIntoConstraints = NO;
  [self.scrollView addSubview:self.cloudContainer];

  // Card 1: Cloud Export
  UIView* cardExport = [self makeCardView];
  UILabel* titleExport = [self makeSectionTitle:@"1. XUẤT SAVE LÊN CLOUD (LẤY MÃ 6 SỐ)"];
  UILabel* descExport = [self makeDescLabel:@"Sao lưu toàn bộ đội hình, cầu thủ, GP/Coins lên máy chủ pes.minhgame.com. Hệ thống sẽ cấp mã 6 chữ số để khôi phục lại bất kỳ lúc nào."];

  self.btnCloudExport = [UIButton buttonWithType:UIButtonTypeSystem];
  [self.btnCloudExport setTitle:@"☁️  LƯU LÊN CLOUD & LẤY MÃ 6 SỐ" forState:UIControlStateNormal];
  self.btnCloudExport.backgroundColor = PESLime();
  self.btnCloudExport.tintColor = PESNight();
  self.btnCloudExport.titleLabel.font = [UIFont systemFontOfSize:15 weight:UIFontWeightHeavy];
  self.btnCloudExport.layer.cornerRadius = 10;
  [self.btnCloudExport addTarget:self action:@selector(handleCloudExport) forControlEvents:UIControlEventTouchUpInside];

  for (UIView* v in @[titleExport, descExport, self.btnCloudExport]) {
    v.translatesAutoresizingMaskIntoConstraints = NO;
    [cardExport addSubview:v];
  }
  [NSLayoutConstraint activateConstraints:@[
    [titleExport.topAnchor constraintEqualToAnchor:cardExport.topAnchor constant:14],
    [titleExport.leadingAnchor constraintEqualToAnchor:cardExport.leadingAnchor constant:14],
    [titleExport.trailingAnchor constraintEqualToAnchor:cardExport.trailingAnchor constant:-14],

    [descExport.topAnchor constraintEqualToAnchor:titleExport.bottomAnchor constant:6],
    [descExport.leadingAnchor constraintEqualToAnchor:cardExport.leadingAnchor constant:14],
    [descExport.trailingAnchor constraintEqualToAnchor:cardExport.trailingAnchor constant:-14],

    [self.btnCloudExport.topAnchor constraintEqualToAnchor:descExport.bottomAnchor constant:14],
    [self.btnCloudExport.leadingAnchor constraintEqualToAnchor:cardExport.leadingAnchor constant:14],
    [self.btnCloudExport.trailingAnchor constraintEqualToAnchor:cardExport.trailingAnchor constant:-14],
    [self.btnCloudExport.heightAnchor constraintEqualToConstant:44],
    [self.btnCloudExport.bottomAnchor constraintEqualToAnchor:cardExport.bottomAnchor constant:-14]
  ]];

  // Card 2: Cloud Import
  UIView* cardImport = [self makeCardView];
  UILabel* titleImport = [self makeSectionTitle:@"2. KHÔI PHỤC SAVE TỪ MÃ 6 SỐ"];
  UILabel* descImport = [self makeDescLabel:@"Nhập đúng 6 chữ số bạn đã lưu trước đó (hoặc từ web) để tải và nạp đè dữ liệu vào game:"];

  self.txtCloudCode = [UITextField new];
  self.txtCloudCode.backgroundColor = [UIColor colorWithWhite:0.08 alpha:0.9];
  self.txtCloudCode.textColor = PESCyan();
  self.txtCloudCode.font = [UIFont monospacedDigitSystemFontOfSize:22 weight:UIFontWeightHeavy];
  self.txtCloudCode.textAlignment = NSTextAlignmentCenter;
  self.txtCloudCode.keyboardType = UIKeyboardTypeNumberPad;
  self.txtCloudCode.placeholder = @"Nhập mã 6 số (VD: 839102)";
  self.txtCloudCode.layer.cornerRadius = 8;
  self.txtCloudCode.layer.borderWidth = 1;
  self.txtCloudCode.layer.borderColor = [PESCyan() colorWithAlphaComponent:0.6].CGColor;
  self.txtCloudCode.delegate = self;

  self.btnCloudImport = [UIButton buttonWithType:UIButtonTypeSystem];
  [self.btnCloudImport setTitle:@"⬇️  TẢI & KHÔI PHỤC DATABASE" forState:UIControlStateNormal];
  self.btnCloudImport.backgroundColor = PESCyan();
  self.btnCloudImport.tintColor = PESNight();
  self.btnCloudImport.titleLabel.font = [UIFont systemFontOfSize:15 weight:UIFontWeightHeavy];
  self.btnCloudImport.layer.cornerRadius = 10;
  [self.btnCloudImport addTarget:self action:@selector(handleCloudImport) forControlEvents:UIControlEventTouchUpInside];

  for (UIView* v in @[titleImport, descImport, self.txtCloudCode, self.btnCloudImport]) {
    v.translatesAutoresizingMaskIntoConstraints = NO;
    [cardImport addSubview:v];
  }
  [NSLayoutConstraint activateConstraints:@[
    [titleImport.topAnchor constraintEqualToAnchor:cardImport.topAnchor constant:14],
    [titleImport.leadingAnchor constraintEqualToAnchor:cardImport.leadingAnchor constant:14],
    [titleImport.trailingAnchor constraintEqualToAnchor:cardImport.trailingAnchor constant:-14],

    [descImport.topAnchor constraintEqualToAnchor:titleImport.bottomAnchor constant:6],
    [descImport.leadingAnchor constraintEqualToAnchor:cardImport.leadingAnchor constant:14],
    [descImport.trailingAnchor constraintEqualToAnchor:cardImport.trailingAnchor constant:-14],

    [self.txtCloudCode.topAnchor constraintEqualToAnchor:descImport.bottomAnchor constant:12],
    [self.txtCloudCode.leadingAnchor constraintEqualToAnchor:cardImport.leadingAnchor constant:14],
    [self.txtCloudCode.trailingAnchor constraintEqualToAnchor:cardImport.trailingAnchor constant:-14],
    [self.txtCloudCode.heightAnchor constraintEqualToConstant:44],

    [self.btnCloudImport.topAnchor constraintEqualToAnchor:self.txtCloudCode.bottomAnchor constant:12],
    [self.btnCloudImport.leadingAnchor constraintEqualToAnchor:cardImport.leadingAnchor constant:14],
    [self.btnCloudImport.trailingAnchor constraintEqualToAnchor:cardImport.trailingAnchor constant:-14],
    [self.btnCloudImport.heightAnchor constraintEqualToConstant:44],
    [self.btnCloudImport.bottomAnchor constraintEqualToAnchor:cardImport.bottomAnchor constant:-14]
  ]];

  // Card 3: Recent Codes History & Status
  UIView* cardHistory = [self makeCardView];
  UILabel* titleHistory = [self makeSectionTitle:@"LỊCH SỬ MÃ ĐÃ LƯU TRÊN THIẾT BỊ"];
  self.lblRecentCodes = [self makeDescLabel:@"Chưa có mã lưu trữ nào."];
  self.lblRecentCodes.textColor = [UIColor colorWithWhite:0.85 alpha:1.0];

  self.spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleMedium];
  self.spinner.color = PESLime();
  self.spinner.hidesWhenStopped = YES;

  self.lblCloudStatus = [self makeDescLabel:@""];
  self.lblCloudStatus.textColor = PESLime();
  self.lblCloudStatus.textAlignment = NSTextAlignmentCenter;
  self.lblCloudStatus.font = [UIFont systemFontOfSize:13 weight:UIFontWeightBold];

  for (UIView* v in @[titleHistory, self.lblRecentCodes, self.spinner, self.lblCloudStatus]) {
    v.translatesAutoresizingMaskIntoConstraints = NO;
    [cardHistory addSubview:v];
  }
  [NSLayoutConstraint activateConstraints:@[
    [titleHistory.topAnchor constraintEqualToAnchor:cardHistory.topAnchor constant:14],
    [titleHistory.leadingAnchor constraintEqualToAnchor:cardHistory.leadingAnchor constant:14],
    [titleHistory.trailingAnchor constraintEqualToAnchor:cardHistory.trailingAnchor constant:-14],

    [self.lblRecentCodes.topAnchor constraintEqualToAnchor:titleHistory.bottomAnchor constant:8],
    [self.lblRecentCodes.leadingAnchor constraintEqualToAnchor:cardHistory.leadingAnchor constant:14],
    [self.lblRecentCodes.trailingAnchor constraintEqualToAnchor:cardHistory.trailingAnchor constant:-14],

    [self.spinner.topAnchor constraintEqualToAnchor:self.lblRecentCodes.bottomAnchor constant:10],
    [self.spinner.centerXAnchor constraintEqualToAnchor:cardHistory.centerXAnchor],

    [self.lblCloudStatus.topAnchor constraintEqualToAnchor:self.spinner.bottomAnchor constant:6],
    [self.lblCloudStatus.leadingAnchor constraintEqualToAnchor:cardHistory.leadingAnchor constant:14],
    [self.lblCloudStatus.trailingAnchor constraintEqualToAnchor:cardHistory.trailingAnchor constant:-14],
    [self.lblCloudStatus.bottomAnchor constraintEqualToAnchor:cardHistory.bottomAnchor constant:-14]
  ]];

  for (UIView* c in @[cardExport, cardImport, cardHistory]) {
    c.translatesAutoresizingMaskIntoConstraints = NO;
    [self.cloudContainer addSubview:c];
  }
  [NSLayoutConstraint activateConstraints:@[
    [self.cloudContainer.topAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.topAnchor],
    [self.cloudContainer.leadingAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.leadingAnchor],
    [self.cloudContainer.trailingAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.trailingAnchor],
    [self.cloudContainer.bottomAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.bottomAnchor],
    [self.cloudContainer.widthAnchor constraintEqualToAnchor:self.scrollView.frameLayoutGuide.widthAnchor],

    [cardExport.topAnchor constraintEqualToAnchor:self.cloudContainer.topAnchor constant:6],
    [cardExport.leadingAnchor constraintEqualToAnchor:self.cloudContainer.leadingAnchor],
    [cardExport.trailingAnchor constraintEqualToAnchor:self.cloudContainer.trailingAnchor],

    [cardImport.topAnchor constraintEqualToAnchor:cardExport.bottomAnchor constant:14],
    [cardImport.leadingAnchor constraintEqualToAnchor:self.cloudContainer.leadingAnchor],
    [cardImport.trailingAnchor constraintEqualToAnchor:self.cloudContainer.trailingAnchor],

    [cardHistory.topAnchor constraintEqualToAnchor:cardImport.bottomAnchor constant:14],
    [cardHistory.leadingAnchor constraintEqualToAnchor:self.cloudContainer.leadingAnchor],
    [cardHistory.trailingAnchor constraintEqualToAnchor:self.cloudContainer.trailingAnchor],
    [cardHistory.bottomAnchor constraintEqualToAnchor:self.cloudContainer.bottomAnchor constant:-20]
  ]];
}

- (void)setupLocalViews {
  self.localContainer = [UIView new];
  self.localContainer.translatesAutoresizingMaskIntoConstraints = NO;
  [self.scrollView addSubview:self.localContainer];

  UIView* cardLocal = [self makeCardView];
  UILabel* title = [self makeSectionTitle:@"SAO LƯU & KHÔI PHỤC VỚI TỆP TRÊN MÁY (OFFLINE)"];
  UILabel* desc = [self makeDescLabel:@"Xuất dữ liệu save thành file .zip để lưu vào ứng dụng Tệp, chia sẻ qua AirDrop, Google Drive hoặc nạp lại trực tiếp từ file trên máy:"];

  self.btnLocalExport = [UIButton buttonWithType:UIButtonTypeSystem];
  [self.btnLocalExport setTitle:@"📤  Xuất File Save (.zip) ra Tệp / Chia sẻ" forState:UIControlStateNormal];
  self.btnLocalExport.backgroundColor = [UIColor colorWithWhite:0.18 alpha:0.95];
  self.btnLocalExport.tintColor = UIColor.whiteColor;
  self.btnLocalExport.titleLabel.font = [UIFont systemFontOfSize:14 weight:UIFontWeightBold];
  self.btnLocalExport.layer.cornerRadius = 10;
  [self.btnLocalExport addTarget:self action:@selector(handleLocalExport) forControlEvents:UIControlEventTouchUpInside];

  self.btnLocalImport = [UIButton buttonWithType:UIButtonTypeSystem];
  [self.btnLocalImport setTitle:@"📥  Chọn File Save (.db / .zip) từ Tệp để nạp" forState:UIControlStateNormal];
  self.btnLocalImport.backgroundColor = [UIColor colorWithWhite:0.18 alpha:0.95];
  self.btnLocalImport.tintColor = PESCyan();
  self.btnLocalImport.titleLabel.font = [UIFont systemFontOfSize:14 weight:UIFontWeightBold];
  self.btnLocalImport.layer.cornerRadius = 10;
  [self.btnLocalImport addTarget:self action:@selector(handleLocalImport) forControlEvents:UIControlEventTouchUpInside];

  self.lblLocalStatus = [self makeDescLabel:@""];
  self.lblLocalStatus.textColor = PESLime();
  self.lblLocalStatus.textAlignment = NSTextAlignmentCenter;

  for (UIView* v in @[title, desc, self.btnLocalExport, self.btnLocalImport, self.lblLocalStatus]) {
    v.translatesAutoresizingMaskIntoConstraints = NO;
    [cardLocal addSubview:v];
  }
  [NSLayoutConstraint activateConstraints:@[
    [title.topAnchor constraintEqualToAnchor:cardLocal.topAnchor constant:14],
    [title.leadingAnchor constraintEqualToAnchor:cardLocal.leadingAnchor constant:14],
    [title.trailingAnchor constraintEqualToAnchor:cardLocal.trailingAnchor constant:-14],

    [desc.topAnchor constraintEqualToAnchor:title.bottomAnchor constant:8],
    [desc.leadingAnchor constraintEqualToAnchor:cardLocal.leadingAnchor constant:14],
    [desc.trailingAnchor constraintEqualToAnchor:cardLocal.trailingAnchor constant:-14],

    [self.btnLocalExport.topAnchor constraintEqualToAnchor:desc.bottomAnchor constant:16],
    [self.btnLocalExport.leadingAnchor constraintEqualToAnchor:cardLocal.leadingAnchor constant:14],
    [self.btnLocalExport.trailingAnchor constraintEqualToAnchor:cardLocal.trailingAnchor constant:-14],
    [self.btnLocalExport.heightAnchor constraintEqualToConstant:44],

    [self.btnLocalImport.topAnchor constraintEqualToAnchor:self.btnLocalExport.bottomAnchor constant:12],
    [self.btnLocalImport.leadingAnchor constraintEqualToAnchor:cardLocal.leadingAnchor constant:14],
    [self.btnLocalImport.trailingAnchor constraintEqualToAnchor:cardLocal.trailingAnchor constant:-14],
    [self.btnLocalImport.heightAnchor constraintEqualToConstant:44],

    [self.lblLocalStatus.topAnchor constraintEqualToAnchor:self.btnLocalImport.bottomAnchor constant:12],
    [self.lblLocalStatus.leadingAnchor constraintEqualToAnchor:cardLocal.leadingAnchor constant:14],
    [self.lblLocalStatus.trailingAnchor constraintEqualToAnchor:cardLocal.trailingAnchor constant:-14],
    [self.lblLocalStatus.bottomAnchor constraintEqualToAnchor:cardLocal.bottomAnchor constant:-14]
  ]];

  cardLocal.translatesAutoresizingMaskIntoConstraints = NO;
  [self.localContainer addSubview:cardLocal];
  [NSLayoutConstraint activateConstraints:@[
    [self.localContainer.topAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.topAnchor],
    [self.localContainer.leadingAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.leadingAnchor],
    [self.localContainer.trailingAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.trailingAnchor],
    [self.localContainer.bottomAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.bottomAnchor],
    [self.localContainer.widthAnchor constraintEqualToAnchor:self.scrollView.frameLayoutGuide.widthAnchor],

    [cardLocal.topAnchor constraintEqualToAnchor:self.localContainer.topAnchor constant:6],
    [cardLocal.leadingAnchor constraintEqualToAnchor:self.localContainer.leadingAnchor],
    [cardLocal.trailingAnchor constraintEqualToAnchor:self.localContainer.trailingAnchor],
    [cardLocal.bottomAnchor constraintEqualToAnchor:self.localContainer.bottomAnchor constant:-20]
  ]];
}

- (void)setupModViews {
  self.modContainer = [UIView new];
  self.modContainer.translatesAutoresizingMaskIntoConstraints = NO;
  [self.scrollView addSubview:self.modContainer];

  self.pickMod = [UIButton buttonWithType:UIButtonTypeSystem];
  [self.pickMod setTitle:@"Chọn ZIP mod từ Tệp" forState:UIControlStateNormal];
  self.pickMod.backgroundColor = PESLime();
  self.pickMod.tintColor = PESNight();
  self.pickMod.titleLabel.font = [UIFont systemFontOfSize:15 weight:UIFontWeightBold];
  self.pickMod.layer.cornerRadius = 10;
  [self.pickMod addTarget:self action:@selector(chooseMod) forControlEvents:UIControlEventTouchUpInside];

  self.inventory = [UITextView new];
  self.inventory.editable = NO;
  self.inventory.backgroundColor = [UIColor colorWithWhite:0.08 alpha:0.7];
  self.inventory.layer.cornerRadius = 10;
  self.inventory.textColor = UIColor.whiteColor;
  self.inventory.font = [UIFont systemFontOfSize:14];
  self.inventory.text = modInventory();

  for (UIView* v in @[self.pickMod, self.inventory]) {
    v.translatesAutoresizingMaskIntoConstraints = NO;
    [self.modContainer addSubview:v];
  }
  [NSLayoutConstraint activateConstraints:@[
    [self.modContainer.topAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.topAnchor],
    [self.modContainer.leadingAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.leadingAnchor],
    [self.modContainer.trailingAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.trailingAnchor],
    [self.modContainer.bottomAnchor constraintEqualToAnchor:self.scrollView.contentLayoutGuide.bottomAnchor],
    [self.modContainer.widthAnchor constraintEqualToAnchor:self.scrollView.frameLayoutGuide.widthAnchor],

    [self.pickMod.topAnchor constraintEqualToAnchor:self.modContainer.topAnchor constant:6],
    [self.pickMod.leadingAnchor constraintEqualToAnchor:self.modContainer.leadingAnchor],
    [self.pickMod.trailingAnchor constraintEqualToAnchor:self.modContainer.trailingAnchor],
    [self.pickMod.heightAnchor constraintEqualToConstant:44],

    [self.inventory.topAnchor constraintEqualToAnchor:self.pickMod.bottomAnchor constant:12],
    [self.inventory.leadingAnchor constraintEqualToAnchor:self.modContainer.leadingAnchor],
    [self.inventory.trailingAnchor constraintEqualToAnchor:self.modContainer.trailingAnchor],
    [self.inventory.heightAnchor constraintEqualToConstant:320],
    [self.inventory.bottomAnchor constraintEqualToAnchor:self.modContainer.bottomAnchor constant:-20]
  ]];
}

- (void)tabChanged:(UISegmentedControl*)sender {
  [self.view endEditing:YES];
  [self updateTabVisibility];
}

- (void)updateTabVisibility {
  NSInteger idx = self.tabs.selectedSegmentIndex;
  self.cloudContainer.hidden = (idx != 0);
  self.localContainer.hidden = (idx != 1);
  self.modContainer.hidden = (idx != 2);
}

- (UIView*)makeCardView {
  UIView* v = [UIView new];
  v.backgroundColor = [UIColor colorWithWhite:0.06 alpha:0.8];
  v.layer.cornerRadius = 12;
  v.layer.borderWidth = 0.5;
  v.layer.borderColor = [UIColor colorWithWhite:1.0 alpha:0.12].CGColor;
  return v;
}

- (UILabel*)makeSectionTitle:(NSString*)text {
  UILabel* l = [UILabel new];
  l.text = text;
  l.textColor = PESLime();
  l.font = [UIFont systemFontOfSize:14 weight:UIFontWeightHeavy];
  return l;
}

- (UILabel*)makeDescLabel:(NSString*)text {
  UILabel* l = [UILabel new];
  l.text = text;
  l.textColor = [UIColor colorWithWhite:0.75 alpha:1.0];
  l.font = [UIFont systemFontOfSize:13 weight:UIFontWeightRegular];
  l.numberOfLines = 0;
  return l;
}

- (void)closeMods {
  [self.view endEditing:YES];
  [self dismissViewControllerAnimated:YES completion:nil];
}

// -----------------------------------------------------------------------------
// Cloud Save Sync Logic
// -----------------------------------------------------------------------------
- (void)handleCloudExport {
  [self.view endEditing:YES];
  self.btnCloudExport.enabled = NO;
  [self.spinner startAnimating];
  self.lblCloudStatus.text = @"Đang nén dữ liệu và gửi lên máy chủ pes.minhgame.com…";

  dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
    NSString* err = nil;
    NSString* zipPath = buildLocalSaveArchive(&err);
    if (!zipPath) {
      dispatch_async(dispatch_get_main_queue(), ^{
        self.btnCloudExport.enabled = YES;
        [self.spinner stopAnimating];
        self.lblCloudStatus.text = @"Lỗi đóng gói file save.";
        [self showAlertWithTitle:@"Lỗi xuất save" message:err ?: @"Không rõ nguyên nhân."];
      });
      return;
    }

    NSData* zipData = [NSData dataWithContentsOfFile:zipPath];
    [NSFileManager.defaultManager removeItemAtPath:zipPath error:nil];

    if (!zipData.length) {
      dispatch_async(dispatch_get_main_queue(), ^{
        self.btnCloudExport.enabled = YES;
        [self.spinner stopAnimating];
        self.lblCloudStatus.text = @"Dữ liệu nén rỗng.";
      });
      return;
    }

    // Prepare multipart form upload
    NSString* boundary = [NSString stringWithFormat:@"Boundary-%@", [[NSUUID UUID] UUIDString]];
    NSMutableURLRequest* req = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:kCloudApiBase] cachePolicy:NSURLRequestReloadIgnoringLocalCacheData timeoutInterval:25.0];
    req.HTTPMethod = @"POST";
    [req setValue:[NSString stringWithFormat:@"multipart/form-data; boundary=%@", boundary] forHTTPHeaderField:@"Content-Type"];

    NSMutableData* body = [NSMutableData data];
    [body appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[@"Content-Disposition: form-data; name=\"action\"\r\n\r\nupload\r\n" dataUsingEncoding:NSUTF8StringEncoding]];

    [body appendData:[[NSString stringWithFormat:@"--%@\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[@"Content-Disposition: form-data; name=\"file\"; filename=\"pes2027_save.zip\"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[@"Content-Type: application/zip\r\n\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:zipData];
    [body appendData:[@"\r\n" dataUsingEncoding:NSUTF8StringEncoding]];
    [body appendData:[[NSString stringWithFormat:@"--%@--\r\n", boundary] dataUsingEncoding:NSUTF8StringEncoding]];

    req.HTTPBody = body;

    NSURLSessionDataTask* task = [[NSURLSession sharedSession] dataTaskWithRequest:req completionHandler:^(NSData* data, NSURLResponse* resp, NSError* netErr) {
      dispatch_async(dispatch_get_main_queue(), ^{
        self.btnCloudExport.enabled = YES;
        [self.spinner stopAnimating];

        if (netErr || !data.length) {
          self.lblCloudStatus.text = @"Lỗi kết nối máy chủ.";
          [self showAlertWithTitle:@"Lỗi kết nối" message:netErr ? netErr.localizedDescription : @"Máy chủ không phản hồi."];
          return;
        }

        NSDictionary* json = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
        if ([json isKindOfClass:[NSDictionary class]] && [json[@"success"] boolValue] && json[@"code"]) {
          NSString* code = [NSString stringWithFormat:@"%@", json[@"code"]];
          double sizeKb = [json[@"size_kb"] doubleValue];
          [self saveRecentCode:code];
          self.txtCloudCode.text = code;
          self.lblCloudStatus.text = [NSString stringWithFormat:@"✅ Đã lưu! Mã của bạn: %@", code];

          NSString* alertMsg = [NSString stringWithFormat:@"Mã khôi phục Cloud của bạn:\n\n👉  %@  👈\n\nDung lượng: %.1f KB\n\nDữ liệu đã lưu an toàn trên máy chủ pes.minhgame.com.\nHãy ghi nhớ hoặc sao chép mã 6 số này để khôi phục bất cứ lúc nào.", code, sizeKb];
          UIAlertController* a = [UIAlertController alertControllerWithTitle:@"🎉 Lưu Cloud Thành Công!" message:alertMsg preferredStyle:UIAlertControllerStyleAlert];
          [a addAction:[UIAlertAction actionWithTitle:@"Sao chép mã" style:UIAlertActionStyleDefault handler:^(UIAlertAction*) {
            [UIPasteboard generalPasteboard].string = code;
          }]];
          [a addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleCancel handler:nil]];
          [self presentViewController:a animated:YES completion:nil];
        } else {
          NSString* msg = json[@"message"] ?: @"Không thể nhận mã từ máy chủ.";
          self.lblCloudStatus.text = msg;
          [self showAlertWithTitle:@"Lỗi máy chủ" message:msg];
        }
      });
    }];
    [task resume];
  });
}

- (void)handleCloudImport {
  [self.view endEditing:YES];
  NSString* code = [self.txtCloudCode.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
  if (code.length != 6) {
    [self showAlertWithTitle:@"Mã không hợp lệ" message:@"Vui lòng nhập đúng 6 chữ số mã khôi phục."];
    return;
  }

  self.btnCloudImport.enabled = NO;
  [self.spinner startAnimating];
  self.lblCloudStatus.text = [NSString stringWithFormat:@"Đang tải database mã %@ từ máy chủ…", code];

  NSString* dlUrlStr = [NSString stringWithFormat:@"%@?action=download&code=%@", kCloudApiBase, code];
  NSURL* u = [NSURL URLWithString:dlUrlStr];

  NSURLSessionDownloadTask* task = [[NSURLSession sharedSession] downloadTaskWithURL:u completionHandler:^(NSURL* loc, NSURLResponse* resp, NSError* netErr) {
    if (netErr || !loc) {
      dispatch_async(dispatch_get_main_queue(), ^{
        self.btnCloudImport.enabled = YES;
        [self.spinner stopAnimating];
        self.lblCloudStatus.text = @"Lỗi tải dữ liệu.";
        [self showAlertWithTitle:@"Lỗi tải dữ liệu" message:netErr ? netErr.localizedDescription : @"Không thể kết nối đến máy chủ."];
      });
      return;
    }

    // Verify response status
    NSHTTPURLResponse* httpResp = (NSHTTPURLResponse*)resp;
    if (httpResp.statusCode != 200) {
      NSData* errData = [NSData dataWithContentsOfURL:loc];
      NSDictionary* j = errData ? [NSJSONSerialization JSONObjectWithData:errData options:0 error:nil] : nil;
      NSString* msg = j[@"message"] ?: [NSString stringWithFormat:@"Mã %@ không tồn tại trên hệ thống.", code];
      dispatch_async(dispatch_get_main_queue(), ^{
        self.btnCloudImport.enabled = YES;
        [self.spinner stopAnimating];
        self.lblCloudStatus.text = msg;
        [self showAlertWithTitle:@"Không tìm thấy file save" message:msg];
      });
      return;
    }

    NSString* tmpZip = [NSTemporaryDirectory() stringByAppendingPathComponent:[NSString stringWithFormat:@"pes_import_%@.zip", code]];
    [NSFileManager.defaultManager removeItemAtPath:tmpZip error:nil];
    [NSFileManager.defaultManager moveItemAtURL:loc toURL:[NSURL fileURLWithPath:tmpZip] error:nil];

    NSString* err = nil;
    BOOL ok = extractAndRestoreSaveArchive(tmpZip, &err);
    [NSFileManager.defaultManager removeItemAtPath:tmpZip error:nil];

    dispatch_async(dispatch_get_main_queue(), ^{
      self.btnCloudImport.enabled = YES;
      [self.spinner stopAnimating];

      if (ok) {
        [self saveRecentCode:code];
        self.lblCloudStatus.text = [NSString stringWithFormat:@"✅ Đã khôi phục save mã %@!", code];
        NSString* successMsg = [NSString stringWithFormat:@"Đã khôi phục toàn bộ database và đội hình từ mã [%@] thành công!\n\n⚠️ Vui lòng vuốt TẮT HẲN GAME (kill app) và mở lại để hệ thống nạp dữ liệu mới.", code];
        UIAlertController* a = [UIAlertController alertControllerWithTitle:@"✅ Khôi Phục Thành Công" message:successMsg preferredStyle:UIAlertControllerStyleAlert];
        [a addAction:[UIAlertAction actionWithTitle:@"Đóng game ngay" style:UIAlertActionStyleDestructive handler:^(UIAlertAction*) {
          exit(0);
        }]];
        [a addAction:[UIAlertAction actionWithTitle:@"Để tôi tự đóng" style:UIAlertActionStyleCancel handler:nil]];
        [self presentViewController:a animated:YES completion:nil];
      } else {
        self.lblCloudStatus.text = @"Giải nén save thất bại.";
        [self showAlertWithTitle:@"Lỗi giải nén" message:err ?: @"Không thể trích xuất database."];
      }
    });
  }];
  [task resume];
}

// -----------------------------------------------------------------------------
// Local Export / Import
// -----------------------------------------------------------------------------
- (void)handleLocalExport {
  NSString* err = nil;
  NSString* zipPath = buildLocalSaveArchive(&err);
  if (!zipPath) {
    [self showAlertWithTitle:@"Lỗi xuất save" message:err ?: @"Không tìm thấy file save."];
    return;
  }
  NSURL* u = [NSURL fileURLWithPath:zipPath];
  UIActivityViewController* avc = [[UIActivityViewController alloc] initWithActivityItems:@[u] applicationActivities:nil];
  if (UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad) {
    avc.popoverPresentationController.sourceView = self.btnLocalExport;
    avc.popoverPresentationController.sourceRect = self.btnLocalExport.bounds;
  }
  [self presentViewController:avc animated:YES completion:nil];
  self.lblLocalStatus.text = @"Đã tạo file zip save local thành công!";
}

- (void)handleLocalImport {
  NSArray* types = @[UTTypeZIP, [UTType typeWithFilenameExtension:@"db"] ?: UTTypeData];
  UIDocumentPickerViewController* p = [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:types asCopy:YES];
  p.delegate = self;
  [self presentViewController:p animated:YES completion:nil];
}

// -----------------------------------------------------------------------------
// Stadium Mod Logic (Original Feature)
// -----------------------------------------------------------------------------
- (void)chooseMod {
  UIDocumentPickerViewController* p = [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[UTTypeZIP] asCopy:NO];
  p.delegate = self;
  [self presentViewController:p animated:YES completion:nil];
}

- (void)documentPicker:(UIDocumentPickerViewController*)picker didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls {
  NSURL* u = urls.firstObject;
  if (!u) return;

  // Check if this was a local save import (.db or save zip)
  if ([u.pathExtension.lowercaseString isEqualToString:@"db"] || [u.lastPathComponent containsString:@"save"]) {
    BOOL scoped = [u startAccessingSecurityScopedResource];
    NSString* err = nil;
    BOOL ok = NO;

    if ([u.pathExtension.lowercaseString isEqualToString:@"db"]) {
      // Direct database file
      NSString* saveDir = [gSupport stringByAppendingPathComponent:@"Save"];
      [NSFileManager.defaultManager createDirectoryAtPath:saveDir withIntermediateDirectories:YES attributes:nil error:nil];
      NSString* targetDb = [saveDir stringByAppendingPathComponent:@"ziru_save.db"];
      [NSFileManager.defaultManager removeItemAtPath:targetDb error:nil];
      ok = [NSFileManager.defaultManager copyItemAtPath:u.path toPath:targetDb error:nil];
      [NSFileManager.defaultManager removeItemAtPath:[saveDir stringByAppendingPathComponent:@"ziru_save.db-wal"] error:nil];
      [NSFileManager.defaultManager removeItemAtPath:[saveDir stringByAppendingPathComponent:@"ziru_save.db-shm"] error:nil];
    } else {
      ok = extractAndRestoreSaveArchive(u.path, &err);
    }
    if (scoped) [u stopAccessingSecurityScopedResource];

    if (ok) {
      [self showAlertWithTitle:@"✅ Khôi phục thành công" message:@"Đã nhập database từ Tệp. Hãy đóng hẳn game và mở lại để áp dụng."];
    } else {
      [self showAlertWithTitle:@"Nhập thất bại" message:err ?: @"Không thể sao chép database."];
    }
    return;
  }

  // Otherwise, it's a stadium/gameplay mod ZIP
  BOOL scoped = [u startAccessingSecurityScopedResource];
  self.pickMod.enabled = NO;
  self.navigationItem.rightBarButtonItem.enabled = NO;
  self.inventory.text = @"Đang giải nén và kiểm tra file mod…\nVui lòng giữ ứng dụng mở.";
  BOOL wasIdleDisabled = UIApplication.sharedApplication.idleTimerDisabled;
  UIApplication.sharedApplication.idleTimerDisabled = YES;
  uint64_t available = freeBytes();

  dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
    std::string summary, error;
    bool ok = false;
    try {
      ok = zm::stageZip(u.path.fileSystemRepresentation,
          [gSupport stringByAppendingPathComponent:@"PendingMods"].fileSystemRepresentation, available, summary, error);
    } catch (const std::exception& e) { error = e.what(); }
    if (scoped) [u stopAccessingSecurityScopedResource];
    ZLog(@"[MOD] stage %s: %s", ok ? "OK" : "FAILED", ok ? summary.c_str() : error.c_str());
    dispatch_async(dispatch_get_main_queue(), ^{
      UIApplication.sharedApplication.idleTimerDisabled = wasIdleDisabled;
      self.pickMod.enabled = YES;
      self.navigationItem.rightBarButtonItem.enabled = YES;
      self.inventory.text = modInventory();
      NSString* msg = ok ? @"Đã kiểm tra và chuẩn bị mod. Hãy đóng hẳn game rồi mở lại để áp dụng."
          : [NSString stringWithUTF8String:error.c_str()];
      [self showAlertWithTitle:ok ? @"Mod đã sẵn sàng" : @"Chưa nhập được mod" message:msg];
    });
  });
}

// -----------------------------------------------------------------------------
// Utilities & Helpers
// -----------------------------------------------------------------------------
- (void)saveRecentCode:(NSString*)code {
  if (code.length != 6) return;
  NSUserDefaults* ud = NSUserDefaults.standardUserDefaults;
  NSMutableArray* arr = [[ud stringArrayForKey:kCloudRecentCodesKey] mutableCopy] ?: [NSMutableArray array];
  [arr removeObject:code];
  [arr insertObject:code atIndex:0];
  while (arr.count > 5) [arr removeLastObject];
  [ud setObject:arr forKey:kCloudRecentCodesKey];
  [ud synchronize];
  [self refreshRecentCodesList];
}

- (void)refreshRecentCodesList {
  NSArray* arr = [NSUserDefaults.standardUserDefaults stringArrayForKey:kCloudRecentCodesKey];
  if (!arr.count) {
    self.lblRecentCodes.text = @"Chưa có mã lưu trữ nào gần đây.";
    return;
  }
  NSMutableString* s = [NSMutableString stringWithString:@"Các mã lưu gần nhất (nhấn để nạp):\n"];
  for (NSString* c in arr) {
    [s appendFormat:@"• Mã: %@\n", c];
  }
  self.lblRecentCodes.text = s;
}

- (BOOL)textField:(UITextField*)textField shouldChangeCharactersInRange:(NSRange)range replacementString:(NSString*)string {
  NSString* current = [textField.text stringByReplacingCharactersInRange:range withString:string];
  NSString* filtered = [[current componentsSeparatedByCharactersInSet:[[NSCharacterSet decimalDigitCharacterSet] invertedSet]] componentsJoinedByString:@""];
  if (filtered.length > 6) return NO;
  textField.text = filtered;
  return NO;
}

- (void)showAlertWithTitle:(NSString*)title message:(NSString*)message {
  UIAlertController* a = [UIAlertController alertControllerWithTitle:title message:message preferredStyle:UIAlertControllerStyleAlert];
  [a addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
  [self presentViewController:a animated:YES completion:nil];
}

@end

// -----------------------------------------------------------------------------
// Floating Menu Button (Ingame Overlay)
// -----------------------------------------------------------------------------
@interface ZiruModButtonTarget : NSObject
- (void)openMods:(UIButton*)button;
- (void)handlePan:(UIPanGestureRecognizer*)pan;
- (void)touchDown:(UIButton*)button;
- (void)touchUp:(UIButton*)button;
@end

@implementation ZiruModButtonTarget
- (void)openMods:(UIButton*)button {
  UIViewController* vc = button.window.rootViewController;
  while (vc.presentedViewController) vc = vc.presentedViewController;
  if (!vc || ([vc isKindOfClass:UINavigationController.class] && [((UINavigationController*)vc).topViewController isKindOfClass:ZiruModVC.class])) return;
  UINavigationController* nav = [[UINavigationController alloc] initWithRootViewController:[ZiruModVC new]];
  nav.modalPresentationStyle = UIModalPresentationPageSheet;
  [vc presentViewController:nav animated:YES completion:nil];
}
- (void)touchDown:(UIButton*)button {
  [UIView animateWithDuration:0.15 animations:^{ button.alpha = 1.0; button.transform = CGAffineTransformMakeScale(1.08, 1.08); }];
}
- (void)touchUp:(UIButton*)button {
  [UIView animateWithDuration:0.15 animations:^{ button.transform = CGAffineTransformIdentity; }];
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(2.0 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
    [UIView animateWithDuration:0.3 animations:^{ button.alpha = 0.35; }];
  });
}
- (void)handlePan:(UIPanGestureRecognizer*)pan {
  UIView* v = pan.view;
  if (!v || !v.superview) return;
  CGPoint trans = [pan translationInView:v.superview];
  v.center = CGPointMake(v.center.x + trans.x, v.center.y + trans.y);
  [pan setTranslation:CGPointZero inView:v.superview];

  if (pan.state == UIGestureRecognizerStateBegan) {
    [UIView animateWithDuration:0.15 animations:^{ v.alpha = 1.0; }];
  } else if (pan.state == UIGestureRecognizerStateEnded || pan.state == UIGestureRecognizerStateCancelled) {
    CGRect b = v.superview.bounds;
    CGFloat midX = CGRectGetMidX(b);
    CGFloat targetX = (v.center.x < midX) ? (v.bounds.size.width / 2.0 + 8.0) : (b.size.width - v.bounds.size.width / 2.0 - 8.0);
    CGFloat targetY = MIN(MAX(v.center.y, 40.0), b.size.height - 40.0);
    [UIView animateWithDuration:0.25 delay:0 options:UIViewAnimationOptionCurveEaseOut animations:^{
      v.center = CGPointMake(targetX, targetY);
      v.alpha = 0.35;
    } completion:nil];
  }
}
@end

static void installModButton(UIWindow* win) {
  if (!win) return;
  static ZiruModButtonTarget* target;
  static UIButton* button;
  if (!target) target = [ZiruModButtonTarget new];
  if (!button) {
    button = [UIButton buttonWithType:UIButtonTypeCustom];
    CGFloat w = 52, h = 24;
    button.frame = CGRectMake(0, 0, w, h);
    button.backgroundColor = [UIColor colorWithWhite:0.04 alpha:0.75];
    button.layer.cornerRadius = h / 2.0;
    button.layer.borderWidth = 0.8;
    button.layer.borderColor = [PESLime() colorWithAlphaComponent:0.6].CGColor;
    button.layer.masksToBounds = YES;

    UIBlurEffect* blur = [UIBlurEffect effectWithStyle:UIBlurEffectStyleDark];
    UIVisualEffectView* blurView = [[UIVisualEffectView alloc] initWithEffect:blur];
    blurView.frame = button.bounds;
    blurView.userInteractionEnabled = NO;
    blurView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    [button insertSubview:blurView atIndex:0];

    [button setTitle:@"DATA" forState:UIControlStateNormal];
    button.titleLabel.font = [UIFont systemFontOfSize:10 weight:UIFontWeightHeavy];
    [button setTitleColor:PESLime() forState:UIControlStateNormal];

    [button addTarget:target action:@selector(touchDown:) forControlEvents:UIControlEventTouchDown];
    [button addTarget:target action:@selector(touchUp:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside];
    [button addTarget:target action:@selector(openMods:) forControlEvents:UIControlEventTouchUpInside];
    UIPanGestureRecognizer* pan = [[UIPanGestureRecognizer alloc] initWithTarget:target action:@selector(handlePan:)];
    [button addGestureRecognizer:pan];
    button.alpha = 0.35;
  }

  if (button.superview == win) {
    [win bringSubviewToFront:button];
    return;
  }
  [button removeFromSuperview];
  button.translatesAutoresizingMaskIntoConstraints = YES;
  CGSize sz = win.bounds.size;
  CGFloat w = 52, h = 24;
  CGFloat x = sz.width > 100 ? (sz.width - w - 12) : 150;
  CGFloat y = 14;
  button.frame = CGRectMake(x, y, w, h);
  [win addSubview:button];
  [win bringSubviewToFront:button];
}

static void showModError(UIWindow* win, NSString* error) {
  UIViewController* vc = win.rootViewController;
  while (vc.presentedViewController) vc = vc.presentedViewController;
  UIAlertController* a = [UIAlertController alertControllerWithTitle:@"Mod chưa được áp dụng" message:error preferredStyle:UIAlertControllerStyleAlert];
  [a addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
  [vc presentViewController:a animated:YES completion:nil];
}
