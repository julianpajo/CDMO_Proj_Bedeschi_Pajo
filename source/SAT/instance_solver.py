from source.SAT.build_model import build_model
from source.SAT.optimization import *
from source.SAT.dimacs import *
import subprocess
from z3 import *
import tempfile
import time
import os

SOLVERS = {
    "z3": None,
    "glucose": "/usr/local/bin/glucose"
}


def solve_instance(n_teams, solver_name, use_sb=False, use_optimization=False, path=None):
    """
    Solves a SAT instance with optional home-away optimization.
    Returns a structured result.
    """
    start_time = time.time()
    Teams = list(range(n_teams))

    # -----------------------------
    # Optimization + Z3 branch
    # -----------------------------
    if use_optimization and solver_name.lower() == "z3":
        model, home, per, max_diff, elapsed = optimize_home_away_difference(
            n_teams, use_sb, timeout=300
        )
        num_weeks, num_periods = n_teams - 1, n_teams // 2

        return {
            "status": sat if model else unsat,
            "time": elapsed,
            "model": model,
            "variables": {"home": home, "per": per},
            "weeks": list(range(num_weeks)),
            "periods": list(range(num_periods)),
            "extra_params": {
                "sb": use_sb,
                "opt": use_optimization,
                "teams_list": Teams,
                "teams": n_teams,
                "max_diff": max_diff
            },
        }

    # -----------------------------
    # Optimization + Glucose branch
    # -----------------------------
    elif use_optimization and solver_name.lower() == "glucose":
        if path is None:
            raise ValueError("For optimization with Glucose you must provide the executable path")

        result = optimize_home_away_difference_glucose(n_teams, path, use_sb, timeout=300)

        return {
            "status": sat if result["dimacs_output"] else unsat,
            "time": result["time"],
            "variables": None,
            "weeks": result["Weeks"],
            "periods": result["Periods"],
            "extra_params": {
                "sb": use_sb,
                "opt": use_optimization,
                "teams_list": Teams,
                "teams": n_teams,
                "max_diff": result["best_max_diff"]
            },
            "dimacs_output": result["dimacs_output"],
            "variable_mapping": result["variable_mapping"],
        }

    # -----------------------------
    # Regular SAT solving
    # -----------------------------
    else:
        solver, home, per, Weeks, Periods, extra_params = build_model(
            n_teams, use_sb, use_optimization
        )

        if solver_name.lower() == "z3":
            return solve_with_z3(solver, home, per, Weeks, Periods, extra_params, start_time)
        else:
            return solve_with_dimacs(solver, home, per, solver_name, Weeks, Periods, extra_params, start_time, solvers_config=SOLVERS,)


def solve_with_z3(solver, home, per, Weeks, Periods, extra_params, start_time):
    """
    Solve the SAT instance using Z3 solver and return a structured result.
    """
    try:
        status = solver.check()
        elapsed_time = time.time() - start_time
        is_optimal = status == sat

        return {
            "status": status,
            "time": elapsed_time,
            "stats": solver.statistics(),
            "variables": {"home": home, "per": per},
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": {**extra_params, "is_optimal": is_optimal},
            "model": solver.model() if status == sat else None,
        }

    except KeyboardInterrupt:
        return {
            "status": unsat,
            "time": 300,
            "model": None,
            "message": "Execution stopped by user"
        }


def solve_with_dimacs(solver, home, per, solver_name, Weeks, Periods, extra_params, start_time, solvers_config=None, instance_name=None):
    """
    Solve using an external DIMACS solver (Glucose) with proper file handling and unique temporary files,
    and return a structured result.
    """

    if solvers_config is None:
        solvers_config = {}

    cnf_file = None
    try:
        # Get solver path
        dimacs_solver_path = solvers_config.get(solver_name)
        if not dimacs_solver_path:
            raise ValueError(f"DIMACS solver path not provided for: {solver_name}")

        Teams = list(range(len(home)))

        # 1. Build DIMACS string and mapping
        dimacs_str, var_map = solver_to_dimacs(solver)

        # 2. Build structured variable mapping for home/per
        variable_mapping = build_variable_mapping(home, per, var_map, Teams, Weeks, Periods)
        if variable_mapping is None:
            print("Variable mapping failed")
            variable_mapping = get_all_variables_for_dimacs_from_variables_only(
                home, per, Teams, Weeks, Periods, solver
            )

        # 3. Write DIMACS to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cnf", delete=False) as tmp_file:
            cnf_file = tmp_file.name
            tmp_file.write(dimacs_str)

        # 4. Execute external solver
        result = subprocess.run(
            [dimacs_solver_path, "-model", cnf_file],
            capture_output=True,
            text=True,
            timeout=max(1, 300 - (time.time() - start_time)),
        )
        elapsed_time = time.time() - start_time

        # 5. Determine status
        if result.returncode == 10:
            status = sat
        elif result.returncode == 20:
            status = unsat
        else:
            status = unknown
            print(f"Unexpected return code: {result.returncode}")
            if result.stderr:
                print(f"Solver stderr: {result.stderr[:200]}...")

        # 6. Build result dictionary
        result_dict = {
            "status": status,
            "time": elapsed_time,
            "stats": {
                "return_code": result.returncode,
                "solver": solver_name,
                "stdout_lines": len(result.stdout.splitlines()),
                "stderr_lines": len(result.stderr.splitlines()),
                "variables_count": len(var_map),
            },
            "variables": None,
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": extra_params,
            "solver_output": result.stdout,
            "solver_error": result.stderr,
            "variable_mapping": variable_mapping,
            "cnf_file": cnf_file,
        }

        if status == sat:
            result_dict["dimacs_output"] = result.stdout

        return result_dict

    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        return {
            "status": unsat,
            "time": 300,
            "extra_params": extra_params,
            "solver_output": "",
            "solver_error": "Timeout or interrupted by user",
            "variable_mapping": {}
        }
    finally:
        if cnf_file and os.path.exists(cnf_file):
            try:
                os.unlink(cnf_file)
            except Exception as cleanup_error:
                print(f"Warning: Could not cleanup {cnf_file}: {cleanup_error}")
