#!/bin/bash
# Builds the self-contained "Výsledkový servis.app" (bundled Python) and a DMG.
# Usage: ./build_app.sh
set -e
cd "$(dirname "$0")"

APP_NAME="Výsledkový servis"
PY="${PY:-/usr/local/bin/python3}"

echo "[1/4] Instaluji PyInstaller (pokud chybí)…"
"$PY" -m pip install --quiet --upgrade pyinstaller

echo "[2/4] Sestavuji .app…"
rm -rf build dist
"$PY" -m PyInstaller --noconfirm --clean --windowed \
    --name "$APP_NAME" \
    --icon icon.icns \
    --osx-bundle-identifier cz.hasicovo.vysledkovyservis \
    --add-data "AdvancedResultWriting.py:appsrc" \
    --add-data "parser.py:appsrc" \
    --add-data "parsing_single.py:appsrc" \
    --add-data "parsing_single_multidiscipline.py:appsrc" \
    --add-data "parsing_ctif.py:appsrc" \
    --add-data "parsing_plamen.py:appsrc" \
    --add-data "parsing_dorost.py:appsrc" \
    --add-data "updater.py:appsrc" \
    --add-data "requirements.txt:appsrc" \
    --add-data "VERSION:appsrc" \
    --add-data "templates:appsrc/templates" \
    app_boot.py

APP="dist/$APP_NAME.app"

echo "[3/4] Podepisuji (ad-hoc)…"
codesign --force --deep --sign - "$APP" || true

echo "[4/4] Vytvářím DMG…"
STAGING="dist/dmg"
rm -rf "$STAGING"; mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "dist/VysledkovyServis.dmg"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGING" -ov -format UDZO "dist/VysledkovyServis.dmg" >/dev/null
rm -rf "$STAGING"

echo ""
echo "HOTOVO:"
echo "  App: $APP"
echo "  DMG: dist/VysledkovyServis.dmg"
