from z3 import *
import json
import math
import os


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
    Params:
        result: dict come restituito da solve_instance
            {
                "status": status,
                "time": elapsed_time,
                "home": home,
                "per": per,
                "weeks": weeks,
                "periods": periods,
                "extra_params": extra_params,
                "model": solver.model()
            }

    Returns:
        schedule_periods[p][w] = [home_team, away_team]  (team index 1-based)
    """

    if result["status"] != sat or "model" not in result:
        return []

    model = result["model"]
    home = result["home"]
    per = result["per"]
    Weeks = result["weeks"]
    Periods = result["periods"]
    Teams = result["extra_params"]["teams_list"]

    # schedule_periods[period][week] = [home, away]
    schedule_periods = [[None for _ in Weeks] for _ in Periods]

    for w in Weeks:
        for i in Teams:
            opp = model.evaluate(home[(i, w)])
            if not opp.is_int():
                continue
            j = opp.as_long()
            if j == -1 or j == i:
                continue

            # Evaluate the period
            period_val = model.evaluate(per[(i, w)]).as_long()

            # Add the match (home = i, away = j)
            if schedule_periods[period_val][w] is None:
                schedule_periods[period_val][w] = [i + 1, j + 1]  # +1 per 1-based

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
        is_optimal = max_diff is not None
        obj = max_diff
    else:
        is_optimal = has_solution
        obj = None

    time_val = min(math.floor(elapsed_time), 300)
    return time_val, is_optimal, solution, obj