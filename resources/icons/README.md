# Application Icons

This directory should contain application icons for different platforms.

## Required Files

### macOS
- `icon.icns` - macOS icon file (required for .app bundle)

Create from a 1024x1024 PNG:
```bash
# Create iconset directory
mkdir icon.iconset

# Generate all required sizes
sips -z 16 16 icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32 icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32 icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64 icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256 icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512 icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png

# Convert to icns
iconutil -c icns icon.iconset
```

### Windows
- `icon.ico` - Windows icon file (multi-resolution)

Create from PNG using ImageMagick:
```bash
convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
```

Or use an online converter like https://icoconvert.com/

### Linux
- `icon.png` - PNG icon (512x512 recommended)

Used in desktop files and application launchers.

## Placeholder Icons

If you don't have icons yet, the build will proceed without them. You can add them later by:
1. Creating the icon files
2. Placing them in this directory
3. Rebuilding the application with Phase 4
