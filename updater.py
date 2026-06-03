"""Self-update for the bundled Mac app – downloads the latest code from the
public GitHub repo as a ZIP (no git required) and writes it into a writable
code directory. The .app bundle itself is never modified."""

import io
import os
import shutil
import tempfile
import urllib.request
import zipfile

APP_NAME = "VysledkovyServis"
ZIP_URL = "https://github.com/VaclavStanek/VysledkovyServis/archive/refs/heads/main.zip"

# Files/dirs that make up the runnable app (seeded and updated)
CODE_ITEMS = [
    "AdvancedResultWriting.py", "parser.py",
    "parsing_single.py", "parsing_single_multidiscipline.py",
    "parsing_ctif.py", "parsing_plamen.py", "parsing_dorost.py",
    "updater.py", "requirements.txt", "VERSION", "templates",
]
# User data that must survive updates
PRESERVE = {"config.json"}


def code_dir():
    base = os.path.expanduser(os.path.join("~/Library/Application Support", APP_NAME))
    return os.path.join(base, "app")


def _copy_item(src_root, dst_root, item):
    s = os.path.join(src_root, item)
    d = os.path.join(dst_root, item)
    if os.path.isdir(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
    elif os.path.exists(s):
        shutil.copy2(s, d)


def ensure_seeded(src_dir):
    """Populate the code dir from a bundled snapshot on first run."""
    cd = code_dir()
    if os.path.exists(os.path.join(cd, "AdvancedResultWriting.py")):
        return
    os.makedirs(cd, exist_ok=True)
    for item in CODE_ITEMS + list(PRESERVE):
        _copy_item(src_dir, cd, item)


def current_version():
    try:
        with open(os.path.join(code_dir(), "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "?"


def update_from_github(timeout=10):
    """Download the latest ZIP and refresh the code dir. Returns (ok, message)."""
    cd = code_dir()
    tmp = None
    try:
        req = urllib.request.Request(ZIP_URL, headers={"User-Agent": APP_NAME})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        zf = zipfile.ZipFile(io.BytesIO(data))
        tmp = tempfile.mkdtemp()
        zf.extractall(tmp)
        roots = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        if not roots:
            return False, "Stažený archiv je prázdný."
        root = os.path.join(tmp, roots[0])
        os.makedirs(cd, exist_ok=True)
        for item in CODE_ITEMS:  # PRESERVE (config.json) is intentionally left untouched
            _copy_item(root, cd, item)
        return True, "Aktualizováno na verzi " + current_version() + "."
    except Exception as ex:
        return False, "Aktualizace se nezdařila: " + str(ex)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
