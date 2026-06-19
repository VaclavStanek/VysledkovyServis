# modules/parsing_plamen.py
import json

def parse_plamen(race, selected_category, selected_event, selected_page,
                 show_results_table, show_racers_list, show_total_results_table):
    categories = (race.get("categories") or {}).get("category", [])
    penaltyPointsDiscipline = False
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
        if categoryName != selected_category:
            continue
        team_list = (cat.get("teams") or {}).get("team", [])
        if not isinstance(team_list, list):
            team_list = [team_list]

        for team in team_list:
            selected_event_order = 0
            selectedEventBestPoints = 9999
            penaltyPointsDiscipline = False

            #PU Plamen
            _fa = team.get("fireAttack") or {}
            attempt1_fireAttackPoints = safe_float(_fa.get("time1"))
            attempt2_fireAttackPoints = safe_float(_fa.get("time2"))
            fireAttack_order = safe_int(_fa.get('order'))
            fireAttackBestPoints = min(attempt1_fireAttackPoints, attempt2_fireAttackPoints) if attempt1_fireAttackPoints and attempt2_fireAttackPoints else max(attempt1_fireAttackPoints, attempt2_fireAttackPoints)

            #Stafety
            _rl = team.get("relay") or {}
            attempt1_relayPoints = safe_float(_rl.get("time1"))
            attempt2_relayPoints = safe_float(_rl.get("time2"))
            relay_order = safe_int(_rl.get('order'))
            relayBestPoints = min(attempt1_relayPoints, attempt2_relayPoints) if attempt1_relayPoints and attempt2_relayPoints else max(attempt1_relayPoints, attempt2_relayPoints)

            #Dvojice
            _pr = team.get("pairs") or {}
            attempt1_pairsPoints = safe_float(_pr.get("time1"))
            attempt1_pairsPenaltyPoints = safe_float(_pr.get('penaltyTime1'))
            attempt1_pairsSum = safe_float(_pr.get('totalTime1'))
            attempt2_pairsPoints = safe_float(_pr.get("time2"))
            attempt2_pairsPenaltyPoints = safe_float(_pr.get('penaltyTime2'))
            attempt2_pairsSum = safe_float(_pr.get('totalTime2'))
            pairs_order = safe_int(_pr.get('order'))
            pairsBestPoints = min(attempt1_pairsSum, attempt2_pairsSum) if attempt1_pairsSum and attempt2_pairsSum else max(attempt1_pairsSum, attempt2_pairsSum)

            #Stafeta CTIF
            _c4 = team.get("ctif400") or {}
            attempt1_ctif400Points = safe_float(_c4.get("time1"))
            attempt1_ctif400PenaltyPoints = safe_float(_c4.get('penaltyTime1'))
            attempt1_ctif400Sum = safe_float(_c4.get('totalTime1'))
            attempt2_ctif400Points = safe_float(_c4.get("time2"))
            attempt2_ctif400PenaltyPoints = safe_float(_c4.get('penaltyTime2'))
            attempt2_ctif400Sum = safe_float(_c4.get('totalTime2'))
            ctif400_order = safe_int(_c4.get('order'))
            ctif400BestPoints = min(attempt1_ctif400Sum, attempt2_ctif400Sum) if attempt1_ctif400Sum and attempt2_ctif400Sum else max(attempt1_ctif400Sum, attempt2_ctif400Sum)

            #PU CTIF
            _cf = team.get('ctifFireAttack') or {}
            attempt1_ctifFireAttackPoints = safe_float(_cf.get('time1'))
            attempt1_ctifFireAttackPenaltyPoints = safe_float(_cf.get('penaltyTime1'))
            attempt1_ctifFireAttackSum = safe_float(_cf.get('totalTime1'))
            attempt2_ctifFireAttackPoints = safe_float(_cf.get('time2'))
            attempt2_ctifFireAttackPenaltyPoints = safe_float(_cf.get('penaltyTime2'))
            attempt2_ctifFireAttackSum = safe_float(_cf.get('totalTime2'))
            ctifFireAttack_order = safe_int(_cf.get('order'))
            ctifFireAttackBestPoints = min(attempt1_ctifFireAttackSum, attempt2_ctifFireAttackSum) if attempt1_ctifFireAttackSum and attempt2_ctifFireAttackSum else max(attempt1_ctifFireAttackSum, attempt2_ctifFireAttackSum)

            #Total stats
            totalSum = safe_int(team.get('sum'))
            totalOrder = safe_int(team.get('order'))

            if selected_event == 'PÚ Plamen':
                selected_event_order = fireAttack_order
                selectedEventBestPoints = fireAttackBestPoints
                attempt1_selectedEventPoints = attempt1_fireAttackPoints
                attempt1_selectedEventPenaltyPoints = 0
                attempt1_selectedEventSumPoints = attempt1_selectedEventPoints
                attempt2_selectedEventPoints = attempt2_fireAttackPoints
                attempt2_selectedEventPenaltyPoints = 0
                attempt2_selectedEventSumPoints = attempt2_selectedEventPoints
            elif selected_event == 'Štafeta 4 x 60 m':
                selected_event_order = relay_order
                selectedEventBestPoints = relayBestPoints
                attempt1_selectedEventPoints = attempt1_relayPoints
                attempt1_selectedEventPenaltyPoints = 0
                attempt1_selectedEventSumPoints = attempt1_selectedEventPoints
                attempt2_selectedEventPoints = attempt2_relayPoints
                attempt2_selectedEventPenaltyPoints = 0
                attempt2_selectedEventSumPoints = attempt2_selectedEventPoints
            elif selected_event == 'Štafeta dvojic':
                selected_event_order = pairs_order
                selectedEventBestPoints = pairsBestPoints
                attempt1_selectedEventPoints = attempt1_pairsPoints
                attempt1_selectedEventPenaltyPoints = attempt1_pairsPenaltyPoints
                attempt1_selectedEventSumPoints = attempt1_pairsSum
                attempt2_selectedEventPoints = attempt2_pairsPoints
                attempt2_selectedEventPenaltyPoints = attempt2_pairsPenaltyPoints
                attempt2_selectedEventSumPoints = attempt2_pairsSum
                penaltyPointsDiscipline = True
            elif selected_event == 'Štafeta CTIF':
                selected_event_order = ctif400_order
                selectedEventBestPoints = ctif400BestPoints
                attempt1_selectedEventPoints = attempt1_ctif400Points
                attempt1_selectedEventPenaltyPoints = attempt1_ctif400PenaltyPoints
                attempt1_selectedEventSumPoints = attempt1_ctif400Sum
                attempt2_selectedEventPoints = attempt2_ctif400Points
                attempt2_selectedEventPenaltyPoints = attempt2_ctif400PenaltyPoints
                attempt2_selectedEventSumPoints = attempt2_ctif400Sum
                penaltyPointsDiscipline = True
            elif selected_event == 'PÚ CTIF':
                selected_event_order = ctifFireAttack_order
                selectedEventBestPoints = ctifFireAttackBestPoints
                attempt1_selectedEventPoints = attempt1_ctifFireAttackPoints
                attempt1_selectedEventPenaltyPoints = attempt1_ctifFireAttackPenaltyPoints
                attempt1_selectedEventSumPoints = attempt1_ctifFireAttackSum
                attempt2_selectedEventPoints = attempt2_ctifFireAttackPoints
                attempt2_selectedEventPenaltyPoints = attempt2_ctifFireAttackPenaltyPoints
                attempt2_selectedEventSumPoints = attempt2_ctifFireAttackSum
                penaltyPointsDiscipline = True
            else:
                selected_event_order = 9999

            team_data = {

                'selected_event': selected_event,
                "name": team.get("name", ""),
                "startingNumber": team.get("statingNumber", ""),
                "SDH": team.get("organization", ""),
                'county': team.get('county', ''),
                'class': team.get('class', ''),
                "isRunning": team.get("isRunning", ""),
                'basePoints': team.get('basePoints', ''),
                
                'attempt1_fireAttackPoints': attempt1_fireAttackPoints,
                'attempt2_fireAttackPoints': attempt2_fireAttackPoints,
                'attempt1_relayPoints': attempt1_relayPoints,
                'attempt2_relayPoints': attempt2_relayPoints,
                'attempt1_pairsPoints': attempt1_pairsPoints,
                'attempt1_pairsPenaltyPoints': attempt1_pairsPenaltyPoints,
                'attempt1_pairsTotalPoints': attempt1_pairsSum,
                'attempt2_pairsPoints': attempt2_pairsPoints,
                'attempt2_pairsPenaltyPoints': attempt2_pairsPenaltyPoints,
                'attempt2_pairsTotalPoints': attempt2_pairsSum,
                'attempt1_ctif400Points': attempt1_ctif400Points,
                'attempt1_ctif400PenaltyPoints': attempt1_ctif400PenaltyPoints,
                'attempt1_ctif400TotalPoints': attempt1_ctif400Sum,
                'attempt2_ctif400Points': attempt2_ctif400Points,
                'attempt2_ctif400PenaltyPoints': attempt2_ctif400PenaltyPoints,
                'attempt2_ctif400TotalPoints': attempt2_ctif400Sum,
                'attempt1_ctifFireAttackPoints': attempt1_ctifFireAttackPoints,
                'attempt1_ctifFireAttackPenaltyPoints': attempt1_ctifFireAttackPenaltyPoints,
                'attempt1_ctifFireAttackTotalPoints': attempt1_ctifFireAttackSum,
                'attempt2_ctifFireAttackPoints': attempt2_ctifFireAttackPoints,
                'attempt2_ctifFireAttackPenaltyPoints': attempt2_ctifFireAttackPenaltyPoints,
                'attempt2_ctifFireAttackTotalPoints': attempt2_ctifFireAttackSum,

                "attempt1_selectedEventPoints": round(attempt1_selectedEventPoints, 2),
                "attempt1_selectedEventPenaltyPoints": round(attempt1_selectedEventPenaltyPoints, 2),
                "attempt1_selectedEventSumPoints": round(attempt1_selectedEventSumPoints, 2),
                "attempt2_selectedEventPoints": round(attempt2_selectedEventPoints, 2),
                "attempt2_selectedEventPenaltyPoints": round(attempt2_selectedEventPenaltyPoints, 2),
                "attempt2_selectedEventSumPoints": round(attempt2_selectedEventSumPoints, 2),

                'fireAttackBestPoints': round(fireAttackBestPoints, 2),
                'relayBestPoints': round(relayBestPoints, 2),
                'pairsBestPoints': round(pairsBestPoints, 2),
                'ctif400BestPoints': round(ctif400BestPoints, 2),
                'ctifFireAttackBestPoints': round(ctifFireAttackBestPoints, 2),
                'fireAttackOrder': fireAttack_order,
                'relayOrder': relay_order,
                'pairsOrder': pairs_order,
                'ctif400Order': ctif400_order,
                'ctifFireAttackOrder': ctifFireAttack_order,
                'totalSum': totalSum,
                'totalOrder': totalOrder,

                "penaltyPointsDiscipline": penaltyPointsDiscipline,
                'nonPenaltyPointsDiscipline': not penaltyPointsDiscipline,
                "selectedEventOrder": selected_event_order,
                "selectedEventBestPoints": selectedEventBestPoints,
            }
            racers.append(team_data)
            if team.get("isRunning") == "1":
                running.append(team_data)

    #Razeni tymu podle spravnych parametru (tabulka discipliny x vysledku)
    if(show_total_results_table):
        racers.sort(key=lambda r: r["totalOrder"] if r["totalOrder"] > 0 else 9999)
    else:
        racers.sort(key=lambda r: r["selectedEventOrder"] if r["selectedEventOrder"] > 0 else 9999)

    
    for index, r in enumerate(racers):
        r["selectedEventOrder"] = r["selectedEventOrder"] if r["selectedEventOrder"] != 0 else "–"
        r["backgroundColor"] = "#878787" if index % 2 == 0 else "#5D5D5D"

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
        "plamenListVisible": show_racers_list,
        "plamenResultTableVisible": show_results_table,
        "TFAListVisible": False,
        "TFATableVisible": False,
        "dorostTableVisible": False,
        "dorostListVisible": False,
        "totalResultsTableVisible": show_total_results_table,
        "dorostTotalResultsTableVisible": False,
        "nonPenaltyPointsDiscipline": not penaltyPointsDiscipline,
        "penaltyPointsDiscipline": penaltyPointsDiscipline,
        "tableContentVysledky": json.dumps({"content": racers}),
        "tableContentAktualniZavodnici": json.dumps({"content": running}),
    }
