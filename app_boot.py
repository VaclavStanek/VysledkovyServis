"""PyInstaller entry point for the macOS .app bundle.

Seeds/updates the app code into a writable directory, runs the Flask server in a
background thread, and shows the control UI in a native window (pywebview /
WKWebView) – no browser. The overlay opens as a second native window that can be
fullscreened and captured in OBS.

Importing flask / requests / xmltodict / webview here ensures PyInstaller bundles
them, since the Flask app itself is executed dynamically."""

import json
import os
import runpy
import struct
import sys
import threading
import time
import urllib.request
import zlib

import flask          # noqa: F401  (force PyInstaller to bundle)
import requests       # noqa: F401
import xmltodict      # noqa: F401
import webview

PORT = 5100
URL = "http://127.0.0.1:%d/" % PORT


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


def bundled_src():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "appsrc")
    return os.path.dirname(os.path.abspath(__file__))


def wait_for_server(timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def start_server(code_dir):
    os.chdir(code_dir)
    sys.path.insert(0, code_dir)
    os.environ["HV_PORT"] = str(PORT)
    runpy.run_path(os.path.join(code_dir, "AdvancedResultWriting.py"), run_name="__main__")


class Api:
    """Exposed to the page as window.pywebview.api"""
    def open_overlay(self):
        # Second native window for the overlay (fullscreen it, capture in OBS)
        webview.create_window("Overlay – výsledky (OBS)", URL + "overlay",
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


def main():
    src = bundled_src()
    sys.path.insert(0, src)
    import updater

    updater.ensure_seeded(src)
    try:
        updater.update_from_github(timeout=8)
    except Exception:
        pass

    code_dir = updater.code_dir()

    # Flask runs in the background; the GUI must own the main thread on macOS
    threading.Thread(target=start_server, args=(code_dir,), daemon=True).start()
    wait_for_server()

    def check_for_updates():
        ok, msg = updater.update_from_github()
        text = ("✅ " + msg + "\n\nZměny se projeví po zavření a opětovném otevření aplikace.")
        if not ok:
            text = "⚠️ " + msg
        try:
            webview.windows[0].evaluate_js("window.alert(%s)" % json.dumps(text))
        except Exception:
            pass

    from webview.menu import Menu, MenuAction
    app_menu = [
        Menu("Aktualizace", [
            MenuAction("Zkontrolovat aktualizace", check_for_updates),
        ]),
    ]

    webview.create_window("Výsledkový servis", URL,
                          width=1080, height=900, min_size=(760, 600),
                          js_api=Api())
    webview.start(menu=app_menu)  # blocks on main thread until all windows close


if __name__ == "__main__":
    main()
