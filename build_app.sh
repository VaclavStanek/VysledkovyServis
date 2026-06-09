#!/bin/bash
# Builds the self-contained "Výsledkový servis.app" (bundled Python) and a DMG.
# Usage: ./build_app.sh
set -e
cd "$(dirname "$0")"

APP_NAME="Výsledkový servis"
PY="${PY:-/usr/local/bin/python3}"

echo "[1/4] Instaluji závislosti (PyInstaller + requirements)…"
"$PY" -m pip install --quiet --upgrade pyinstaller
"$PY" -m pip install --quiet -r requirements.txt

echo "[2/4] Sestavuji .app…"
rm -rf build dist
"$PY" -m PyInstaller --noconfirm --clean --windowed \
    --name "$APP_NAME" \
    --icon icon.icns \
    --osx-bundle-identifier cz.hasicovo.vysledkovyservis \
    --collect-all webview \
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

echo "[3/4] Podepisuji ad-hoc inside-out (--deep na macOS 26 padá SIGBUSem)…"
# Smaž extended attributes (FinderInfo apod.) – jinak codesign hlásí "sealed resource is invalid".
xattr -cr "$APP"
# Pořadí je klíčové: nejdřív vnořené Mach-O knihovny, pak verzované frameworky, pak vnořené
# .app, a nakonec vnější bundle. Jinak zůstane podpis nekonzistentní (typicky Python.framework)
# a appka hlásí "je poškozena".
find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" \) -print0 \
    | while IFS= read -r -d '' f; do codesign --force --sign - "$f"; done
# Frameworky: podepiš konkrétní verzi (ne symlink Current/root), pak framework jako celek.
find "$APP/Contents" -type d -name "*.framework" -print0 \
    | while IFS= read -r -d '' fw; do
        for ver in "$fw"/Versions/*/; do
            [ -d "$ver" ] && [ "$(basename "$ver")" != "Current" ] && codesign --force --sign - "$ver"
        done
        codesign --force --sign - "$fw"
      done
find "$APP/Contents" -type d -name "*.app" -print0 \
    | while IFS= read -r -d '' b; do codesign --force --sign - "$b"; done
codesign --force --sign - "$APP/Contents/MacOS/$APP_NAME"
codesign --force --sign - "$APP"
# Pozn.: ad-hoc podpis PyInstaller bundlu neprojde `codesign --verify --strict` (kvůli layoutu),
# ale appka se po SMAZÁNÍ KARANTÉNY normálně spustí. Plné ověření vyžaduje notarizaci
# (Apple Developer ID, $99/rok). Stažený DMG proto vždy potřebuje krok s `xattr` – viz README.
codesign -dv "$APP" 2>&1 | grep -i "Signature=" || true

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
