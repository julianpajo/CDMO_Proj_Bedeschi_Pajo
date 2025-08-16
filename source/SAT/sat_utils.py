import os
import json
from z3 import *



def parse_solution(model, M, Weeks, Periods, n):
    """
    Parses the solution from a SAT model.

    Params:
        model: The SAT model after solving.
        M: Boolean variables M[w][p][i][j], True if team i plays home vs j in week w, period p.
        Weeks: List of week indices.
        Periods: List of period indices.
        n: Number of teams.

    Returns:
        A list of lists representing the schedule for each period.
        schedule_periods[p][w] = [home_team, away_team]
    """
    schedule_weeks = []
    for w in Weeks:
        week_matches = []
        for p in Periods:
            found = None
            for i in range(n):
                for j in range(n):
                    if i != j and is_true(model.evaluate(M[w][p][i][j], model_completion=True)):
                        found = [i + 1, j + 1]  # 1-based
                        break
                if found:
                    break
            week_matches.append(found) # even if None
        schedule_weeks.append(week_matches)

    # Transpose to have [period][week] 
    schedule_periods = [[schedule_weeks[w_idx][p_idx] for w_idx in range(len(Weeks))] for p_idx in range(len(Periods))]
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



def write_solution(output_dir, n, results_dict):
    """
    Writes SAT results to a JSON file.
    (no 'obj' field by default).

    Args:
        output_dir: Directory to save JSON files (e.g., 'res/SAT')
        n: Number of teams (used for filename)
        results_dict: Dictionary with keys like "z3_sb"/"z3_nosb" and values:
            {
                "sol": list,  # Schedule solution
                "time": int,  # Time in seconds
                "optimal": bool,
                "obj": None   # Optional (not used in SAT)
            }
    """
    out_path = os.path.join(output_dir, f"{n}.json")
    os.makedirs(output_dir, exist_ok=True)  # Ensure directory exists

    with open(out_path, 'w') as f:
        f.write('{\n')
        for i, (key, val) in enumerate(results_dict.items()):
            f.write(f'  "{key}": {{\n')
            
            # Format solution array
            sol_str = json.dumps(val["sol"], separators=(',', ':'))
            f.write(f'    "sol": {sol_str},\n')
            
            # Add time and optimal fields
            f.write(f'    "time": {val["time"]},\n')
            f.write(f'    "optimal": {"true" if val["optimal"] else "false"}')
            
            # Handle optional 'obj' (not present in SAT by default)
            if "obj" in val:
                f.write(f',\n    "obj": {json.dumps(val["obj"])}\n')
            else:
                f.write('\n')
            
            f.write('  }' + (',' if i < len(results_dict) - 1 else '') + '\n')
        f.write('}\n')



def process_result(model, solution, elapsed_time):
    """
    Processes the Z3 SAT model solution.

    Params:
        model: The Z3 model returned by solver.model()
        M: The 4D SAT variables M[w][p][i][j]
        n: Number of teams
        elapsed_time: Time taken to solve

    Returns:
        time_val: Elapsed time (capped if needed)
        optimal: Always True if a solution exists
        solution: Parsed solution as a nested dict/list
        obj: None (SAT has no objective by default)
    """

    has_solution = True
    if solution is None or any(cell is None for row in solution for cell in row):
        has_solution = False
        solution = []

    obj = None
    is_optimal = False
    time_val = int(elapsed_time)

    if time_val > 300:
        time_val = 300

    
    if has_solution and model is not None:
        is_optimal = True

    return time_val, is_optimal, solution, obj