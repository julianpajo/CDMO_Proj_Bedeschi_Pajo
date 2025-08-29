from source.SAT.model.sat_model import add_max_diff_constraint, calculate_imbalances
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
    Optimize home-away difference using binary search on max imbalance.
    n_teams >= 6
    """
    start_time = time.time()

    try:
        # Build base model
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
            # Add SAT constraint for maximum allowed imbalance
            add_max_diff_constraint(home, Teams, Weeks, mid, solver)
        
            if solver.check() == sat:
                current_model = solver.model()
                current_imbalances = calculate_imbalances(current_model, home, Teams, Weeks)
                current_max = max(current_imbalances.values())

                best_model, best_max_diff = current_model, current_max
                upper_bound = mid - 1  # try lower imbalance
            
            else:
                lower_bound = mid + 1  # increase allowed imbalance
        
            solver.pop()
    
        elapsed = time.time() - start_time
    
        if best_model:
            is_optimal = (best_max_diff == 1)
            return best_model, home, per, best_max_diff, elapsed, is_optimal
    
        # If no model found
        return None, None, None, total_weeks, elapsed, False
    
    except KeyboardInterrupt:
        return None, None, None, total_weeks, timeout, False



def optimize_home_away_difference_glucose(n_teams, glucose_path, use_sb=False, timeout=300):
    """
    Optimize home-away difference using binary search on max imbalance via Glucose DIMACS.
    Returns raw DIMACS output, best max_diff, and variable mapping.
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

    # 2. Create variable mapping once from base model
    variable_mapping = get_all_variables_for_dimacs_from_variables_only(home, per, Teams, Weeks, Periods, base_solver)

    while lower <= upper and (time.time() - start_time) < timeout:
        mid = (lower + upper) // 2
        print(f"Testing max_imbalance = {mid}")

        # 3. Create temporary solver with base assertions
        temp_solver = Solver()

        temp_solver.set("timeout", int((timeout - (time.time() - start_time)) * 1000))

        for assertion in base_solver.assertions():
            temp_solver.add(assertion)

        # 4. Add max_diff constraint
        add_max_diff_constraint(home, Teams, Weeks, mid, temp_solver)

        # 5. Convert to DIMACS
        temp_dimacs, var_map = solver_to_dimacs(temp_solver)

        # 6. Build mapping from DIMACS
        current_mapping = build_variable_mapping(home, per, var_map, Teams, Weeks, Periods)

        # 7. Write temporary CNF file
        cnf_file = None
        try:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".cnf", delete=False) as tmpfile:
                cnf_file = tmpfile.name
                tmpfile.write(temp_dimacs)

            # 8. Run Glucose
            result = subprocess.run([glucose_path, "-model", cnf_file],
                                    capture_output=True, text=True,
                                    timeout=max(1, timeout - (time.time() - start_time)))

            if result.returncode == 10:  # SAT
                best_max_diff = mid
                best_dimacs_output = result.stdout
                best_variable_mapping = current_mapping
                upper = mid - 1  # try smaller imbalance
            elif result.returncode == 20:  # UNSAT
                lower = mid + 1  # need larger allowed imbalance
            else:
                # Unknown return code: assume UNSAT
                lower = mid + 1

        except subprocess.TimeoutExpired:
            print("Glucose timeout")
            break
        except KeyboardInterrupt:
            print("Optimization interrupted by user")
            return {
                "status": "unknown",
                "time": 300,
                "weeks": Weeks,
                "periods": Periods,
                "solver_output": "",
                "solver_error": "Interrupted by user",
                "variable_mapping": variable_mapping
            }
        finally:
            if cnf_file and os.path.exists(cnf_file):
                try:
                    os.unlink(cnf_file)
                except Exception as cleanup_error:
                    print(f"Warning: Could not remove temp file {cnf_file}: {cleanup_error}")

    elapsed_time = time.time() - start_time
    is_optimal = (best_max_diff == 1)

    return {
        "dimacs_output": best_dimacs_output,
        "best_max_diff": best_max_diff,
        "time": elapsed_time,
        "is_optimal": is_optimal,
        "Weeks": Weeks,
        "Periods": Periods,
        "Teams": Teams,
        "variable_mapping": best_variable_mapping
    }