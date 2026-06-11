"""Updatable native UI – menus, windows, Stream Deck / Companion installers.

Loaded from the writable code dir by the thin app_boot launcher, so everything here
ships via the in-app updater: change a menu or window and users get it on the next
launch, no new .app needed. Only uses libraries already bundled in the .app (webview
+ stdlib) – adding a new dependency or changing the launcher still needs a rebuild."""

import json
import os
import shutil
import struct
import subprocess
import time
import zlib

import webview
from webview.menu import Menu, MenuAction

# Filled in by run() from the launcher – the URL/port of the local Flask server and
# the two places code can live (writable code dir, then the bundled snapshot).
_URL = ""
_PORT = 5100
_BUNDLED_SRC = ""
_CODE_DIR = ""

STREAMDECK_PLUGIN = "cz.vysledkovyservis.sdPlugin"
STREAMDECK_PLUGINS_DIR = os.path.expanduser(
    "~/Library/Application Support/com.elgato.StreamDeck/Plugins")
# Pre-built Bitfocus Companion module bundle (Companion has no auto-load folder).
COMPANION_MODULE_TGZ = "vysledkovyservis.tgz"


def _hex_to_rgb(color):
    h = color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _solid_png(width, height, rgb):
    # Hand-rolled PNG encoder (stdlib only) for a single solid color – used by the
    # "download keying background" button. Avoids pulling in Pillow just for a fill.
    r, g, b = rgb
    row = bytes([0]) + bytes([r, g, b]) * width  # filter type 0 + RGB pixels
    raw = row * height
    compressed = zlib.compress(raw, 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def _streamdeck_plugin_src():
    # Prefer the self-updated copy in the code dir, fall back to the bundled snapshot
    for base in (_CODE_DIR, _BUNDLED_SRC):
        candidate = os.path.join(base, "streamdeck", STREAMDECK_PLUGIN)
        if os.path.isdir(candidate):
            return candidate
    return None


def _companion_module_src():
    for base in (_CODE_DIR, _BUNDLED_SRC):
        candidate = os.path.join(base, "companion-modules", COMPANION_MODULE_TGZ)
        if os.path.isfile(candidate):
            return candidate
    return None


def install_streamdeck_plugin():
    """Copy the bundled Stream Deck plugin into Stream Deck and restart it.
    Returns (ok, message) for display in an alert."""
    src = _streamdeck_plugin_src()
    if not src:
        return False, "Plugin se v aplikaci nepodařilo najít."

    # Stream Deck keeps its data under com.elgato.StreamDeck; a missing folder means
    # Stream Deck almost certainly isn't installed on this Mac.
    if not os.path.isdir(os.path.dirname(STREAMDECK_PLUGINS_DIR)):
        return False, ("Nenašel jsem aplikaci Stream Deck. Nainstaluj nejdřív Elgato "
                       "Stream Deck a zkus to znovu.")

    dest = os.path.join(STREAMDECK_PLUGINS_DIR, STREAMDECK_PLUGIN)
    try:
        os.makedirs(STREAMDECK_PLUGINS_DIR, exist_ok=True)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    except OSError as ex:
        return False, "Kopírování pluginu selhalo: " + str(ex)

    # Restart Stream Deck so it picks up the freshly installed plugin
    try:
        subprocess.run(["osascript", "-e", 'quit app "Stream Deck"'], check=False, timeout=10)
        time.sleep(1)
        subprocess.run(["open", "-a", "Stream Deck"], check=False, timeout=10)
    except Exception:
        pass  # plugin is installed regardless; a manual restart still works

    return True, ("Plugin nainstalován. Stream Deck se restartuje – akce najdeš "
                  "v kategorii „Výsledkový servis“.")


class Api:
    """Exposed to the page as window.pywebview.api"""
    def open_overlay(self):
        # Second native window for the overlay (fullscreen it, capture in OBS)
        webview.create_window("Overlay – výsledky (OBS)", _URL + "overlay",
                              width=1280, height=720)

    def save_background(self, color, width, height):
        # Save a solid keying-color PNG via a native dialog. WKWebView can't trigger
        # anchor downloads, so the file is written from Python instead of the page.
        try:
            rgb = _hex_to_rgb(color)
            w, h = max(1, int(width)), max(1, int(height))
        except (ValueError, TypeError, IndexError):
            return {"ok": False, "error": "Neplatné parametry pozadí."}

        filename = "pozadi_%s_%dx%d.png" % (color.lstrip("#"), w, h)
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG, save_filename=filename)
        if not result:
            return {"ok": False, "cancelled": True}

        path = result[0] if isinstance(result, (list, tuple)) else result
        try:
            with open(path, "wb") as f:
                f.write(_solid_png(w, h, rgb))
        except OSError as ex:
            return {"ok": False, "error": str(ex)}
        return {"ok": True, "path": path}


def run(url, port, bundled_src, code_dir):
    """Build the native menus and window, then block on webview until the app quits.
    Called by the launcher on the main thread after the Flask server is up."""
    global _URL, _PORT, _BUNDLED_SRC, _CODE_DIR
    _URL, _PORT, _BUNDLED_SRC, _CODE_DIR = url, port, bundled_src, code_dir

    import updater  # bundled copy is fine – only its stable API is used here

    def _alert(text):
        try:
            webview.windows[0].evaluate_js("window.alert(%s)" % json.dumps(text))
        except Exception:
            pass

    def _confirm(text):
        # window.confirm gives a native OK/Cancel dialog – OK = the "update" button
        try:
            return bool(webview.windows[0].evaluate_js("window.confirm(%s)" % json.dumps(text)))
        except Exception:
            return False

    def check_for_updates():
        local = updater.current_version()
        ok, remote = updater.latest_version()
        if not ok:
            _alert("⚠️ Nepodařilo se zjistit nejnovější verzi:\n" + remote)
            return
        if remote == local:
            _alert("✅ Máš aktuální verzi (v%s)." % local)
            return
        if not _confirm("Je dostupná nová verze v%s (máš v%s).\n\nStáhnout a nainstalovat?"
                        % (remote, local)):
            return
        ok2, msg = updater.update_from_github()
        if ok2:
            _alert("✅ " + msg + "\n\nZměny se projeví po zavření a opětovném otevření aplikace.")
        else:
            _alert("⚠️ " + msg)

    def install_plugin():
        ok, msg = install_streamdeck_plugin()
        _alert(("✅ " + msg) if ok else ("⚠️ " + msg))

    def save_companion_module():
        # Companion can't auto-load modules, so we hand the user the ready .tgz to import.
        src = _companion_module_src()
        if not src:
            _alert("⚠️ Modul pro Companion se v aplikaci nenašel.")
            return
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG, save_filename="vysledkovyservis-companion.tgz")
        if not result:
            return
        path = result[0] if isinstance(result, (list, tuple)) else result
        try:
            shutil.copyfile(src, path)
        except OSError as ex:
            _alert("⚠️ Uložení modulu selhalo: " + str(ex))
            return
        try:
            subprocess.run(["open", "-R", path], check=False, timeout=10)  # reveal in Finder
        except Exception:
            pass
        _alert("✅ Modul pro Companion uložen.\n\nV Bitfocus Companion:\n"
               "Connections → + Add connection → Import custom module → vyber uložený soubor.\n"
               "Pak přidej připojení „Výsledkový servis“ a zadej adresu 127.0.0.1:%d.\n\n"
               "Celý návod: menu Companion → Návod k nastavení." % _PORT)

    def open_companion_help():
        webview.create_window("Companion – návod k nastavení", _URL + "companion",
                              width=760, height=820)

    sd_addr = "127.0.0.1:%d" % _PORT

    def show_sd_addr():
        _alert("Do pole host:port ve Stream Decku zadej tuhle adresu:\n\n" + sd_addr)

    app_menu = [
        Menu("Aktualizace", [
            MenuAction("Zkontrolovat aktualizace", check_for_updates),
        ]),
        Menu("Stream Deck", [
            MenuAction("Nainstalovat plugin do Stream Decku", install_plugin),
            MenuAction("Adresa pro plugin:  " + sd_addr, show_sd_addr),
        ]),
        Menu("Companion", [
            MenuAction("Návod k nastavení…", open_companion_help),
            MenuAction("Připravit modul pro Companion…", save_companion_module),
            MenuAction("Adresa pro modul:  " + sd_addr, show_sd_addr),
        ]),
    ]

    webview.create_window("Výsledkový servis", _URL,
                          width=1080, height=900, min_size=(760, 600),
                          js_api=Api())
    webview.start(menu=app_menu)  # blocks on main thread until all windows close
