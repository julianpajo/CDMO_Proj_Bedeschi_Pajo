from itertools import combinations
from z3 import *
import os
import json
import math


def print_solution(time, optimal, solution, obj):
    """
    Prints the solution in a formatted way.

    Params:
        time: The time taken for the solution in seconds.
        optimal: Boolean indicating if the solution is optimal.
        solution: A list of lists representing the matchups for each period.
        obj: The objective value if available, otherwise None.
    """

    if not solution:
        print("\nNo solution found.")
        return

    num_periods = len(solution)
    num_weeks = len(solution[0])

    output = [f"\nSolution found:\n"]

    header = ["Period \\ Week"] + [str(w + 1) for w in range(num_weeks)]
    output.append("{:<15}".format(header[0]) + "".join(f"{w:<10}" for w in header[1:]))

    for p in range(num_periods):
        row = [f"{p + 1:<15}"]
        for w in range(num_weeks):
            row.append(f"{str(solution[p][w]):<10}")
        output.append("".join(row))

    output.append(f"\nTime taken: {time} seconds")
    output.append(f"Optimal: {'Yes' if optimal else 'No'}")
    output.append(f"Objective value: {obj if obj is not None else 'N/A'}")

    print("\n".join(output) + "\n")



def parse_solution(result):
    """
    Parses the solution from a SAT model (Z3 or DIMACS).

    Returns:
        schedule_periods[p][w] = [home_team, away_team]
    """
    if result["status"] != sat:
        return []

    Teams = result["extra_params"]["teams_list"]
    Weeks = result["weeks"]
    Periods = result["periods"]

    schedule_periods = [[None for _ in Weeks] for _ in Periods]

    # ----- Z3 case -----
    if "model" in result and result["model"] is not None:
        model = result["model"]
        home_vars = result["variables"]["home"]
        per_vars = result["variables"]["per"]

        for w in Weeks:
            for p in Periods:
                # Trova le due squadre in questo periodo e settimana
                teams_in_period = []
                for i in Teams:
                    # Verifica che la variabile per esista nel modello
                    if (i, w, p) in per_vars:
                        if is_true(model.evaluate(per_vars[(i, w, p)])):
                            teams_in_period.append(i)
                
                if len(teams_in_period) != 2:
                    continue  # ignora periodi incompleti

                i, j = teams_in_period
                # Verifica che le variabili home esistano
                if (i, j, w) in home_vars and is_true(model.evaluate(home_vars.get((i, j, w), False))):
                    home_team, away_team = i + 1, j + 1
                elif (j, i, w) in home_vars and is_true(model.evaluate(home_vars.get((j, i, w), False))):
                    home_team, away_team = j + 1, i + 1
                else:
                    continue  # skip if no home variable found

                schedule_periods[p][w] = [home_team, away_team]

    # ----- DIMACS case -----
    elif "dimacs_output" in result and "variable_mapping" in result:
        dimacs_output = result["dimacs_output"]
        variable_mapping = result["variable_mapping"]

        if not variable_mapping or "to_var" not in variable_mapping:
            print("[ERROR] variable_mapping missing or invalid")
            return []

        # Legge le assegnazioni dal DIMACS
        assignments = {}
        for line in dimacs_output.splitlines():
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("v"):
                line = line[1:].strip()
            for tok in line.split():
                if tok == "0":
                    continue
                try:
                    lit = int(tok)
                except ValueError:
                    continue
                assignments[abs(lit)] = (lit > 0)

        # Ricostruisce schedule usando home/per
        for p in Periods:
            for w in Weeks:
                teams_in_period = []
                for var_id, info in variable_mapping["to_var"].items():
                    if info[0] == "period" and info[3] == p and info[2] == w:
                        if assignments.get(var_id, False):
                            teams_in_period.append(info[1])
                if len(teams_in_period) != 2:
                    continue
                i, j = teams_in_period
                home_id = None
                for var_id, info in variable_mapping["to_var"].items():
                    if info[0] == "home" and info[1] == i and info[2] == j and info[3] == w:
                        home_id = var_id
                        break
                if home_id and assignments.get(home_id, False):
                    home_team, away_team = i + 1, j + 1
                else:
                    home_team, away_team = j + 1, i + 1
                schedule_periods[p][w] = [home_team, away_team]

    return schedule_periods




def make_key(solver_name, sb, opt):
    """
    Creates a unique key for the solver configuration.

    Params:
        solver_name: String name of the solver (e.g., "z3").
        sb: Boolean indicating if symmetry breaking is used.
        opt: Boolean indicating if optimization is used.

    Returns:
        A string key representing the solver configuration.
    """
    solver_str = solver_name.lower() if solver_name else "unknown"

    parts = [
        solver_str,
        "sb" if sb else "nosb",
        "opt" if opt else "noopt"
    ]

    return "_".join(parts)



def write_solution(output_dir, n, results_dict):
    """
    Writes the results to a JSON file.
    Params:
        output_dir: The directory where the results will be saved.
        n: An identifier for the results (e.g., number of teams).
        results_dict: A dictionary containing the results to be written.
    """

    out_path = os.path.join(output_dir, f"{n}.json")
    with open(out_path, 'w') as f:
        f.write('{\n')
        for i, (key, val) in enumerate(results_dict.items()):
            f.write(f'  "{key}": {{\n')

            sol_str = json.dumps(val["sol"], separators=(',', ':'))
            f.write(f'    "time": {val["time"]},\n')
            f.write(f'    "optimal": {"true" if val["optimal"] else "false"},\n')
            f.write(f'    "obj": {json.dumps(val["obj"])},\n')
            f.write(f'    "sol": {sol_str}\n')

            f.write('  }' + (',' if i < len(results_dict) - 1 else '') + '\n')
        f.write('}\n')



def process_result(result, use_optimization):
    """
    Processes the result from a SAT solver with validation
    """
    elapsed_time = result["time"]
    solution = parse_solution(result)
    has_solution = bool(solution)

    if use_optimization and has_solution:
        max_diff = result["extra_params"].get("max_diff")
        obj = max_diff
        is_optimal = (obj == 1)
        
    else:
        is_optimal = has_solution
        obj = None

    time_val = min(math.floor(elapsed_time), 300)
    return time_val, is_optimal, solution, obj