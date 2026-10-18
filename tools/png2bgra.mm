#import <AppKit/AppKit.h>
#import <CoreGraphics/CoreGraphics.h>
#include <cstdio>
#include <cstdlib>

int main(int argc, char* argv[]) {
    if (argc < 5) {
        fprintf(stderr, "Usage: png2bgra <input.png> <width> <height> <output.raw>\n");
        return 1;
    }
    const char* inPath = argv[1];
    int width = atoi(argv[2]);
    int height = atoi(argv[3]);
    const char* outPath = argv[4];

    @autoreleasepool {
        NSString* path = [NSString stringWithUTF8String:inPath];
        NSImage* img = [[NSImage alloc] initWithContentsOfFile:path];
        if (!img) {
            fprintf(stderr, "Failed to load image: %s\n", inPath);
            return 1;
        }

        size_t bytesCount = width * height * 4;
        uint8_t* buffer = (uint8_t*)calloc(1, bytesCount);
        if (!buffer) return 1;

        CGColorSpaceRef cs = CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
        CGContextRef ctx = CGBitmapContextCreate(buffer, width, height, 8, width * 4, cs,
                                                kCGBitmapByteOrder32Little | kCGImageAlphaPremultipliedFirst);
        CGColorSpaceRelease(cs);

        if (!ctx) {
            free(buffer);
            return 1;
        }

        // Draw image scaled while preserving aspect ratio, centered in width x height box
        CGFloat imgW = img.size.width;
        CGFloat imgH = img.size.height;
        CGFloat scale = MIN((CGFloat)width / imgW, (CGFloat)height / imgH);
        CGFloat drawW = imgW * scale;
        CGFloat drawH = imgH * scale;
        CGFloat drawX = ((CGFloat)width - drawW) / 2.0;
        CGFloat drawY = ((CGFloat)height - drawH) / 2.0;

        NSGraphicsContext* nsCtx = [NSGraphicsContext graphicsContextWithCGContext:ctx flipped:NO];
        [NSGraphicsContext saveGraphicsState];
        [NSGraphicsContext setCurrentContext:nsCtx];

        [img drawInRect:NSMakeRect(drawX, drawY, drawW, drawH)
               fromRect:NSZeroRect
              operation:NSCompositingOperationCopy
               fraction:1.0];

        [NSGraphicsContext restoreGraphicsState];
        CGContextRelease(ctx);

        FILE* fp = fopen(outPath, "wb");
        if (!fp) {
            free(buffer);
            return 1;
        }
        fwrite(buffer, 1, bytesCount, fp);
        fclose(fp);
        free(buffer);
    }
    return 0;
}
