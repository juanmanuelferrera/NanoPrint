# Packaging (Standalone, No Dependencies)

We use PyInstaller to produce standalone binaries. This guide builds unsigned, non‑notarized artifacts per your request.

## Prepare icons from provided logo

Place your PNG under `assets/logo.png` and run:

```bash
# macOS .icns
mkdir -p assets/NanoPrint.iconset
sips -z 16 16     assets/logo.png --out assets/NanoPrint.iconset/icon_16x16.png
sips -z 32 32     assets/logo.png --out assets/NanoPrint.iconset/icon_16x16@2x.png
sips -z 32 32     assets/logo.png --out assets/NanoPrint.iconset/icon_32x32.png
sips -z 64 64     assets/logo.png --out assets/NanoPrint.iconset/icon_32x32@2x.png
sips -z 128 128   assets/logo.png --out assets/NanoPrint.iconset/icon_128x128.png
sips -z 256 256   assets/logo.png --out assets/NanoPrint.iconset/icon_128x128@2x.png
sips -z 256 256   assets/logo.png --out assets/NanoPrint.iconset/icon_256x256.png
sips -z 512 512   assets/logo.png --out assets/NanoPrint.iconset/icon_256x256@2x.png
sips -z 512 512   assets/logo.png --out assets/NanoPrint.iconset/icon_512x512.png
cp assets/logo.png assets/NanoPrint.iconset/icon_512x512@2x.png
iconutil -c icns assets/NanoPrint.iconset -o assets/NanoPrint.icns

# Windows .ico (requires ImageMagick)
convert assets/logo.png -define icon:auto-resize=256,128,64,48,32,16 assets/NanoPrint.ico
```

## Build environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pip install pyinstaller==6.6.0
```

## Build macOS .app and .dmg (unsigned, non‑notarized)

```bash
pyinstaller packaging/specs/nanorosetta_macos_app.spec
hdiutil create -volname "NanoPrint" -srcfolder dist/NanoPrint.app -ov -format UDZO dist/NanoPrint.dmg
```

## Build Windows 64‑bit one‑file .exe (unsigned)

```bash
pyinstaller packaging/specs/nanorosetta_windows_onefile.spec
```

Notes:
- These builds are fully standalone; users don’t need Python or packages installed.
- macOS Gatekeeper will warn for unsigned apps; users can Ctrl‑click → Open to run.
- Provide .icns/.ico created above; specs already point to `assets/NanoPrint.icns` and `assets/NanoPrint.ico`.
