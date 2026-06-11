"""PyInstaller entry point for the macOS .app bundle – a thin, stable launcher.

It seeds/updates the app code into a writable directory, runs the Flask server in a
background thread, then hands off to the *updatable* native UI (app_ui.py in the code
dir). Keeping menus/windows in app_ui means they ship via the in-app updater – no new
.app needed for UI changes. If a bad update makes app_ui fail to load, it falls back
to the copy bundled in the .app, so the app never bricks itself.

Importing flask / requests / xmltodict / webview here ensures PyInstaller bundles
them (the Flask app and app_ui are executed dynamically and aren't analyzed)."""

import importlib.util
import os
import runpy
import sys
import threading
import time
import urllib.request

import flask          # noqa: F401  (force PyInstaller to bundle)
import requests       # noqa: F401
import xmltodict      # noqa: F401
import webview        # noqa: F401
import webview.menu   # noqa: F401  (ensure the menu submodule is bundled for app_ui)

PORT = 5100
URL = "http://127.0.0.1:%d/" % PORT


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


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_ui(code_dir, src):
    # Prefer the updatable UI in the code dir; fall back to the bundled copy if a bad
    # update makes it fail to load, so a broken update can never brick the app.
    last_err = None
    for base in (code_dir, src):
        ui_path = os.path.join(base, "app_ui.py")
        if not os.path.isfile(ui_path):
            continue
        try:
            mod = _load_module("app_ui", ui_path)
            mod.run(URL, PORT, src, code_dir)
            return
        except Exception as ex:
            last_err = ex
            print("UI se nepodařilo spustit z %s: %s" % (base, ex))
    if last_err:
        raise last_err
    raise SystemExit("app_ui.py nenalezen")


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
    sys.path.insert(0, code_dir)  # so app_ui can `import updater` and friends

    # Flask runs in the background; the GUI must own the main thread on macOS
    threading.Thread(target=start_server, args=(code_dir,), daemon=True).start()
    wait_for_server()

    run_ui(code_dir, src)


if __name__ == "__main__":
    main()
