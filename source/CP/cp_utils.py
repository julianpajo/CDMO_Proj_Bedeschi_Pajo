import os
import json
import math


def print_solution(solution) -> str:
    if not solution:
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


def parse_solution(solution):
    if solution is None:
        return []

    weeks = len(solution.home)
    periods = len(solution.home[0])

    weekly = []
    for w in range(weeks):
        week_matches = []
        for p in range(periods):
            home_team = solution.home[w][p]
            away_team = solution.away[w][p]
            week_matches.append([home_team, away_team])
        weekly.append(week_matches)

    result = [[weekly[w][p] for w in range(weeks)] for p in range(periods)]
    return result


def make_key(solver, sb, hf, opt):
    parts = [solver, "sat", "sb" if sb else "nosb", "hf" if hf else "nohf", "opt" if opt else "noopt"]
    return "_".join(parts)


def process_result(result, use_optimization):
    raw_time = result.statistics.get('time', None)

    if raw_time is not None and hasattr(raw_time, "total_seconds"):
        actual_time = math.floor(raw_time.total_seconds())
    else:
        actual_time = 300

    solution = parse_solution(result.solution)
    has_solution = bool(solution)

    obj = None

    if use_optimization:
        if has_solution:
            is_optimal = True
            time_val = actual_time
            obj = result.objective if hasattr(result, 'objective') else None
        else:
            is_optimal = False
            time_val = 300
            obj = None
    else:
        if has_solution:
            is_optimal = True
            time_val = actual_time
        else:
            is_optimal = False
            time_val = 300

    return time_val, is_optimal, solution, obj


def write_solution(output_dir, n, results_dict):
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
