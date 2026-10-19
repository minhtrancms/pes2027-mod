CXX ?= g++
CXXFLAGS ?= -std=c++17 -O1 -g -Wall -Wno-unused

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  CRYPTO_LIBS ?= -framework Security
else
  CRYPTO_LIBS ?= -lcrypto
endif

CORE = core/jvalue.cpp core/codec.cpp core/store.cpp core/server.cpp core/zipread.cpp

all: build/runcpp build/packtest build/gameplaytest build/modtest build/zipcheck

build/gameplaytest: $(CORE) test/gameplaytest.cpp core/*.hpp core/*.inc
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $(CORE) test/gameplaytest.cpp -lz -lsqlite3 $(CRYPTO_LIBS)

build/runcpp: $(CORE) test/runcpp.cpp core/*.hpp core/*.inc
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $(CORE) test/runcpp.cpp -lz -lsqlite3 $(CRYPTO_LIBS)

build/zipcheck: core/zipread.cpp test/zipcheck.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ core/zipread.cpp test/zipcheck.cpp -lz

build/packtest: core/datapack.cpp core/zipread.cpp core/jvalue.cpp test/packtest.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ core/datapack.cpp core/zipread.cpp core/jvalue.cpp test/packtest.cpp -lz

build/modtest: core/modpack.cpp core/datapack.cpp core/zipread.cpp core/jvalue.cpp test/modtest.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ core/modpack.cpp core/datapack.cpp core/zipread.cpp core/jvalue.cpp test/modtest.cpp -lz

build/ZiruOffline.dylib:
	mkdir -p build
	xcrun --sdk iphoneos clang++ -arch arm64 -isysroot $$(xcrun --sdk iphoneos --show-sdk-path) -miphoneos-version-min=15.0 \
	  -std=c++17 -O2 -fobjc-arc -fvisibility=hidden -Wall -Wno-unused \
	  -dynamiclib -install_name @executable_path/Frameworks/ZiruOffline.dylib \
	  ios/ZiruOffline.mm ios/ZiruFontPak.mm ios/ZiruWebView.mm core/jvalue.cpp core/codec.cpp core/store.cpp core/server.cpp core/zipread.cpp core/datapack.cpp core/modpack.cpp \
	  -framework Foundation -framework UIKit -framework UniformTypeIdentifiers -framework Security -framework QuartzCore -framework CoreGraphics -framework WebKit \
	  -lz -lsqlite3 -o $@
	codesign -f -s - $@

dylib: build/ZiruOffline.dylib

test: all
	./build/gameplaytest
	rm -rf /tmp/mod-test && python3 test/mod_fixtures.py /tmp/mod-test && ./build/modtest /tmp/mod-test
	python3 -m unittest discover -s test -p 'ios_tables_test.py' -v
	.venv/bin/python3 -m unittest discover -s online -p 'test_online_server.py' -v

clean:
	rm -rf build /tmp/mod-test
