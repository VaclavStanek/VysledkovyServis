# modules/parsing_dorost.py
import json
import copy

def parse_dorost(race, selected_category, selected_event, selected_page,
                 show_results_table, show_racers_list, show_total_results_table):
    categories = (race.get("categories") or {}).get("category", [])
    if not isinstance(categories, list):
        categories = [categories]

    def safe_float(val):
        try:
            return float(val)
        except:
            return 0

    def safe_int(val, default=0):
        try:
            return int(val)
        except:
            return default

    racers = []
    running = []
    for cat in categories:
        categoryName = cat.get('customName')
        if categoryName == None:
            categoryName = cat.get('name')

        team_list = (cat.get("teams") or {}).get("team", [])
        if not isinstance(team_list, list):
            team_list = [team_list]

        for team in team_list:
            selected_event_order = 0
            selectedEventBestPoints = 9999

            #Pozarni utok
            _fa = team.get("fireAttack") or {}
            attempt1_fireAttackPoints = safe_float(_fa.get("time1"))
            attempt2_fireAttackPoints = safe_float(_fa.get("time2"))
            fireAttack_order = safe_int(_fa.get('order'))
            fireAttackBestPoints = min(attempt1_fireAttackPoints, attempt2_fireAttackPoints) if attempt1_fireAttackPoints and attempt2_fireAttackPoints else max(attempt1_fireAttackPoints, attempt2_fireAttackPoints)

            #Stafeta
            _rl = team.get("relay") or {}
            attempt1_relayPoints = safe_float(_rl.get("time1"))
            attempt2_relayPoints = safe_float(_rl.get("time2"))
            relay_order = safe_int(_rl.get('order'))
            relayBestPoints = min(attempt1_relayPoints, attempt2_relayPoints) if attempt1_relayPoints and attempt2_relayPoints else max(attempt1_relayPoints, attempt2_relayPoints)

            #Beh 100 m
            _r100 = team.get("run100m") or {}
            attempt1_runner1_run100mPoints = safe_float((_r100.get("runner1") or {}).get("time1"))
            attempt2_runner1_run100mPoints = safe_float((_r100.get("runner1") or {}).get("time2"))
            attempt1_runner2_run100mPoints = safe_float((_r100.get("runner2") or {}).get("time1"))
            attempt2_runner2_run100mPoints = safe_float((_r100.get("runner2") or {}).get("time2"))
            attempt1_runner3_run100mPoints = safe_float((_r100.get("runner3") or {}).get("time1"))
            attempt2_runner3_run100mPoints = safe_float((_r100.get("runner3") or {}).get("time2"))
            attempt1_runner4_run100mPoints = safe_float((_r100.get("runner4") or {}).get("time1"))
            attempt2_runner4_run100mPoints = safe_float((_r100.get("runner4") or {}).get("time2"))
            attempt1_runner5_run100mPoints = safe_float((_r100.get("runner5") or {}).get("time1"))
            attempt2_runner5_run100mPoints = safe_float((_r100.get("runner5") or {}).get("time2"))
            attempt1_runner6_run100mPoints = safe_float((_r100.get("runner6") or {}).get("time1"))
            attempt2_runner6_run100mPoints = safe_float((_r100.get("runner6") or {}).get("time2"))
            attempt1_runner7_run100mPoints = safe_float((_r100.get("runner7") or {}).get("time1"))
            attempt2_runner7_run100mPoints = safe_float((_r100.get("runner7") or {}).get("time2"))
            attempt1_run100mSumPoints = attempt1_runner1_run100mPoints + attempt1_runner2_run100mPoints + attempt1_runner3_run100mPoints + attempt1_runner4_run100mPoints + attempt1_runner5_run100mPoints + attempt1_runner6_run100mPoints + attempt1_runner7_run100mPoints
            attempt2_run100mSumPoints = attempt2_runner1_run100mPoints + attempt2_runner2_run100mPoints + attempt2_runner3_run100mPoints + attempt2_runner4_run100mPoints + attempt2_runner5_run100mPoints + attempt2_runner6_run100mPoints + attempt2_runner7_run100mPoints
            run100m_order = safe_int(_r100.get('order'))
            run100m_best = min(attempt1_run100mSumPoints, attempt2_run100mSumPoints) if attempt1_run100mSumPoints and attempt2_run100mSumPoints else max(attempt1_run100mSumPoints, attempt2_run100mSumPoints)

            #Total stats
            totalSum = fireAttack_order + relay_order + run100m_order
            totalOrder = safe_int(team.get('order'))

            if selected_event == 'Požární útok':
                selected_event_order = fireAttack_order
                selectedEventBestPoints = fireAttackBestPoints
                attempt1_selectedEventPoints = attempt1_fireAttackPoints
                attempt1_selectedEventSumPoints = attempt1_selectedEventPoints
                attempt2_selectedEventPoints = attempt2_fireAttackPoints
                attempt2_selectedEventSumPoints = attempt2_selectedEventPoints
            elif selected_event == 'Štafeta 4 x 100 m':
                selected_event_order = relay_order
                selectedEventBestPoints = relayBestPoints
                attempt1_selectedEventPoints = attempt1_relayPoints
                attempt1_selectedEventSumPoints = attempt1_selectedEventPoints
                attempt2_selectedEventPoints = attempt2_relayPoints
                attempt2_selectedEventSumPoints = attempt2_selectedEventPoints
            elif selected_event == 'Běh na 100 m':
                selected_event_order = run100m_order
                selectedEventBestPoints = run100m_best
                attempt1_selectedEventPoints = attempt1_run100mSumPoints
                attempt1_selectedEventPenaltyPoints = 0
                attempt1_selectedEventSumPoints = 0
                attempt2_selectedEventPoints = attempt2_run100mSumPoints
                attempt2_selectedEventPenaltyPoints = 0
                attempt2_selectedEventSumPoints = 0
            else:
                selected_event_order = 9999
                selectedEventBestPoints = 9999
                attempt1_selectedEventPoints = 9999
                attempt1_selectedEventSumPoints = 9999
                attempt2_selectedEventPoints = 9999
                attempt2_selectedEventSumPoints = 9999

            team_data = {

                'selected_event': selected_event,
                "name": team.get("name", ""),
                "startingNumber": team.get("statingNumber", ""),
                "SDH": team.get("organization", team.get('name', "SUS")) if team.get("organization") != None else team.get("name", "SUS"),
                'county': team.get('county', ''),
                'class': team.get('class', ''),
                "isRunning": team.get("isRunning", ""),
                'basePoints': team.get('basePoints', ''),

                'attempt1_fireAttackPoints': attempt1_fireAttackPoints,
                'attempt2_fireAttackPoints': attempt2_fireAttackPoints,
                'attempt1_relayPoints': attempt1_relayPoints,
                'attempt2_relayPoints': attempt2_relayPoints,


                "attempt1_selectedEventPoints": round(attempt1_selectedEventPoints, 2),
                "attempt1_selectedEventSumPoints": round(attempt1_selectedEventSumPoints, 2),
                "attempt2_selectedEventPoints": round(attempt2_selectedEventPoints, 2),
                "attempt2_selectedEventSumPoints": round(attempt2_selectedEventSumPoints, 2),

                'fireAttackOrder': fireAttack_order,
                'relayOrder': relay_order,
                'run100mOrder': run100m_order,
                'totalSum': totalSum,
                'totalOrder': totalOrder,

                "selectedEventOrder": selected_event_order,
                "selectedEventBestPoints": round(selectedEventBestPoints, 2),
            }

            if team.get("isRunning") == "1":
                running.append(copy.deepcopy(team_data))

            if categoryName != selected_category:
                continue

            racers.append(team_data)


    #Razeni tymu podle spravnych parametru (tabulka discipliny x vysledku)
    if(show_total_results_table):
        racers.sort(key=lambda r: r["totalOrder"] if r["totalOrder"] > 0 else 9999)
    else:
        racers.sort(key=lambda r: r["selectedEventOrder"] if r["selectedEventOrder"] > 0 else 9999)


    for index, r in enumerate(racers):
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["selectedEventOrder"] != 0 else "–"
        r["attempt1_selectedEventPoints"] = r["attempt1_selectedEventPoints"] if r["attempt1_selectedEventPoints"] != 0 else "–"
        r["attempt2_selectedEventPoints"] = r["attempt2_selectedEventPoints"] if r["attempt2_selectedEventPoints"] != 0 else "–"
        r["selectedEventBestPoints"] = r["selectedEventBestPoints"] if r["selectedEventBestPoints"] != 0 else "–"
        r["backgroundColor"] = "#878787" if index % 2 == 0 else "#5D5D5D"
    for index, r in enumerate(running):
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["selectedEventOrder"] != "0" else "–"
        r["backgroundColor"] = "#878787" if index % 2 == 0 else "#5D5D5D"

    return {
        "raceName": race.get("name", ""),
        "racePlace": race.get("place", ""),
        "category": selected_category,
        "totalResultsTitle": "CELKOVÉ VÝSLEDKY – " + selected_category,
        "categoryCustom": selected_category,
        "selected_event": selected_event,
        "selected_event_and_category": selected_event + " – " + selected_category,
        "racersResultTableVisible": False,
        "racersListVisible": False,
        "singlesMultieventListVisible": False,
        "CTIFListVisible": False,
        "CTIFResultTableVisible": False,
        "plamenListVisible": False,
        "plamenResultTableVisible": False,
        "TFAListVisible": False,
        "TFATableVisible": False,
        "dorostTableVisible": show_results_table,
        "dorostListVisible": show_racers_list,
        "totalResultsTableVisible": False,
        "dorostTotalResultsTableVisible": show_total_results_table,
        "tableContentVysledky": json.dumps({"content": racers}),
        "tableContentAktualniZavodnici": json.dumps({"content": running}),
    }
