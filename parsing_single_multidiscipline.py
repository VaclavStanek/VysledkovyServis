# modules/parsing_single_multidiscipline.py
import json
import copy

def parse_single_multidiscipline(race, selected_category, selected_event, selected_page,
                 show_results_table, show_racers_list, show_total_results_table):
    categories = race.get("categories", {}).get("category", [])
    print(categories)
    if not isinstance(categories, list):
        categories = [categories]

    def safe_float(val):
        try:
            return float(val)
        except:
            return 0

    racers = []
    running = []
    for cat in categories:
        categoryName = cat.get('customName')
        if categoryName == None:
            categoryName = cat.get('name')
        # if categoryName != selected_category:
        #     continue

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

            if selected_event != "-":
                #100 m překážky
                attempt1_hurdles = safe_float(r.get("hurdles", '').get("points1", ''))
                attempt2_hurdles = safe_float(r.get("hurdles", '').get("points2", ''))
                hurdlesOrder = int(r.get("hurdles", '').get("order", "0")) if str(r.get("hurdles").get("order")).isdigit() else 0
                hurdlesBest = min(attempt1_hurdles, attempt2_hurdles) if attempt1_hurdles and attempt2_hurdles else max(attempt1_hurdles, attempt2_hurdles)

                #100 m PHP
                attempt1_php = safe_float(r.get("php", '').get("points1", ''))
                attempt2_php = safe_float(r.get("php", '').get("points2", ''))
                phpOrder = int(r.get("php").get("order", "0")) if str(r.get("php").get("order")).isdigit() else 0
                print(f"phpOrder: {phpOrder}" )
                phpBest = min(attempt1_php, attempt2_php) if attempt1_php and attempt2_php else max(attempt1_php, attempt2_php)
            else:
                #General single discipline
                attempt1_general = safe_float(r.get("time1"))
                attempt2_general = safe_float(r.get("time2"))
                generalOrder = int(r.get("order", "0")) if str(r.get("order", "")).isdigit() else 0
                generalBest = min(attempt1_general, attempt2_general) if attempt1_general and attempt2_general else max(attempt1_general, attempt2_general)

            #Prirazeni spravnych casu k discipline
            if selected_event == '100 m překážky':
                selected_event_order = hurdlesOrder
                selectedEventBestPoints = hurdlesBest
                attempt1_selectedEventPoints = attempt1_hurdles
                attempt2_selectedEventPoints = attempt2_hurdles
            elif selected_event == '100 m s PHP':
                selected_event_order = phpOrder
                selectedEventBestPoints = phpBest
                attempt1_selectedEventPoints = attempt1_php
                attempt2_selectedEventPoints = attempt2_php
            elif selected_event == "-":
                selected_event_order = generalOrder
                selectedEventBestPoints = generalBest
                attempt1_selectedEventPoints = attempt1_general
                attempt2_selectedEventPoints = attempt2_general
            else:
                selected_event_order = 999
                selectedEventBestPoints = 999
                attempt1_selectedEventPoints = 999
                attempt2_selectedEventPoints = 999

            if "mladší" in categoryName:
                racerCategoryShort = "mladší"
            elif "střední" in categoryName:
                racerCategoryShort = "střední"
            elif "starší" in categoryName:
                racerCategoryShort = "starší"
            else:
                racerCategoryShort = ""

            racer = {
                "name": r.get("name", ""),
                "startingNumber": r.get("statingNumber", ""),
                "track": r.get("track", ""),
                "SDH": r.get("SDH", ""),
                "isRunning": r.get("isRunning", ""),
                "finalTime": selectedEventBestPoints,
                "time1": attempt1_selectedEventPoints,
                "time2": attempt2_selectedEventPoints,
                "result": hurdlesBest+phpBest,
                "category": racerCategoryShort,
                "hurdlesOrder": hurdlesOrder,
                "phpOrder": phpOrder,
                "totalSum": int(phpOrder) + int(hurdlesOrder),
                "order": int(r.get("order", "0")) if str(r.get("order", "")).isdigit() else 0,
                "selectedEventOrder": selected_event_order,
                "trackColor": "#2467F7" if r.get("track") == "modrá" else "#F52525" if r.get("track") == "červená" else "#000000" if r.get("track") == "černá" else 0
            }

            if racer["isRunning"] == "1":
                running.append(copy.deepcopy(racer))

            if categoryName == selected_category:
                racers.append(racer)


    racers_with_order = [r for r in racers if r["order"] > 0]
    racers_without_order = [r for r in racers if r["order"] == 0]
    racers_with_order.sort(key=lambda r: r["selectedEventOrder"])
    if show_total_results_table:
        racers.sort(key=lambda r: r["order"])
    else:
        racers.sort(key=lambda r: r["selectedEventOrder"])
    # racers = racers_with_order + racers_without_order

    running.sort(key=lambda r: r["track"] if int(r["track"]) > 0 else 9999)     

    # Send all rows; the overlay handles paging (auto-rotate or manual via selected_page).
    for index, r in enumerate(racers):
        r["order"] = r["order"] if r["order"] != 0 else "–"
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["finalTime"] != 0 else "–"
        r["time1"] = r["time1"] if r["time1"] != 0 else "–"
        r["time2"] = r["time2"] if r["time2"] != 0 else "–"        
        r["finalTime"] = r["finalTime"] if r["finalTime"] != 0 else "–"
        r["backgroundColor"] = "#878787" if index % 2 == 0 else "#5D5D5D"

    for idx, r in enumerate(running):
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["finalTime"] != 0 else "–"
        r["time1"] = r["time1"] if r["time1"] != 0 else "–"
        r["time2"] = r["time2"] if r["time2"] != 0 else "–"        
        r["finalTime"] = r["finalTime"] if r["finalTime"] != 0 else "–"
        r["backgroundColor"] = "#878787" if idx % 2 == 0 else "#5D5D5D"


    return {
        "raceName": race.get("name", ""),
        "racePlace": race.get("place", ""),
        "category": selected_category,
        "categoryCustom": selected_category,
        "totalResultsTitle": "CELKOVÉ VÝSLEDKY – " + selected_category,
        "selected_event": selected_event,
        "racersResultTableVisible": show_results_table,
        "racersListVisible": False,
        "singlesMultieventListVisible": show_racers_list,
        "singlesMultieventTotalTableVisible": show_total_results_table,
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
