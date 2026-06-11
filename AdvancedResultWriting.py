# Final production-ready version of AutomaticResultWriting.py (optimized and functional)

import requests
import xmltodict
import os
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

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("last_url", DEFAULT_XMLURL)
    return DEFAULT_XMLURL

def save_config(url):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"last_url": url}, f)

def normalize_xml_url(input_value):
    if input_value.isdigit():
        return f"https://pozarnisport.hasicovo.cz/export_xml/show/{input_value}"
    if "pozarnisport.hasicovo.cz" in input_value:
        return input_value
    return None

# Settings
# No race is loaded on startup – the user must pick one via the modal (empty state).
XMLurl = ""

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
    raw = race_obj.get('categories', {}).get('category', [])
    return raw if isinstance(raw, list) else [raw]

def get_custom_category_names(race_obj):
    categories = normalize_categories(race_obj)
    names = [c.get('name', '') for c in categories]
    custom_names = [c.get('customName', n) or n for c, n in zip(categories, names)]
    return custom_names

def control_status():
    # Current control state, served to the Stream Deck plugin (and /control responses)
    return {
        "ok": True,
        "is_running": is_running,
        "has_race": bool(XMLurl),
        "view": "results" if show_results_table else "racers" if show_racers_list
                else "total" if show_total_results_table else "none",
        "category": sel_category,
        "discipline": sel_event,
        "page": sel_page,
        "categories": list(categories),
        "disciplines": list(events_list),
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
    # JSON feed polled by the overlay (replaces the Singular control API)
    return jsonify(latest_data)

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
    global XMLurl, sel_category, sel_event, sel_page
    global show_results_table, show_racers_list, show_total_results_table

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

@app.route('/control', methods=['GET', 'POST'])
def control():
    # Stream Deck friendly control via query params (works with any HTTP-request button).
    # Examples:
    #   /control?view=results|racers|total
    #   /control?category=next|prev   /control?discipline=next|prev
    #   /control?page=next|prev|<n>
    #   /control?race=532&action=start   /control?action=start|stop
    global show_results_table, show_racers_list, show_total_results_table
    global sel_category, sel_event, sel_page, is_running, latest_data, XMLurl

    # Load a specific race (and default the selection) before anything else
    race_id = request.args.get('race')
    if race_id:
        parsed = normalize_xml_url(race_id)
        if parsed:
            test = fetch_xml_data(parsed)
            if test and test.get('race'):
                XMLurl = parsed
                save_config(XMLurl)
                categories.clear()
                categories.extend(load_categories_from_xml())
                sel_category = categories[0] if categories else ''
                sel_event = events_list[0] if events_list else ''
                sel_page = "1"

    cat = request.args.get('category')
    if cat in ('next', 'prev'):
        sel_category = cycle_value(categories, sel_category, cat)
    elif cat:
        sel_category = cat

    disc = request.args.get('discipline')
    if disc in ('next', 'prev'):
        sel_event = cycle_value(events_list, sel_event, disc)
    elif disc:
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
        elif page.isdigit():
            sel_page = page

    view = request.args.get('view')
    if view:
        show_results_table = view == 'results'
        show_racers_list = view == 'racers'
        show_total_results_table = view == 'total'

    action = request.args.get('action')
    if action == 'start' and XMLurl:
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
