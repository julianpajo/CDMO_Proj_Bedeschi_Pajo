import os
import json


def parse_solution(ampl, X_name_or_dict, W, P, n):
    """
    Parses the solution from the AMPL model.

    Params:
        ampl: The amplpy. AMPL object after solving.
        X_name_or_dict: Either a string with the variable name or a dictionary with variable values.
        W: Number of weeks.
        P: Number of periods.
        n: Number of teams.

    Returns:
        A list of lists representing the schedule for each period.
    """

    if isinstance(X_name_or_dict, dict):
        X_raw = {tuple(int(x) for x in k): float(v) for k, v in X_name_or_dict.items()}
    else:
        X_name = X_name_or_dict
        var = ampl.get_variable(X_name)
        df = var.get_values().to_pandas()
        X_raw = {}
        if not df.empty:
            val_col = df.columns[-1]
            idx_cols = df.columns[:-1]
            for _, row in df.iterrows():
                indices = tuple(int(row[c]) for c in idx_cols)
                val = float(row[val_col])
                X_raw[indices] = val

    X_active = {k: v for k, v in X_raw.items() if float(v) > 0.5}

    schedule_weeks = []
    for w in range(1, W + 1):
        week_matches = []
        for p in range(1, P + 1):
            found = None
            for h in range(1, n + 1):
                if found:
                    break
                for a in range(1, n + 1):
                    if h == a:
                        continue
                    if X_active.get((h, a, w, p), 0) != 0:
                        found = [h, a]
                        break
            week_matches.append(found)
        schedule_weeks.append(week_matches)

    schedule_periods = [[schedule_weeks[w_idx][p_idx] for w_idx in range(W)] for p_idx in range(P)]

    return schedule_periods


def make_key(solver_name, sb, opt):
    """
    Creates a unique key for the solver configuration.

    Params:
        solver_name: String name of the solver (e.g., "gurobi", "cplex", "highs").
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


def print_solution(solution) -> str:
    """
    Formats the solution for printing.
    Params:
        solution: A list of lists where each sublist represents a period and contains the matchups for that period.
    Returns:
        A formatted string representing the solution.
    """

    if solution is None or any(cell is None for row in solution for cell in row):
        return "No solution"

    num_periods = len(solution)
    num_weeks = len(solution[0])

    output = []
    header = ["Period \\ Week"] + [str(w + 1) for w in range(num_weeks)]
    output.append("{:<15}".format(header[0]) + "".join(f"{w:<10}" for w in header[1:]))

    for p in range(num_periods):
        row = [f"{p + 1:<15}"]
        for w in range(num_weeks):
            row.append(f"{str(solution[p][w]):<10}")
        output.append("".join(row))

    return "\n".join(output)


def process_result(ampl, solution, elapsed_time, use_optimization):
    """
    Processes the result from an AMPL solver.

    Params:
        ampl: The amplpy. AMPL object after solving.
        solution: The parsed solution as a list of lists.
        elapsed_time: The time taken to solve (in seconds).
        use_optimization: Boolean indicating if optimization is used.

    Returns:
        A tuple containing:
            - time_val: The time taken for the solution in seconds (int).
            - is_optimal: Boolean indicating if the solution is optimal.
            - solution: The parsed solution as a list of lists.
            - obj: The objective value if available, otherwise None.
    """
    has_solution = True
    if solution is None or any(cell is None for row in solution for cell in row):
        has_solution = False

    obj = None
    is_optimal = False
    time_val = int(elapsed_time)

    if time_val > 300:
        time_val = 300

    solve_status = ampl.get_value("solve_result_num")
    solve_result = ampl.get_value("solve_result")

    if use_optimization:
        if has_solution:
            if solve_status == 0 or str(solve_result).lower() == "optimal":
                is_optimal = True

            objectives = list(ampl.get_objectives())
            if objectives:
                obj_name = objectives[0][0] if isinstance(objectives[0], tuple) else str(objectives[0])
                obj = int(ampl.get_objective(obj_name).value())
    else:
        if has_solution and str(solve_result).lower() in ("solved", "feasible"):
            is_optimal = True

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
            f.write(f'    "sol": {sol_str},\n')

            f.write(f'    "time": {val["time"]},\n')
            f.write(f'    "optimal": {"true" if val["optimal"] else "false"},\n')
            f.write(f'    "obj": {json.dumps(val["obj"])}\n')

            f.write('  }' + (',' if i < len(results_dict) - 1 else '') + '\n')
        f.write('}\n')
