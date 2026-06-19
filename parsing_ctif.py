# modules/parsing_ctif.py
import json

def parse_ctif(race, selected_category, selected_event, selected_page,
               show_results_table, show_racers_list, show_total_results_table):
    categories = (race.get("categories") or {}).get("category", [])
    if not isinstance(categories, list):
        categories = [categories]

    racers = []
    running = []
    for cat in categories:
        categoryName = cat.get('customName')
        if categoryName == None:
            categoryName = cat.get('name')
        # if categoryName != selected_category:
        #     continue
        team_list = (cat.get("teams") or {}).get("team", [])
        if not isinstance(team_list, list):
            team_list = [team_list]

        for index, team in enumerate(team_list):
            _a1 = team.get("attempt1") or {}
            _a2 = team.get("attempt2") or {}
            a1a = float(_a1.get("attackPoints", 0) or 0)
            a1v = float(_a1.get("validAttackPoints", 1) or 0)
            a1p = float(_a1.get("penaltyAttackPoints", 0) or 0)
            a2a = float(_a2.get("attackPoints", 0) or 0)
            a2v = float(_a2.get("validAttackPoints", 1) or 0)
            a2p = float(_a2.get("penaltyAttackPoints", 0) or 0)
            r1a = float(_a1.get("relayPoints", 0) or 0)
            r1v = float(_a1.get("validRelayPoints", 1) or 0)
            r1p = float(_a1.get("penaltyRelayPoints", 0) or 0)
            r2a = float(_a2.get("relayPoints", 0) or 0)
            r2v = float(_a2.get("validRelayPoints", 1) or 0)
            r2p = float(_a2.get("penaltyRelayPoints", 0) or 0)
            
            attempt1sum = round(a1a+a1p+r1a+r1p, 2)
            attempt2sum = round(a2a+a2p+r2a+r2p, 2)
            
            best = min(attempt1sum, attempt2sum) if attempt1sum and attempt2sum else max(attempt1sum, attempt2sum)
            
            #clean away invalid times
            if a1v == 0:
                a1a = "N"
                a1p = "N"
                attempt1sum = "N"
            if a2v == 0:
                a2a = "N"
                a2p = "N"
                attempt2sum = "N"
            if r1v == 0:
                r1a = "N"
                r1p = "N"
                attempt1sum = "N"
            if r2v == 0:
                r2a = "N"
                r2p = "N"
                attempt2sum = "N"

            if selected_event == "Útok":
                attempt1_selectedEventPoints = a1a
                attempt1_selectedEventPenaltyPoints = a1p
                attempt1_selectedEventSumPoints = (a1a + a1p) if a1v == 1 else "N"
                attempt2_selectedEventPoints = a2a
                attempt2_selectedEventPenaltyPoints = a2p
                attempt2_selectedEventSumPoints = (a2a + a2p) if a2v == 1 else "N"
            else:
                attempt1_selectedEventPoints = r1a
                attempt1_selectedEventPenaltyPoints = r1p
                attempt1_selectedEventSumPoints = (r1a + r1p) if r1v == 1 else "N"
                attempt2_selectedEventPoints = r2a
                attempt2_selectedEventPenaltyPoints = r2p
                attempt2_selectedEventSumPoints = (r2a + r2p) if r2v == 1 else "N"

            team_data = {
                "name": team.get("name", ""),
                "startingNumber": team.get("statingNumber", ""),
                "isRunning": team.get("isRunning", ""),
                "category": categoryName,
                "class": team.get("class", ""),
                "order": int(team.get("order", "0") or 0),
                "bestPoints": best,
                "attempt1_attackPoints": a1a,
                "attempt1_penaltyAttackPoints": a1p,
                "attempt2_attackPoints": a2a,
                "attempt2_penaltyAttackPoints": a2p,
                "attempt1_relayPoints": r1a,
                "attempt1_penaltyRelayPoints": r1p,
                "attempt2_relayPoints": r2a,
                "attempt2_penaltyRelayPoints": r2p,
                "attempt1_sumPoints": attempt1sum,
                "attempt2_sumPoints": attempt2sum,
                "attempt1_selectedEventPoints": attempt1_selectedEventPoints,
                "attempt1_selectedEventPenaltyPoints": attempt1_selectedEventPenaltyPoints,
                "attempt1_selectedEventSumPoints": attempt1_selectedEventSumPoints,
                "attempt2_selectedEventPoints": attempt2_selectedEventPoints,
                "attempt2_selectedEventPenaltyPoints": attempt2_selectedEventPenaltyPoints,
                "attempt2_selectedEventSumPoints": attempt2_selectedEventSumPoints,
                "backgroundColor": "#878787" if index % 2 == 0 else "#5D5D5D"
            }
            if team.get("isRunning") == "1":
                running.append(team_data)
            if categoryName != selected_category:
                continue
            racers.append(team_data)
        
    racers.sort(key=lambda r: r["order"] if r["order"] > 0 else 9999)
    for r in racers:
        r["order"] = r["order"] if r["order"] != 0 else "–"

    return {
        "raceName": race.get("name", ""),
        "racePlace": race.get("place", ""),
        "category": selected_category,
        "categoryCustom": selected_category,
        "selected_event": selected_event,
        "racersResultTableVisible": False,
        "racersListVisible": False,
        "CTIFListVisible": show_racers_list,
        "CTIFResultTableVisible": show_results_table or show_total_results_table,
        "singlesMultieventListVisible": False,
        "plamenListVisible": False,
        "plamenResultTableVisible": False,
        "TFAListVisible": False,
        "TFATableVisible": False,
        "totalResultsTableVisible": False,
        "dorostTotalResultsTableVisible": False,
        "nonPenaltyPointsDiscipline": False,
        "penaltyPointsDiscipline": True,
        "tableContentVysledky": json.dumps({"content": racers}),
        "tableContentAktualniZavodnici": json.dumps({"content": running})
    }
