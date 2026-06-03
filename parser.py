# modules/parser.py
import json


def determine_event_list(race_type, race_kind):
    if race_type == 'single':
        if race_kind == 'Dorost - jednotlivci':
            return ['100 m překážky', '100 m s PHP']
        else:
            return ['-']
    elif race_type == 'team':
        if race_kind == 'CTIF':
            return ['Útok', 'Štafeta']
        elif race_kind == 'Plamen':
            return ['PÚ Plamen', 'Štafeta 4 x 60 m', 'Štafeta dvojic', 'Štafeta CTIF', 'PÚ CTIF']
        elif race_kind == 'Dorost':
            return ['Požární útok', 'Štafeta 4 x 100 m', 'Běh na 100 m']
    return ['Neznámý typ závodu']


def parse_race_data(race_data, selected_category, selected_event, selected_page,
                    show_results_table, show_racers_list, show_total_results_table):
    race = race_data.get("race", {})
    race_type = race.get("raceType", "")
    race_kind = race.get("raceName", "")

    if race_type == "single":
        if race_kind == 'Dorost - jednotlivci':
            return parse_single_multidiscipline(race, selected_category, selected_event, selected_page,
                            show_results_table, show_racers_list, show_total_results_table)
        else:
            return parse_single(race, selected_category, selected_event, selected_page,
                            show_results_table, show_racers_list, show_total_results_table)
    elif race_type == "team":
        if race_kind == "CTIF":
            return parse_ctif(race, selected_category, selected_event, selected_page,
                              show_results_table, show_racers_list, show_total_results_table)
        elif race_kind == "Plamen":
            return parse_plamen(race, selected_category, selected_event, selected_page,
                                show_results_table, show_racers_list, show_total_results_table)
        elif race_kind == "Dorost":
            return parse_dorost(race, selected_category, selected_event, selected_page,
                                show_results_table, show_racers_list, show_total_results_table)
    return None


from parsing_single import parse_single
from parsing_single_multidiscipline import parse_single_multidiscipline
from parsing_ctif import parse_ctif
from parsing_plamen import parse_plamen
from parsing_dorost import parse_dorost
