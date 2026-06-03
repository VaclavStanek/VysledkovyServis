"""PyInstaller entry point for the macOS .app bundle.

Seeds/updates the app code into a writable directory, then runs the Flask app
from there and opens the control UI in the default browser. Importing flask /
requests / xmltodict here ensures PyInstaller bundles them, since the actual
app code is executed dynamically (and wouldn't be seen by static analysis)."""

import os
import runpy
import subprocess
import sys
import threading
import time
import urllib.request

import flask          # noqa: F401  (force PyInstaller to bundle)
import requests       # noqa: F401
import xmltodict      # noqa: F401

PORT = 5100
URL = "http://127.0.0.1:%d/" % PORT


def bundled_src():
    """Directory holding the bundled code snapshot."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "appsrc")
    return os.path.dirname(os.path.abspath(__file__))


def open_browser_when_ready():
    for _ in range(160):  # ~40 s
        try:
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(0.25)
    subprocess.run(["/usr/bin/open", URL])


def main():
    src = bundled_src()
    sys.path.insert(0, src)
    import updater

    updater.ensure_seeded(src)

    # Best-effort auto-update on launch (silent on failure → keep current version)
    try:
        updater.update_from_github(timeout=8)
    except Exception:
        pass

    cd = updater.code_dir()
    os.chdir(cd)
    sys.path.insert(0, cd)
    os.environ["HV_PORT"] = str(PORT)

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    # Run the Flask app as __main__ (blocks until the app quits)
    runpy.run_path(os.path.join(cd, "AdvancedResultWriting.py"), run_name="__main__")


if __name__ == "__main__":
    main()
