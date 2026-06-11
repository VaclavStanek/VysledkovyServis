# modules/parsing_single.py
import json
import copy

def parse_single(race, selected_category, selected_event, selected_page,
                 show_results_table, show_racers_list, show_total_results_table):
    categories = race.get("categories", {}).get("category", [])
    if not isinstance(categories, list):
        categories = [categories]

    racers = []
    running = []
    for cat in categories:
        categoryName = cat.get('customName')
        if categoryName == None:
            categoryName = cat.get('name')

        #If there are no racers
        if type(cat.get('racers', {})) != type({}):
            cat_racers = []
        else:
            cat_racers = cat.get("racers", {}).get("racer", [])

        if not isinstance(cat_racers, list):
            cat_racers = [cat_racers]
        for r in cat_racers:

            def safe_text(x): return x.get("#text", "") if isinstance(x, dict) else ""
            def safe_attr(x): return x.get("@validTime", "") if isinstance(x, dict) else ""

            racer = {
                "name": r.get("name", ""),
                "startingNumber": r.get("statingNumber", ""),
                "track": r.get("track", ""),
                "SDH": r.get("SDH", ""),
                "isRunning": r.get("isRunning", ""),
                "finalTime": r.get("finalTime", ""),
                "time1": safe_text(r.get("time1")),
                "time1_validity": safe_attr(r.get("time1")),
                "time2": safe_text(r.get("time2")),
                "time2_validity": safe_attr(r.get("time2")),
                "time3": safe_text(r.get("time3")),
                "time3_validity": safe_attr(r.get("time3")),
                "time4": safe_text(r.get("time4")),
                "time4_validity": safe_attr(r.get("time4")),
                "penaltyTime": r.get("penaltyTime", ""),
                "penaltyReason": r.get("penaltyReason", ""),
                "points": r.get("points", ""),
                "result": r.get("result", ""),
                "order": int(r.get("order", "0")) if str(r.get("order", "")).isdigit() else 0,
                "selectedEventOrder": int(r.get("order", "0")) if str(r.get("order", "")).isdigit() else 0,
                "trackColor": "#2467F7" if r.get("track") == "modrá" else "#F52525" if r.get("track") == "červená" else "#000000" if r.get("track") == "černá" else 0
            }
            if categoryName == selected_category:
                racers.append(racer)
            if racer["isRunning"] == "1":
                running.append(copy.deepcopy(racer))

    racers_with_order = [r for r in racers if r["order"] > 0]
    racers_without_order = [r for r in racers if r["order"] == 0]
    racers_with_order.sort(key=lambda r: r["order"])
    racers = racers_with_order + racers_without_order

    # Sort running racers by track number; unknown/empty tracks (e.g. TFA "-" or missing) go last
    def _track_sort_key(r):
        try:
            n = int(r.get("track"))
        except (TypeError, ValueError):
            return 9999
        return n if n > 0 else 9999
    running.sort(key=_track_sort_key)

    # Send all rows; the overlay handles paging (auto-rotate or manual via selected_page).
    for index, r in enumerate(racers):
        r["order"] = r["order"] if r["order"] != 0 else "–"
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["selectedEventOrder"] != 0 else "–"
        r["time1"] = r["time1"] if r["time1"] != 0 else "–"
        r["time2"] = r["time2"] if r["time2"] != 0 else "–"        
        r["finalTime"] = r["finalTime"] if r["finalTime"] != 0 else "–"
        r["backgroundColor"] = "#878787" if index % 2 == 0 else "#5D5D5D"

    for idx, r in enumerate(running):
        r["backgroundColor"] = "#878787" if idx % 2 == 0 else "#5D5D5D"
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["selectedEventOrder"] != 0 else "–"

    # split between TFA and single
    if(race.get("raceName") == "TFA"):
        print("TFA")
        show_tfa_table = show_results_table or show_total_results_table
        return {
            "raceName": race.get("name", ""),
            "racePlace": race.get("place", ""),
            "category": selected_category,
            "categoryCustom": selected_category,
            "selected_event": selected_event,
            "racersResultTableVisible": False,
            "racersListVisible": False,
            "singlesMultieventListVisible": False,
            "CTIFListVisible": False,
            "CTIFResultTableVisible": False,
            "plamenListVisible": False,
            "plamenResultTableVisible": False,
            "TFAListVisible": show_racers_list,
            "TFATableVisible": show_tfa_table,
            "totalResultsTableVisible": False,
            "nonPenaltyPointsDiscipline": False,
            "penaltyPointsDiscipline": False,
            "tableContentVysledky": json.dumps({"content": racers}),
            "tableContentAktualniZavodnici": json.dumps({"content": running})
        }
    else:
        return {
            "raceName": race.get("name", ""),
            "racePlace": race.get("place", ""),
            "category": selected_category,
            "categoryCustom": selected_category,
            "selected_event": selected_event,
            "racersResultTableVisible": show_results_table or show_total_results_table,
            "racersListVisible": show_racers_list,
            "singlesMultieventListVisible": False,
            "singlesMultieventTotalTableVisible": False,
            "CTIFListVisible": False,
            "CTIFResultTableVisible": False,
            "plamenListVisible": False,
            "plamenResultTableVisible": False,
            "TFAListVisible": False,
            "TFATableVisible": False,
            "dorostTableVisible": False,
            "dorostListVisible": False,
            "totalResultsTableVisible": False,
            "dorostTotalResultsTableVisible": False,
            "nonPenaltyPointsDiscipline": False,
            "penaltyPointsDiscipline": False,
            "tableContentVysledky": json.dumps({"content": racers}),
            "tableContentAktualniZavodnici": json.dumps({"content": running})
        }
