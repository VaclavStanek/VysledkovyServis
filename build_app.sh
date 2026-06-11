#!/bin/bash
# Builds the self-contained "Výsledkový servis.app" (bundled Python) and a DMG.
# Usage: ./build_app.sh
set -e
cd "$(dirname "$0")"

# Pozor na název spustitelného souboru: musí být ASCII (bez diakritiky a mezer).
# Když je v něm diakritika ("Výsledkový servis"), codesign ho kvůli Unicode
# normalizaci (NFD na disku vs. NFC v Info.plist) nedokáže spárovat s
# CFBundleExecutable, takže HLAVNÍ binárku zapečetí jako vnořený resource. Tím
# vznikne neuspokojitelná kruhová závislost cdhash → "a sealed resource is missing
# or invalid" → Gatekeeper appku hlásí jako "poškozenou" a jediná záchrana je `xattr`.
# ASCII jméno tohle odstraní (verify --strict projde, spctl vrátí jen "rejected" =
# nenotarizováno → uživatel dostane jednorázové "Otevřít přesto", žádný Terminál).
# Hezký název pro Finder/menu se vrátí přes CFBundleDisplayName + přejmenování bundlu.
BUILD_NAME="VysledkovyServis"
DISPLAY_NAME="Výsledkový servis"
PY="${PY:-/usr/local/bin/python3}"

echo "[1/5] Instaluji závislosti (PyInstaller + requirements)…"
"$PY" -m pip install --quiet --upgrade pyinstaller
"$PY" -m pip install --quiet -r requirements.txt

echo "[2/5] Sestavuji .app…"
rm -rf build dist
"$PY" -m PyInstaller --noconfirm --clean --windowed \
    --name "$BUILD_NAME" \
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
    --add-data "streamdeck/cz.vysledkovyservis.sdPlugin:appsrc/streamdeck/cz.vysledkovyservis.sdPlugin" \
    --add-data "companion-modules/vysledkovyservis.tgz:appsrc/companion-modules" \
    app_boot.py

BUILD_APP="dist/$BUILD_NAME.app"
APP="dist/$DISPLAY_NAME.app"

echo "[3/5] Nastavuji zobrazovaný název a přejmenovávám bundle…"
# CFBundleExecutable zůstává ASCII (nesahat na něj) – jen doplníme hezký název pro UI.
/usr/bin/plutil -replace CFBundleDisplayName -string "$DISPLAY_NAME" "$BUILD_APP/Contents/Info.plist"
/usr/bin/plutil -replace CFBundleName -string "$DISPLAY_NAME" "$BUILD_APP/Contents/Info.plist"
# Název bundlu (adresáře) může diakritiku mít – do code-sealu nevstupuje.
rm -rf "$APP"
mv "$BUILD_APP" "$APP"

echo "[4/5] Podepisuji ad-hoc inside-out…"
# Smaž extended attributes (FinderInfo apod.) – jinak codesign hlásí "sealed resource is invalid".
xattr -cr "$APP"
# Pořadí je klíčové: nejdřív vnořené Mach-O knihovny, pak verzované frameworky a nakonec
# vnější bundle (ten podepíše i hlavní binárku v MacOS/). Díky ASCII názvu se hlavní
# binárka korektně vyloučí z resource pečeti a podpis je konzistentní.
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
codesign --force --sign - "$APP"
# Pojistka: pokud by se kvůli změně layoutu pečeť zase rozbila, build TVRDĚ spadne,
# ať nikdy nevypustíme bundle, který Gatekeeper označí za "poškozený".
echo "  Ověřuji podpis (codesign --verify --strict)…"
codesign --verify --strict "$APP"
echo "  Podpis OK – verify --strict prošel (Gatekeeper: nenotarizováno, ne 'poškozeno')."

echo "[5/5] Vytvářím DMG…"
STAGING="dist/dmg"
rm -rf "$STAGING"; mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
rm -f "dist/VysledkovyServis.dmg"
hdiutil create -volname "$DISPLAY_NAME" -srcfolder "$STAGING" -ov -format UDZO "dist/VysledkovyServis.dmg" >/dev/null
rm -rf "$STAGING"

echo ""
echo "HOTOVO:"
echo "  App: $APP"
echo "  DMG: dist/VysledkovyServis.dmg"
