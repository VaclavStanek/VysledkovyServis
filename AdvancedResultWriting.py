# Final production-ready version of AutomaticResultWriting.py (optimized and functional)

import requests
import xmltodict
import os
import re
import json
import time
import threading
from flask import Flask, request, render_template, redirect, jsonify
from parser import parse_race_data, determine_event_list

# Flask app setup
app = Flask(__name__)

@app.after_request
def allow_cors(response):
    # Local control API – the Stream Deck plugin fetches these from its embedded browser
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# Global state
is_running = False
current_thread = None
# Latest parsed result served to the local overlay (replaces Singular output)
latest_data = {}
# Most recent raw XML, cached so settings changes can re-render instantly (no re-fetch)
last_race_data = None

# Params and methods for loading XML URL from file
CONFIG_FILE = "config.json"
DEFAULT_XMLURL = "https://pozarnisport.hasicovo.cz/export_xml/show/532"
# Default Apps Script Web App URL offered when picking the "Google Tabulka" source.
# Set this to your deployed Web App URL so it's prefilled. Not a real secret (returns
# only the running-team rows), but keep it out of public places if you want it private.
DEFAULT_SHEET_URL = ""

def load_config_data():
    # config.json holds user runtime data (last race URL, prepared nameplate list).
    # It is in the updater PRESERVE set, so it survives in-app updates.
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_config_data(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def load_config():
    return load_config_data().get("last_url", DEFAULT_XMLURL)

def save_config(url):
    # Read-modify-write so saving the URL never drops other keys (e.g. nameplate list)
    data = load_config_data()
    data["last_url"] = url
    save_config_data(data)

def normalize_xml_url(input_value):
    if input_value.isdigit():
        return f"https://pozarnisport.hasicovo.cz/export_xml/show/{input_value}"
    if "pozarnisport.hasicovo.cz" in input_value:
        return input_value
    return None

# Settings
# No race is loaded on startup – the user must pick one via the modal (empty state).
XMLurl = ""
# Data source of the current "race": "hasicovo" (XML) or "sheet" (Google Sheet lišta).
race_source = "hasicovo"

# Checkbox state
show_results_table = False
show_racers_list = False
show_total_results_table = False
# Auto-rotate the result table pages in the overlay. When off, the page is driven
# manually (page number field / Stream Deck "strana" buttons) via sel_page.
auto_paging = True
# Workaround: hasicovo.cz sometimes appends a stray "a" to every team/racer name.
# Modes: "auto" (decide per race via detection), "on" (always trim), "off" (never).
strip_mode = "auto"

# Current selection, persisted across requests. Broadcasting never starts implicitly here –
# it is triggered explicitly from the "select race" modal (see /start_race).
sel_category = ""
sel_event = ""
sel_page = "1"

# Events and categories
events_list = []
categories = []
race_type = ""
race = {}

# ---------------------------------------------------------------------------
# Nameplate (lower-third) – a manually driven caption independent of the race
# XML pipeline. Works with or without a loaded race, so it can be reused on any
# stream. Country -> ISO2 (emoji flag) + international 3-letter abbreviation.
# ---------------------------------------------------------------------------
COUNTRIES = [
    # (český název, ISO2 pro vlajku, mezinárodní 3písmenná zkratka)
    ("Česká republika", "CZ", "CZE"),
    ("Slovensko", "SK", "SVK"),
    ("Polsko", "PL", "POL"),
    ("Německo", "DE", "GER"),
    ("Rakousko", "AT", "AUT"),
    ("Maďarsko", "HU", "HUN"),
    ("Slovinsko", "SI", "SVN"),
    ("Chorvatsko", "HR", "CRO"),
    ("Srbsko", "RS", "SRB"),
    ("Bosna a Hercegovina", "BA", "BIH"),
    ("Bulharsko", "BG", "BUL"),
    ("Rumunsko", "RO", "ROU"),
    ("Ukrajina", "UA", "UKR"),
    ("Bělorusko", "BY", "BLR"),
    ("Rusko", "RU", "RUS"),
    ("Švýcarsko", "CH", "SUI"),
    ("Lichtenštejnsko", "LI", "LIE"),
    ("Itálie", "IT", "ITA"),
    ("Francie", "FR", "FRA"),
    ("Belgie", "BE", "BEL"),
    ("Nizozemsko", "NL", "NED"),
    ("Lucembursko", "LU", "LUX"),
    ("Španělsko", "ES", "ESP"),
    ("Portugalsko", "PT", "POR"),
    ("Velká Británie", "GB", "GBR"),
    ("Irsko", "IE", "IRL"),
    ("Dánsko", "DK", "DEN"),
    ("Norsko", "NO", "NOR"),
    ("Švédsko", "SE", "SWE"),
    ("Finsko", "FI", "FIN"),
    ("Estonsko", "EE", "EST"),
    ("Lotyšsko", "LV", "LAT"),
    ("Litva", "LT", "LTU"),
    ("Řecko", "GR", "GRE"),
    ("Turecko", "TR", "TUR"),
    ("Severní Makedonie", "MK", "MKD"),
    ("Černá Hora", "ME", "MNE"),
    ("Albánie", "AL", "ALB"),
    ("Kosovo", "XK", "KOS"),
    ("Moldavsko", "MD", "MDA"),
    ("Island", "IS", "ISL"),
    ("Spojené státy", "US", "USA"),
    ("Kanada", "CA", "CAN"),
    ("Čína", "CN", "CHN"),
    ("Japonsko", "JP", "JPN"),
    ("Jižní Korea", "KR", "KOR"),
    ("Kazachstán", "KZ", "KAZ"),
    ("Austrálie", "AU", "AUS"),
    ("Jihoafrická republika", "ZA", "RSA"),
]
# Lookup by lowercased name, abbreviation and ISO2, for resolving typed input
_COUNTRY_BY_NAME = {name.lower(): (name, iso2, abbr) for name, iso2, abbr in COUNTRIES}
_COUNTRY_BY_ABBR = {abbr.lower(): (name, iso2, abbr) for name, iso2, abbr in COUNTRIES}
_COUNTRY_BY_ISO2 = {iso2.lower(): (name, iso2, abbr) for name, iso2, abbr in COUNTRIES}

# English / native aliases -> ISO2 (Google Sheet uses English names like "Finland",
# plus native quirks like "Italia"). Maps onto the COUNTRIES table for flag + abbr.
COUNTRY_ALIASES = {
    "czechia": "CZ", "czech republic": "CZ",
    "slovakia": "SK", "poland": "PL", "germany": "DE", "austria": "AT",
    "hungary": "HU", "slovenia": "SI", "croatia": "HR", "serbia": "RS",
    "bosnia and herzegovina": "BA", "bosnia": "BA", "bulgaria": "BG",
    "romania": "RO", "ukraine": "UA", "belarus": "BY", "russia": "RU",
    "switzerland": "CH", "liechtenstein": "LI", "italy": "IT", "italia": "IT",
    "france": "FR", "belgium": "BE", "netherlands": "NL",
    "luxembourg": "LU", "luxemburg": "LU", "spain": "ES", "portugal": "PT",
    "united kingdom": "GB", "great britain": "GB", "uk": "GB", "england": "GB",
    "ireland": "IE", "denmark": "DK", "norway": "NO", "sweden": "SE",
    "finland": "FI", "estonia": "EE", "latvia": "LV", "lithuania": "LT",
    "greece": "GR", "turkey": "TR", "türkiye": "TR", "turkiye": "TR",
    "north macedonia": "MK", "macedonia": "MK", "montenegro": "ME",
    "albania": "AL", "kosovo": "XK", "moldova": "MD", "iceland": "IS",
    "united states": "US", "united states of america": "US", "usa": "US",
    "canada": "CA", "china": "CN", "japan": "JP", "south korea": "KR",
    "korea": "KR", "kazakhstan": "KZ", "australia": "AU", "south africa": "ZA",
}

def flag_emoji(iso2):
    # ISO2 country code -> regional-indicator emoji flag ("CZ" -> "🇨🇿")
    if not iso2 or len(iso2) != 2 or not iso2.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())

def resolve_country(text):
    # Turn a typed/looked-up country name/abbr/English-alias into {title, flag, abbr}.
    # Unknown input is passed through as a plain title with no flag/abbr.
    key = (text or "").strip()
    if not key:
        return {"title": "", "flag": "", "abbr": ""}
    low = key.lower()
    entry = _COUNTRY_BY_NAME.get(low) or _COUNTRY_BY_ABBR.get(low)
    if not entry and low in COUNTRY_ALIASES:
        entry = _COUNTRY_BY_ISO2.get(COUNTRY_ALIASES[low].lower())
    if entry:
        name, iso2, abbr = entry
        return {"title": name, "flag": flag_emoji(iso2), "abbr": abbr}
    return {"title": key, "flag": "", "abbr": ""}

def countries_for_ui():
    # Serializable list for the control panel (datalist + row flag/abbr display)
    return [{"name": name, "abbr": abbr, "flag": flag_emoji(iso2)} for name, iso2, abbr in COUNTRIES]

# Nameplate live state (what is currently on air). Never persisted – only the
# prepared country list is saved to config.json ("nameplate" key).
nameplate_on = False
nameplate_name = ""      # main line (person name, or a country name, or anything)
nameplate_flag = ""      # emoji flag of the picked country (optional)
nameplate_abbr = ""      # international 3-letter code of the picked country (optional)
nameplate_role = ""      # secondary line (function/role)

def nameplate_payload():
    # Merged into /data when the nameplate is on air; buildView() checks it first.
    return {
        "nameplateVisible": True,
        "nameplateName": nameplate_name,
        "nameplateFlag": nameplate_flag,
        "nameplateAbbr": nameplate_abbr,
        "nameplateRole": nameplate_role,
        "autoPaging": True,
    }

def nameplate_status():
    return {
        "on": nameplate_on,
        "name": nameplate_name,
        "flag": nameplate_flag,
        "abbr": nameplate_abbr,
        "role": nameplate_role,
    }

# ---------------------------------------------------------------------------
# Running-team lišta from a Google Sheet via an Apps Script Web App (returns JSON).
# The sheet stays PRIVATE; the Web App runs as the owner and exposes only the rows – so
# NO API key / service account / google-auth is needed, just an HTTP GET (like the XML).
# Sheet columns (matched by header): startovní číslo | družstvo | Stát | [kategorie] |
#   právě běží <disciplína> …   (marker non-empty = running in that discipline)
# ---------------------------------------------------------------------------
SHEET_POLL_SEC = 4

# Live state (not persisted; only the Web App URL / label / discipline names are in config.json).
# The lišta is "on air" when race_source == "sheet" and is_running (normal start/stop).
sheet_mode = "auto"        # "auto" (rows marked in the sheet) | "manual" (operator picks)
sheet_sel_nums = set()     # manual mode: selected start numbers (multi-select, toggle)
sheet_discipline = 0       # index of the active discipline (marker column) shown in the lišta
sheet_disciplines = []     # [{key, name}] detected from marker columns
sheet_category = ""        # optional category filter ("" = all); from a "kategorie" column
sheet_rows = []            # cached rows: [{num, team, country, category, flag, abbr, marks:[…]}]
sheet_error = ""           # last fetch error (shown in the panel)
sheet_last_ok = 0          # timestamp of last successful fetch

def _discipline_default_name(header_text):
    # "právě běží Požární útok" -> "Požární útok"
    key = (header_text or "").strip()
    low = key.lower()
    for pref in ("právě běží", "prave bezi", "právě běží ", "běží"):
        if low.startswith(pref):
            return key[len(pref):].strip() or key
    return key

def sheet_url_configured():
    return bool(load_config_data().get("sheet_url", "").strip())

def _cell(row, i):
    return row[i].strip() if 0 <= i < len(row) else ""

def _find_col(header, needles):
    # First column whose (lowercased) header contains any of the needles; -1 if none
    for i, h in enumerate(header):
        hl = (h or "").strip().lower()
        if hl and any(n in hl for n in needles):
            return i
    return -1

def fetch_sheet_rows():
    # GET the Apps Script Web App (returns {"values": [[header…],[row…],…]}) and parse it.
    # Columns are matched BY HEADER NAME, so extra columns (kategorie) or reordering are fine.
    cfg = load_config_data()
    url = cfg.get("sheet_url", "").strip()
    if not url:
        raise RuntimeError("Není nastavená URL (Apps Script Web App).")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError("Odpověď není JSON – zkontroluj, že URL míří na nasazený Web App.")
    values = data.get("values", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    header = values[0] if values else []
    overrides = cfg.get("sheet_disc_names", {})

    num_col = _find_col(header, ["číslo", "cislo", "start"])
    team_col = _find_col(header, ["družstvo", "druzstvo", "tým", "tym", "team"])
    country_col = _find_col(header, ["stát", "stat", "země", "zeme", "country"])
    cat_col = _find_col(header, ["kategori", "category"])
    if num_col < 0: num_col = 0
    if team_col < 0: team_col = 1
    if country_col < 0: country_col = 2

    # Disciplines = marker columns whose header contains "běž" ("právě běží …")
    disc_cols = [i for i, h in enumerate(header) if "běž" in (h or "").lower()]
    if not disc_cols:   # fallback: trailing columns that aren't the identity/category ones
        used = {num_col, team_col, country_col, cat_col}
        disc_cols = [i for i in range(3, len(header)) if i not in used and (header[i] or "").strip()]
    disciplines = [{"col": i, "key": (header[i] or "").strip(),
                    "name": overrides.get((header[i] or "").strip(), _discipline_default_name(header[i]))}
                   for i in disc_cols]

    out = []
    for r in values[1:]:
        num = _cell(r, num_col)
        team = _cell(r, team_col)
        if not (num or team):
            continue
        country = _cell(r, country_col)
        rc = resolve_country(country)
        out.append({
            "num": num, "team": team, "country": country,
            "category": _cell(r, cat_col) if cat_col >= 0 else "",
            "flag": rc["flag"], "abbr": rc["abbr"],
            "marks": [bool(_cell(r, d["col"])) for d in disciplines],
        })
    return out, disciplines

def refresh_sheet():
    global sheet_rows, sheet_disciplines, sheet_error, sheet_last_ok
    try:
        sheet_rows, sheet_disciplines = fetch_sheet_rows()
        sheet_error = ""
        sheet_last_ok = time.time()
        return True
    except Exception as ex:
        sheet_error = str(ex)
        return False

def sheet_poll_loop():
    # Background refresh of the sheet cache (only when configured); near-live updates
    while True:
        try:
            if sheet_url_configured():
                refresh_sheet()
        except Exception:
            pass
        time.sleep(SHEET_POLL_SEC)

def active_discipline_index():
    return sheet_discipline if 0 <= sheet_discipline < len(sheet_disciplines) else 0

def sheet_category_list():
    # Unique category values (order preserved) if the sheet has a category column
    cats = []
    for r in sheet_rows:
        c = r.get("category", "")
        if c and c not in cats:
            cats.append(c)
    return cats

def sheet_current_rows():
    # Rows to display: optional category filter, then manual pick / auto marker.
    di = active_discipline_index()
    rows = sheet_rows
    if sheet_category:
        rows = [r for r in rows if r.get("category", "") == sheet_category]
    if sheet_mode == "manual":
        return [r for r in rows if r["num"] in sheet_sel_nums]
    return [r for r in rows if di < len(r["marks"]) and r["marks"][di]]

def sheet_payload():
    # Merged into /data when the runner lišta is on air (overlay: sheetListVisible)
    cfg = load_config_data()
    disc = sheet_disciplines[active_discipline_index()]["name"] if sheet_disciplines else ""
    label = cfg.get("sheet_label", "")
    # Header: race — [category if a single one is filtered] — discipline
    header = " — ".join([x for x in (label, sheet_category, disc) if x])
    content = [{"name": r["team"], "startNumber": r["num"], "flag": r["flag"],
                "abbr": r["abbr"], "category": r.get("category", "")}
               for r in sheet_current_rows()]
    # Show the category column only when no single category is filtered (i.e. "všechny")
    show_category = (not sheet_category) and bool(sheet_category_list())
    return {
        "sheetListVisible": True,
        "sheetTitle": header,
        "sheetContent": json.dumps({"content": content}),
        "sheetShowCategory": show_category,
        "autoPaging": True,
    }

def sheet_active():
    # The running-team lišta is showing when the sheet is the source and we're on air
    return race_source == "sheet" and is_running

def sheet_status():
    cfg = load_config_data()
    di = active_discipline_index()
    # Panel list respects the category filter (show only the selected category's teams)
    base = sheet_rows if not sheet_category else [r for r in sheet_rows if r.get("category", "") == sheet_category]
    rows = [{
        "num": r["num"], "team": r["team"], "country": r["country"],
        "flag": r["flag"], "abbr": r["abbr"], "category": r.get("category", ""),
        "running": di < len(r["marks"]) and r["marks"][di],
    } for r in base]
    return {
        "on": sheet_active(),
        "source": race_source,
        "mode": sheet_mode,
        "sel_nums": sorted(sheet_sel_nums),
        "discipline": di,
        "disciplines": [{"key": d["key"], "name": d["name"]} for d in sheet_disciplines],
        "category": sheet_category,
        "categories": sheet_category_list(),
        "url_ok": bool(cfg.get("sheet_url", "").strip()),
        "url": cfg.get("sheet_url", ""),
        "label": cfg.get("sheet_label", ""),
        "error": sheet_error,
        "rows": rows,
        "count_running": sum(1 for r in rows if r["running"]),
    }

# Background sheet poller (daemon) – idle-sleeps until a sheet is configured
threading.Thread(target=sheet_poll_loop, daemon=True).start()


def fetch_xml_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return xmltodict.parse(response.text)
    except Exception as ex:
        print(f"Chyba při získávání XML dat: {ex}")
        return None

def all_names_end_with_a(race_data):
    # Detect the hasicovo.cz quirk: every team/racer name carries a trailing "a"
    names = []
    race = race_data.get("race", {})
    cats = race.get("categories", {}).get("category", [])
    if not isinstance(cats, list):
        cats = [cats]
    for c in cats:
        for group_key, item_key in (("teams", "team"), ("racers", "racer")):
            group = c.get(group_key)
            if not group:
                continue
            items = group.get(item_key, [])
            if not isinstance(items, list):
                items = [items]
            for it in items:
                name = it.get("name") if isinstance(it, dict) else None
                if name:
                    names.append(name)
    return bool(names) and all(n.endswith("a") for n in names)

def strip_trailing_a_from_result(result):
    # Trim the trailing "a" from displayed names (the quirk only affects the name field)
    for key in ("tableContentVysledky", "tableContentAktualniZavodnici"):
        raw = result.get(key)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        for row in parsed.get("content", []):
            name = row.get("name")
            if isinstance(name, str) and name.endswith("a"):
                row["name"] = name[:-1]
        result[key] = json.dumps(parsed)

def normalize_categories(race_obj):
    raw = (race_obj.get('categories') or {}).get('category', [])
    return raw if isinstance(raw, list) else [raw]

def get_custom_category_names(race_obj):
    categories = normalize_categories(race_obj)
    names = [c.get('name', '') for c in categories]
    custom_names = [c.get('customName', n) or n for c, n in zip(categories, names)]
    return custom_names

PAGE_SIZE = 10  # must match overlay.html PAGE_SIZE constant

def current_page_count():
    if not latest_data:
        return 1
    key = "tableContentAktualniZavodnici" if show_racers_list else "tableContentVysledky"
    raw = latest_data.get(key)
    if not raw:
        return 1
    try:
        rows = json.loads(raw).get("content", [])
        return max(1, -(-len(rows) // PAGE_SIZE))  # ceiling division
    except Exception:
        return 1

def control_status():
    # Current control state, served to the Stream Deck plugin (and /control responses).
    # For the sheet source the "discipline" fields carry the sheet disciplines, so the
    # existing Companion/Stream Deck discipline next/prev (and its variables) just work.
    if race_source == "sheet":
        disc_names = [d["name"] for d in sheet_disciplines]
        cur_disc = disc_names[active_discipline_index()] if disc_names else ""
        cat_list = sheet_category_list()
        cur_cat = sheet_category
    else:
        disc_names = list(events_list)
        cur_disc = sel_event
        cat_list = list(categories)
        cur_cat = sel_category
    return {
        "ok": True,
        "is_running": is_running,
        "has_race": bool(XMLurl) or race_source == "sheet",
        "view": "results" if show_results_table else "racers" if show_racers_list
                else "total" if show_total_results_table else "none",
        "category": cur_cat,
        "discipline": cur_disc,
        "page": "AUTO" if auto_paging else sel_page,
        "page_count": current_page_count(),
        "auto_paging": auto_paging,
        "categories": cat_list,
        "disciplines": disc_names,
        # Nameplate on-air state (for panel tile + Stream Deck / Companion feedback)
        "nameplate_on": nameplate_on,
        "nameplate_name": nameplate_name,
        # Running-team lišta (Google Sheet)
        "race_source": race_source,
        "sheet_on": sheet_active(),
        "sheet_mode": sheet_mode,
    }

def cycle_value(items, current, direction):
    # Step to the next/previous item in a list, wrapping around (used by Stream Deck controls)
    if not items:
        return current
    try:
        idx = items.index(current)
    except ValueError:
        idx = 0
    idx = (idx + (1 if direction == 'next' else -1)) % len(items)
    return items[idx]

def build_race_preview(race_obj):
    # Human-readable race summary shown in the UI / select-race modal (no side effects)
    race_type = race_obj.get('raceType', '')
    race_kind = race_obj.get('raceName', '')
    return {
        "name": race_obj.get('name', ''),
        "place": race_obj.get('place', ''),
        "date": race_obj.get('date', ''),
        "raceType": race_type,
        "raceKind": race_kind,
        "events": determine_event_list(race_type, race_kind),
        "categories": get_custom_category_names(race_obj),
    }

def load_categories_from_xml():
    global events_list, race_type, race
    xml_data = fetch_xml_data(XMLurl)
    if not xml_data:
        return []

    race = xml_data.get('race', {})
    race_type = race.get('raceType', '')
    event_list = determine_event_list(race_type, race.get('raceName', ''))
    events_list.clear()
    events_list.extend(event_list)

    return get_custom_category_names(race)

def stop_script():
    global is_running
    is_running = False

def start_script():
    # Start the broadcast thread if it isn't already running. The thread reads all settings
    # (XMLurl, selection, view flags) from globals each loop, so changing them needs no restart.
    global current_thread, is_running
    is_running = True
    if current_thread and current_thread.is_alive():
        return
    current_thread = threading.Thread(target=run_script, daemon=True)
    current_thread.start()

def publish_current(race_data):
    # Parse the given XML with the CURRENT selection/view and push it to the overlay.
    # Used both by the polling loop and for instant updates when settings change.
    global latest_data
    if not race_data:
        return
    result = parse_race_data(
        race_data=race_data,
        selected_category=sel_category,
        selected_event=sel_event,
        selected_page=sel_page,
        show_results_table=show_results_table,
        show_racers_list=show_racers_list,
        show_total_results_table=show_total_results_table
    )
    if result is None:
        return
    do_strip = strip_mode == "on" or (strip_mode == "auto" and all_names_end_with_a(race_data))
    if do_strip:
        strip_trailing_a_from_result(result)
    # Paging is resolved in the overlay: auto-rotate when on, else show this page.
    result["autoPaging"] = auto_paging
    try:
        result["selectedPage"] = int(sel_page)
    except (TypeError, ValueError):
        result["selectedPage"] = 1
    latest_data = result

def run_script():
    global last_race_data

    while is_running:
        # Only the hasicovo source polls XML; the sheet source is fed by sheet_poll_loop
        if race_source != "hasicovo" or not XMLurl:
            time.sleep(1)
            continue
        race_data = fetch_xml_data(XMLurl)
        if not race_data:
            time.sleep(1)
            continue

        # Cache the raw XML so settings changes can re-render instantly without re-fetching
        last_race_data = race_data
        publish_current(race_data)
        time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_running, show_results_table, show_racers_list, show_total_results_table
    global strip_mode, sel_category, sel_event, sel_page, auto_paging
    error_message = None

    if request.method == 'POST':
        # Fallback only – live settings now go through /apply_settings (AJAX, no reload).
        sel_category = request.form.get('selected_category', sel_category)
        sel_event = request.form.get('selected_event', sel_event)
        sel_page = request.form.get('selected_page', sel_page)
        show_results_table = request.form.get('show_results_table') == 'true'
        show_racers_list = request.form.get('show_racers_list') == 'true'
        show_total_results_table = request.form.get('show_total_results_list') == 'true'
        strip_mode = request.form.get('strip_mode', strip_mode)
        auto_paging = request.form.get('auto_paging', 'true') == 'true'

    # Single XML fetch builds categories, disciplines, race summary and quirk detection
    categories.clear()
    events_list.clear()
    race_preview = {}
    quirk_detected = False
    if XMLurl:
        _xml = fetch_xml_data(XMLurl)
        if _xml and _xml.get('race'):
            race_obj = _xml['race']
            events_list.extend(determine_event_list(race_obj.get('raceType', ''), race_obj.get('raceName', '')))
            categories.extend(get_custom_category_names(race_obj))
            race_preview = build_race_preview(race_obj)
            quirk_detected = all_names_end_with_a(_xml)

    app_version = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION"), encoding="utf-8") as _vf:
            app_version = _vf.read().strip()
    except Exception:
        app_version = ""

    return render_template('index.html',
                           categories=categories,
                           events=events_list,
                           pages=['1', '2', '3', '4', '5'],
                           is_running=is_running,
                           selected_category=sel_category,
                           selected_event=sel_event,
                           selected_page=sel_page,
                           show_results_table=show_results_table,
                           show_racers_list=show_racers_list,
                           show_total_results_table=show_total_results_table,
                           auto_paging=auto_paging,
                           strip_mode=strip_mode,
                           quirk_detected=quirk_detected,
                           app_version=app_version,
                           XMLurl=XMLurl,
                           race=race_preview,
                           has_race=bool(race_preview),
                           np_countries=countries_for_ui(),
                           np_items=load_config_data().get('nameplate', []),
                           np_status=nameplate_status(),
                           race_source=race_source,
                           default_sheet_url=DEFAULT_SHEET_URL,
                           sheet_status=sheet_status(),
                           error_message=error_message)


@app.route('/overlay')
def overlay():
    # Browser source page for OBS – renders the latest parsed data locally
    return render_template('overlay.html')

@app.route('/companion')
def companion_help():
    # Step-by-step guide for setting up the Bitfocus Companion module (opened from the app menu)
    return render_template('companion.html')

@app.route('/data')
def data():
    # JSON feed polled by the overlay (replaces the Singular control API).
    # The nameplate is merged on top so it can show over the current view – and
    # even with no race loaded/broadcasting (latest_data empty).
    payload = dict(latest_data)
    if nameplate_on:
        payload.update(nameplate_payload())
    if sheet_active():
        payload.update(sheet_payload())
    return jsonify(payload)

@app.route('/race_info')
def race_info():
    # Preview a race by id/URL for the select-race modal – no side effects, does not start anything
    raw = request.args.get('id', '').strip()
    parsed = normalize_xml_url(raw)
    if not parsed:
        return jsonify({"ok": False, "error": "Neplatné číslo nebo URL závodu."}), 400
    xml = fetch_xml_data(parsed)
    race_obj = xml.get('race') if xml else None
    if not race_obj:
        return jsonify({"ok": False, "error": "Závod se nepodařilo načíst – zkontroluj číslo."}), 404
    preview = build_race_preview(race_obj)
    preview.update({"ok": True, "url": parsed, "id": parsed.split('/')[-1]})
    return jsonify(preview)

@app.route('/start_race', methods=['POST'])
def start_race():
    # Explicit start: set the race, default the selection, and begin broadcasting to the overlay
    global XMLurl, sel_category, sel_event, sel_page, race_source
    global show_results_table, show_racers_list, show_total_results_table

    race_source = "hasicovo"
    raw = request.form.get('race_id', '').strip()
    parsed = normalize_xml_url(raw)
    if parsed:
        test = fetch_xml_data(parsed)
        if test and test.get('race'):
            XMLurl = parsed
            save_config(XMLurl)

    # Reload categories/disciplines for the (possibly new) race
    categories.clear()
    categories.extend(load_categories_from_xml())

    # Default the selection to the first available so the overlay has content immediately
    sel_category = categories[0] if categories else ''
    sel_event = events_list[0] if events_list else ''
    sel_page = "1"

    # Ensure at least one view is active, otherwise the overlay would stay empty
    if not (show_results_table or show_racers_list or show_total_results_table):
        show_results_table = True

    start_script()
    return redirect('/')

@app.route('/apply_settings', methods=['POST'])
def apply_settings():
    # Lightweight live update of selection/view/strip from the control panel (AJAX, no reload).
    # The broadcast thread reads these globals each loop, so no restart is needed.
    global show_results_table, show_racers_list, show_total_results_table
    global strip_mode, sel_category, sel_event, sel_page, auto_paging
    sel_category = request.form.get('selected_category', sel_category)
    sel_event = request.form.get('selected_event', sel_event)
    sel_page = request.form.get('selected_page', sel_page)
    show_results_table = request.form.get('show_results_table') == 'true'
    show_racers_list = request.form.get('show_racers_list') == 'true'
    show_total_results_table = request.form.get('show_total_results_list') == 'true'
    strip_mode = request.form.get('strip_mode', strip_mode)
    auto_paging = request.form.get('auto_paging', 'true') == 'true'
    # Re-render immediately from cached XML so the overlay reflects the change at once
    if is_running and last_race_data is not None:
        publish_current(last_race_data)
    return jsonify({"ok": True, "is_running": is_running})

@app.route('/nameplate/save', methods=['POST'])
def nameplate_save():
    # Persist the prepared nameplates (entered ahead of the stream) to config.json.
    # Each item = {name, country, role}; country resolves to flag/abbr at render time.
    raw = request.form.get('items', '[]')
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            parsed = []
    except Exception:
        parsed = []
    items = []
    for it in parsed:
        if not isinstance(it, dict):
            continue
        entry = {
            "name": str(it.get("name", "")).strip(),
            "country": str(it.get("country", "")).strip(),
            "role": str(it.get("role", "")).strip(),
        }
        if entry["name"] or entry["country"] or entry["role"]:
            items.append(entry)
    cfg = load_config_data()
    cfg['nameplate'] = items
    save_config_data(cfg)
    return jsonify({"ok": True, "items": items})

@app.route('/nameplate/show', methods=['POST'])
def nameplate_show():
    # Put a nameplate on air: name + optional country (-> flag + abbr) + optional role.
    # Independent of the race pipeline; picked up by the overlay on the next poll.
    global nameplate_on, nameplate_name, nameplate_flag, nameplate_abbr, nameplate_role
    resolved = resolve_country(request.form.get('country', ''))
    nameplate_name = (request.form.get('name', '') or '').strip()
    nameplate_role = (request.form.get('role', '') or '').strip()
    nameplate_flag = resolved['flag']
    nameplate_abbr = resolved['abbr']
    # No explicit name but a country was picked -> use the country name as the main line
    if not nameplate_name and resolved['title']:
        nameplate_name = resolved['title']
    nameplate_on = True
    return jsonify({"ok": True, **nameplate_status()})

@app.route('/nameplate/hide', methods=['POST'])
def nameplate_hide():
    global nameplate_on
    nameplate_on = False
    return jsonify({"ok": True, **nameplate_status()})

# ---- Running-team lišta from Google Sheet ----
@app.route('/sheet/data')
def sheet_data():
    # Full sheet state for the panel (rows, mode, on-air, key/url status, last error)
    return jsonify({"ok": True, **sheet_status()})

@app.route('/sheet/settings', methods=['POST'])
def sheet_settings():
    # Save the Apps Script Web App URL (+ optional overlay label), then fetch to preview
    url = (request.form.get('url', '') or '').strip()
    label = (request.form.get('label', '') or '').strip()
    cfg = load_config_data()
    cfg['sheet_url'] = url
    cfg['sheet_label'] = label
    save_config_data(cfg)
    refresh_sheet()   # fetch immediately so the panel/modal shows rows without waiting
    return jsonify({"ok": bool(url), **sheet_status()})

@app.route('/sheet/mode', methods=['POST'])
def sheet_set_mode():
    global sheet_mode
    m = request.form.get('mode', '')
    if m in ('auto', 'manual'):
        sheet_mode = m
    return jsonify({"ok": True, **sheet_status()})

@app.route('/sheet/select', methods=['POST'])
def sheet_select():
    # Manual multi-select: click toggles a start number in/out of the on-track set
    num = (request.form.get('num', '') or '').strip()
    if num:
        sheet_sel_nums.discard(num) if num in sheet_sel_nums else sheet_sel_nums.add(num)
    return jsonify({"ok": True, **sheet_status()})

@app.route('/sheet/discipline', methods=['POST'])
def sheet_set_discipline():
    # Pick which discipline (marker column) the lišta shows
    global sheet_discipline
    try:
        sheet_discipline = int(request.form.get('index', '0'))
    except (TypeError, ValueError):
        sheet_discipline = 0
    return jsonify({"ok": True, **sheet_status()})

@app.route('/sheet/category', methods=['POST'])
def sheet_set_category():
    # Optional category filter ("" = all)
    global sheet_category
    sheet_category = (request.form.get('value', '') or '').strip()
    return jsonify({"ok": True, **sheet_status()})

@app.route('/start_sheet', methods=['POST'])
def start_sheet():
    # Start the Google Sheet as the data source (a "race" whose lišta shows the running teams)
    global race_source, XMLurl, latest_data, is_running, sheet_mode, sheet_discipline, sheet_sel_nums
    url = (request.form.get('url', '') or '').strip() or DEFAULT_SHEET_URL
    label = (request.form.get('label', '') or '').strip()
    mode = request.form.get('mode', 'auto')
    cfg = load_config_data()
    cfg.update({'sheet_url': url, 'sheet_label': label})
    # Custom discipline display names {header_key: name}
    try:
        dn = json.loads(request.form.get('disc_names', '') or '{}')
        if isinstance(dn, dict):
            cfg['sheet_disc_names'] = {str(k): str(v).strip() for k, v in dn.items() if str(v).strip()}
    except Exception:
        pass
    save_config_data(cfg)
    if mode in ('auto', 'manual'):
        sheet_mode = mode
    sheet_discipline = 0
    sheet_sel_nums = set()
    refresh_sheet()
    stop_script()                 # stop any hasicovo polling thread
    race_source = "sheet"
    XMLurl = ""
    latest_data = {}
    is_running = True             # on air; lišta is fed by sheet_poll_loop
    return redirect('/')

@app.route('/control', methods=['GET', 'POST'])
def control():
    # Stream Deck friendly control via query params (works with any HTTP-request button).
    # Examples:
    #   /control?view=results|racers|total
    #   /control?category=next|prev   /control?discipline=next|prev
    #   /control?page=next|prev|<n>
    #   /control?race=532&action=start   /control?action=start|stop
    global show_results_table, show_racers_list, show_total_results_table
    global sel_category, sel_event, sel_page, auto_paging, is_running, latest_data, XMLurl
    global nameplate_on, race_source, sheet_discipline, sheet_category

    # Load a specific race (and default the selection) before anything else
    race_id = request.args.get('race')
    if race_id:
        parsed = normalize_xml_url(race_id)
        if parsed:
            test = fetch_xml_data(parsed)
            if test and test.get('race'):
                race_source = "hasicovo"
                XMLurl = parsed
                save_config(XMLurl)
                categories.clear()
                categories.extend(load_categories_from_xml())
                sel_category = categories[0] if categories else ''
                sel_event = events_list[0] if events_list else ''
                sel_page = "1"

    cat = request.args.get('category')
    if cat:
        if race_source == 'sheet':
            opts = [""] + sheet_category_list()   # "" = všechny kategorie
            if cat in ('next', 'prev'):
                sheet_category = cycle_value(opts, sheet_category, cat)
            else:
                sheet_category = cat if cat in sheet_category_list() else ""
        elif cat in ('next', 'prev'):
            sel_category = cycle_value(categories, sel_category, cat)
        else:
            sel_category = cat

    disc = request.args.get('discipline')
    if disc:
        if race_source == 'sheet' and sheet_disciplines:
            n = len(sheet_disciplines)
            if disc == 'next':
                sheet_discipline = (active_discipline_index() + 1) % n
            elif disc == 'prev':
                sheet_discipline = (active_discipline_index() - 1) % n
            else:
                for i, d in enumerate(sheet_disciplines):
                    if disc in (d["name"], d["key"]):
                        sheet_discipline = i
                        break
        elif disc in ('next', 'prev'):
            sel_event = cycle_value(events_list, sel_event, disc)
        else:
            sel_event = disc

    page = request.args.get('page')
    if page:
        try:
            cur = int(sel_page)
        except (TypeError, ValueError):
            cur = 1
        if page == 'next':
            sel_page = str(cur + 1)
        elif page == 'prev':
            sel_page = str(max(1, cur - 1))
        elif page == 'auto':
            auto_paging = True
        elif page == 'cycle':
            if auto_paging:
                # AUTO → strana 1 (manuální)
                auto_paging = False
                sel_page = "1"
            elif cur >= current_page_count():
                # poslední strana → AUTO
                auto_paging = True
            else:
                # pokračuj na další stranu
                sel_page = str(cur + 1)
        elif page.isdigit():
            auto_paging = False
            sel_page = page

    view = request.args.get('view')
    if view:
        show_results_table = view == 'results'
        show_racers_list = view == 'racers'
        show_total_results_table = view == 'total'

    # Nameplate on-air toggle (uses the content last set from the panel). Independent
    # of the race pipeline, so it works even with no race loaded.
    np = request.args.get('nameplate')
    if np == 'show':
        nameplate_on = True
    elif np == 'hide':
        nameplate_on = False
    elif np == 'toggle':
        nameplate_on = not nameplate_on

    action = request.args.get('action')
    if action == 'start':
        if race_source == 'sheet':
            is_running = True          # sheet lišta is fed by the poller, no run_script needed
        elif XMLurl:
            if not (show_results_table or show_racers_list or show_total_results_table):
                show_results_table = True
            start_script()
    elif action == 'stop':
        stop_script()
        latest_data = {}

    # Instant re-render for same-race changes (view/category/page); a new race re-fetches itself
    if not race_id and is_running and last_race_data is not None:
        publish_current(last_race_data)

    return jsonify(control_status())

@app.route('/status')
def status():
    # Side-effect-free state, polled by the Stream Deck plugin for live button feedback
    return jsonify(control_status())

@app.route('/update', methods=['POST'])
def update_app():
    # Manual "check for updates" – downloads latest code; applied on next launch
    try:
        import updater
        ok, message = updater.update_from_github()
    except Exception as ex:
        ok, message = False, str(ex)
    return jsonify({"ok": ok, "message": message})

@app.route('/pause', methods=['POST'])
def pause_script():
    global latest_data
    stop_script()
    latest_data = {}  # clear the overlay when broadcasting stops
    return redirect('/')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    global XMLurl
    if 'URLinput' in request.form:
        raw_input = request.form['URLinput']
        parsed = normalize_xml_url(raw_input)
        if parsed:
            XMLurl = parsed
            save_config(XMLurl)
            categories.clear()
            categories.extend(load_categories_from_xml())
    stop_script()
    return redirect('/')

if __name__ == '__main__':
    # No race is preloaded – the empty-state UI prompts the user to pick one (see index()).
    if XMLurl:
        categories.clear()
        categories.extend(load_categories_from_xml())
        xml_data = fetch_xml_data(XMLurl)
        if xml_data:
            race.update(xml_data.get('race', {}))
            race_type = race.get('raceType', '')
    # Configurable via env: HV_PORT (port), HV_DEBUG=1 (autoreload),
    # HV_HOST=0.0.0.0 to expose on the LAN (e.g. Stream Deck on another machine)
    port = int(os.environ.get("HV_PORT", "5000"))
    debug = os.environ.get("HV_DEBUG") == "1"
    host = os.environ.get("HV_HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=debug)
