# Final production-ready version of AutomaticResultWriting.py (optimized and functional)

import requests
import xmltodict
import os
import json
import json
import time
import threading
from flask import Flask, request, render_template, redirect, jsonify
from parser import parse_race_data, determine_event_list

# Flask app setup
app = Flask(__name__)

# Global state
is_running = False
current_thread = None
# Latest parsed result served to the local overlay (replaces Singular output)
latest_data = {}

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
XMLurl = load_config()

# Checkbox state
show_results_table = False
show_racers_list = False
show_total_results_table = False
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

def start_script(*args):
    global current_thread, is_running
    if current_thread and current_thread.is_alive():
        stop_script()
        current_thread.join()

    current_thread = threading.Thread(target=run_script, args=args)
    is_running = True
    current_thread.start()

def run_script(XMLurl, selected_category, selected_event, selected_page):
    global is_running, latest_data, show_racers_list, show_results_table, show_total_results_table, strip_mode

    while is_running:
        race_data = fetch_xml_data(XMLurl)
        if not race_data:
            time.sleep(1)
            continue

        result = parse_race_data(
            race_data=race_data,
            selected_category=selected_category,
            selected_event=selected_event,
            selected_page=selected_page,
            show_results_table=show_results_table,
            show_racers_list=show_racers_list,
            show_total_results_table=show_total_results_table
        )

        if result is None:
            time.sleep(1)
            continue

        # Decide automatically (or by manual override) whether to trim the trailing "a"
        do_strip = strip_mode == "on" or (strip_mode == "auto" and all_names_end_with_a(race_data))
        if do_strip:
            strip_trailing_a_from_result(result)

        # Publish the latest result to the local overlay (polled by /data)
        latest_data = result
        time.sleep(1)

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_running, show_results_table, show_racers_list, show_total_results_table
    global strip_mode, sel_category, sel_event, sel_page
    error_message = None

    if request.method == 'POST':
        sel_category = request.form.get('selected_category', sel_category)
        sel_event = request.form.get('selected_event', sel_event)
        sel_page = request.form.get('selected_page', sel_page)

        show_results_table = request.form.get('show_results_table') == 'true'
        show_racers_list = request.form.get('show_racers_list') == 'true'
        show_total_results_table = request.form.get('show_total_results_list') == 'true'
        strip_mode = request.form.get('strip_mode', strip_mode)

        # Apply selection changes live ONLY while already broadcasting.
        # Starting from idle is explicit and only happens via the modal (see /start_race).
        if is_running:
            start_script(XMLurl, sel_category, sel_event, sel_page)

    categories.clear()
    categories.extend(load_categories_from_xml())

    # Live race summary + trailing-"a" quirk detection, shown in the UI
    race_preview = {}
    quirk_detected = False
    try:
        _xml = fetch_xml_data(XMLurl)
        if _xml and _xml.get('race'):
            race_preview = build_race_preview(_xml['race'])
            quirk_detected = all_names_end_with_a(_xml)
    except Exception:
        pass

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
                           strip_mode=strip_mode,
                           quirk_detected=quirk_detected,
                           app_version=app_version,
                           XMLurl=XMLurl,
                           race=race_preview,
                           error_message=error_message)


@app.route('/overlay')
def overlay():
    # Browser source page for OBS – renders the latest parsed data locally
    return render_template('overlay.html')

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

    start_script(XMLurl, sel_category, sel_event, sel_page)
    return redirect('/')

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
    categories.clear()
    categories.extend(load_categories_from_xml())
    xml_data = fetch_xml_data(XMLurl)
    if xml_data:
        race.update(xml_data.get('race', {}))
        race_type = race.get('raceType', '')
    # Port/debug configurable via env (HV_DEBUG=1 for dev autoreload, HV_PORT to change port)
    port = int(os.environ.get("HV_PORT", "5000"))
    debug = os.environ.get("HV_DEBUG") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)
