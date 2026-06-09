#!/usr/bin/env bash
# Nainstaluje plugin do Stream Decku (zkopíruje do složky pluginů a restartuje app).
set -e

SRC="$(cd "$(dirname "$0")" && pwd)/cz.vysledkovyservis.sdPlugin"
DEST="$HOME/Library/Application Support/com.elgato.StreamDeck/Plugins"

if [ ! -d "$SRC" ]; then
    echo "Chyba: nenalezen $SRC"
    exit 1
fi

mkdir -p "$DEST"
rm -rf "$DEST/cz.vysledkovyservis.sdPlugin"
cp -R "$SRC" "$DEST/"
echo "✅ Plugin nainstalován do:"
echo "   $DEST/cz.vysledkovyservis.sdPlugin"

# Restart Stream Decku, aby plugin načetl
osascript -e 'quit app "Stream Deck"' 2>/dev/null || true
sleep 1
open -a "Stream Deck" 2>/dev/null || true
echo "✅ Stream Deck restartován. Plugin najdeš v kategorii „Výsledkový servis“."
