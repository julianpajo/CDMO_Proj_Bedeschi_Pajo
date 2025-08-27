import os
import json
import math
from z3 import *


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
    Parses the solution from a SAT model.

    Params:
        result: a dictionary
        result = {
            "status": status,
            "time": elapsed_time,  # building + solving time
            "stats": solver.statistics(),
            "variables": variables,
            "weeks": weeks,
            "periods": periods,
            "extra_params": extra_params
            "model": solver.model() for Z3
            "solver_output": result.stdout, for dimacs
            "solver_error": result.stderr for dimacs
        }

    Returns:
        A list of lists representing the schedule for each period.
        schedule_periods[p][w] = [home_team, away_team]
    """

    if result["status"] != sat:
        return []
    
    # case Z3
    if "model" in result:
        model = result["model"]
        variables = result["variables"]
        Weeks = result["weeks"]
        Periods = result["periods"]
        Teams = result["extra_params"]["teams_list"]

        weekly = [[None for _ in Periods] for _ in Weeks]

        for w in Weeks:
            for p in Periods:
                home_team = None
                away_team = None
                for t in Teams:
                    if is_true(model.evaluate(variables[w][p][0][t])):
                        home_team = t + 1
                    if is_true(model.evaluate(variables[w][p][1][t])):
                        away_team = t + 1

                if home_team and away_team:
                    weekly[w][p] = [home_team, away_team]

        # Transpose to have [period][week] 
        schedule_periods = [[weekly[w][p] for w in Weeks] for p in Periods]
        return schedule_periods
    
        # case dimacs
    elif "dimacs_output" in result and "variable_mapping" in result:
        dimacs_output = result["dimacs_output"]
        variable_mapping = result["variable_mapping"]
        Weeks = result["weeks"]
        Periods = result["periods"]

        if not variable_mapping or "to_var" not in variable_mapping:
            print("[ERROR] variable_mapping missing or invalid")
            return []

        # 1. Parse all variable assignments from DIMACS output
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
                var_id = abs(lit)
                assignments[var_id] = lit > 0


        # 2. Build weekly solution
        weekly = [[None for _ in Periods] for _ in Weeks]
        for var_id, info in variable_mapping["to_var"].items():
            if assignments.get(var_id, False):
                w, p, s, t, _ = info
                if weekly[w][p] is None:
                    weekly[w][p] = [None, None]
                weekly[w][p][s] = t + 1

        # 3. Validate matches: no None, no same-team
        for w in Weeks:
            for p in Periods:
                if weekly[w][p] is None or None in weekly[w][p]:
                    print(f"[WARN] Incomplete match Week {w}, Period {p}: {weekly[w][p]}")

        # 4. Transpose to [period][week]
        schedule_periods = [[weekly[w][p] for w in Weeks] for p in Periods]
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