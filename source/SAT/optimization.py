from source.SAT.model.sat_model import add_max_diff_constraint
from source.SAT.dimacs import solver_to_dimacs
from .build_model import build_model
from source.SAT.dimacs import *
import subprocess
from z3 import *
import tempfile
import time
import os


def optimize_home_away_difference(n_teams, use_sb=False, timeout=300):
    """
    Optimize home-away difference using binary search on max imbalance (Z3).
    """
    start_time = time.time()

    try:
        # Base model
        solver, home, per, Weeks, Periods, _ = build_model(n_teams, use_sb, use_optimization=True)
        Teams = list(range(n_teams))
        total_weeks = n_teams - 1

        # Binary search bounds
        lower_bound, upper_bound = 1, total_weeks
        best_model, best_max_diff = None, upper_bound

        # Binary search loop
        while lower_bound <= upper_bound and (time.time() - start_time) < timeout:
            mid = (lower_bound + upper_bound) // 2
            print(f"Testing max_imbalance = {mid}")

            solver.push()
            # Add max imbalance constraint
            add_max_diff_constraint(home, Teams, Weeks, mid, solver)

            status = solver.check()

            if status == sat:
                best_model = solver.model()
                best_max = mid
                solver.pop()
                upper_bound = mid - 1
                if best_max == 1:
                    break
            else:
                solver.pop()
                lower_bound = mid + 1


        elapsed = time.time() - start_time

        # Timeout with no solution
        if (elapsed >= timeout and best_model is None):
            return None, None, None, None, timeout

        # Solution found or timeout with partial solution
        return best_model, home, per, best_max, elapsed


    except KeyboardInterrupt:
        return best_model, home, per, best_max, timeout


def optimize_home_away_difference_glucose(n_teams, glucose_path, use_sb=False, timeout=300):
    """
    Optimize home-away difference using binary search on max imbalance (Glucose).
    """
    start_time = time.time()
    Teams = list(range(n_teams))
    total_weeks = n_teams - 1
    num_weeks, num_periods = total_weeks, n_teams // 2
    Weeks, Periods = list(range(num_weeks)), list(range(num_periods))

    lower, upper = 1, total_weeks
    best_max_diff = upper
    best_dimacs_output = None
    best_variable_mapping = None

    # 1. Build base model without max_diff constraint
    base_solver, home, per, _, _, _ = build_model(n_teams, use_sb, use_optimization=True)

    try:
        while lower <= upper and (time.time() - start_time) < timeout:
            mid = (lower + upper) // 2
            print(f"Testing max_imbalance = {mid}")

            # 2. Copy assertions into a temporary solver
            temp_solver = Solver()
            temp_solver.set("timeout", int((timeout - (time.time() - start_time)) * 1000))
            for assertion in base_solver.assertions():
                temp_solver.add(assertion)

            # 3. Add max_diff constraint
            add_max_diff_constraint(home, Teams, Weeks, mid, temp_solver)

            # 4. Convert to DIMACS
            temp_dimacs, var_map = solver_to_dimacs(temp_solver)

            # 5. Build mapping from DIMACS
            current_mapping = build_variable_mapping(home, per, var_map, Teams, Weeks, Periods)

            # 6. Write CNF to temp file
            cnf_file = None
            try:
                with tempfile.NamedTemporaryFile(mode="w+", suffix=".cnf", delete=False) as tmpfile:
                    cnf_file = tmpfile.name
                    tmpfile.write(temp_dimacs)

                # 7. Run Glucose
                result = subprocess.run(
                    [glucose_path, "-model", cnf_file],
                    capture_output=True,
                    text=True,
                    timeout=max(1, timeout - (time.time() - start_time)),
                )

                if result.returncode == 10:  # SAT
                    best_max_diff = mid
                    best_dimacs_output = result.stdout
                    best_variable_mapping = current_mapping
                    upper = mid - 1
                elif result.returncode == 20:  # UNSAT
                    lower = mid + 1
                else:  # Unknown return code
                    lower = mid + 1

            finally:
                if cnf_file and os.path.exists(cnf_file):
                    try:
                        os.unlink(cnf_file)
                    except Exception as cleanup_error:
                        print(f"Warning: Could not remove temp file {cnf_file}: {cleanup_error}")

    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        # always return the best model found
        pass

    elapsed_time = time.time() - start_time

    return {
        "dimacs_output": best_dimacs_output,
        "best_max_diff": best_max_diff,
        "time": elapsed_time,
        "Weeks": Weeks,
        "Periods": Periods,
        "Teams": Teams,
        "variable_mapping": best_variable_mapping,
    }
