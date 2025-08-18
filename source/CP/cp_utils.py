import os
import json
import math
from minizinc import Status


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


def parse_solution(solution):
    """
    Parses the solution from a MiniZinc result object.
    Params:
        solution: A MiniZinc result object containing the solution.
    Returns:
        A list of lists representing the matchups for each period, or an empty list if no solution is found.
    """

    if solution is None:
        return []

    teams = len(solution.O)
    weeks = len(solution.O[0])
    periods = teams // 2

    # weekly[w][p] = [home, away]
    weekly = [[None for _ in range(periods)] for _ in range(weeks)]

    for w in range(weeks):
        filled_periods = set()

        for t in range(teams):
            p = solution.per[t][w] - 1
            if p in filled_periods:
                continue

            opp = solution.O[t][w]
            is_home = solution.P[t][w]

            if is_home == 1:
                weekly[w][p] = [t + 1, opp]
            else:
                weekly[w][p] = [opp, t + 1]

            filled_periods.add(p)

    result = [[weekly[w][p] for w in range(weeks)] for p in range(periods)]
    return result


def make_key(solver, sb, hf, opt):
    """
    Creates a unique key for the solver configuration.
    Params:
        solver: The name of the solver.
        sb: Boolean indicating if superblock is used.
        hf: Boolean indicating if home/away format is used.
        opt: Boolean indicating if optimization is used.
    Returns:
        A string key representing the solver configuration.
    """

    parts = [
        solver,
        "sb" if sb else "nosb",
        "hf" if hf else "nohf",
        "opt" if opt else "noopt"
    ]

    return "_".join(parts)


def process_result(result, use_optimization):
    """
    Processes the result from a MiniZinc solver.
    Params:
        result: A MiniZinc result object containing the solution and statistics.
        use_optimization: Boolean indicating if optimization is used.
    Returns:
        A tuple containing:
            - time_val: The time taken for the solution in seconds.
            - is_optimal: Boolean indicating if the solution is optimal.
            - solution: The parsed solution as a list of lists.
            - obj: The objective value if available, otherwise None.
    """

    raw_time = result.statistics.get("time", None)

    if raw_time is not None:
        actual_time = math.floor(raw_time.total_seconds())
    else:
        actual_time = 300

    solution = parse_solution(result.solution)
    has_solution = bool(solution)

    obj = None
    is_optimal = False
    time_val = 300

    if use_optimization:
        if has_solution:
            if result.status == Status.OPTIMAL_SOLUTION:
                is_optimal = True
                time_val = actual_time
            obj = result.objective if hasattr(result, "objective") else None
    else:
        if has_solution and result.status.has_solution():
            is_optimal = True
            time_val = actual_time

    return time_val, is_optimal, solution, obj


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