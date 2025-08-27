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
    Fast optimization using binary search with push/pop
    n_teams >= 6
    """
    start_time = time.time()

    try:
        # Build base model
        solver, variables, Weeks, Periods, _ = build_model(n_teams, use_sb, True, None)
        Teams = list(range(n_teams))

        total_weeks = n_teams - 1
    
        # Binary search bounds
        lower_bound, upper_bound = 1, total_weeks
        best_model, best_max_diff = None, upper_bound
        best_solution = None
    
    
        # Binary search
        while lower_bound <= upper_bound and (time.time() - start_time) < timeout:
            mid = (lower_bound + upper_bound) // 2
            print(f"Testing max_imbalance = {mid}")
        
            solver.push()
            add_max_diff_constraint(variables, Teams, Weeks, Periods, mid, solver)
        
            if solver.check() == sat:
                current_model = solver.model()
                current_imbalances = calculate_imbalances(current_model, variables, Teams, Weeks, Periods)
                current_max = max(current_imbalances.values())

                best_model, best_max_diff = current_model, current_max
                upper_bound = mid - 1
            
            else:
                lower_bound = mid + 1
        
            solver.pop()
    
        elapsed = time.time() - start_time
    
        if best_model:
            is_optimal = (best_max_diff == 1)

            return best_model, variables, best_max_diff, elapsed, is_optimal
    
        return None, None, n_teams - 1, elapsed, False
    
    except KeyboardInterrupt:
        return None, None, n_teams - 1, 300, False


def optimize_home_away_difference_glucose(n_teams, glucose_path, use_sb=False, timeout=300):
    """
    Binary search optimization for home-away difference using Glucose.
    Returns raw DIMACS output and variable mapping, parsing is left to solve_instance.
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

    # 1. Build base model ONCE (without max_diff constraint)
    base_solver, variables, _, _, _ = build_model(n_teams, use_sb, True, None)

    # 2. Get variable mapping from original variables (solo una volta!)
    variable_mapping = get_all_variables_for_dimacs_from_variables_only(variables, Teams, Weeks, Periods, base_solver)


    while lower <= upper and (time.time() - start_time) < timeout:
        mid = (lower + upper) // 2
        print(f"Testing max_imbalance = {mid}")

        # 3. Create temporary solver with base constraints + max_diff
        temp_solver = Solver()
        for assertion in base_solver.assertions():
            temp_solver.add(assertion)

            
        # 4. Add only the max_diff constraint
        add_max_diff_constraint(variables, Teams, Weeks, Periods, mid, temp_solver)

        # 5. Convert to DIMACS
        temp_dimacs, var_map = solver_to_dimacs(temp_solver)

        # Costruisci il mapping coerente con questo CNF
        current_mapping = build_variable_mapping(variables, var_map, Teams, Weeks, Periods)
        
        
        # 6. Create temporary file with auto-cleanup
        cnf_file = None
        try:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".cnf", delete=False) as tmpfile:
                cnf_file = tmpfile.name
                tmpfile.write(temp_dimacs)


            # 7. Execute Glucose
            result = subprocess.run([glucose_path, "-model", cnf_file],
                                   capture_output=True, text=True,
                                   timeout = timeout - (time.time() - start_time))
            

            if result.returncode == 10:  # SAT
                best_max_diff = mid
                best_dimacs_output = result.stdout
                best_variable_mapping = current_mapping
                upper = mid - 1
            elif result.returncode == 20:  # UNSAT
                lower = mid + 1
            else:
                # Continue with binary search assuming UNSAT for safety
                lower = mid + 1
        except subprocess.TimeoutExpired:
            break
        except KeyboardInterrupt:
            return {
                "status": unknown,
                "time": 300, 
                "stats": {"error": "timeout", "solver": "glucose"},
                "variables": variables,
                "weeks": Weeks,
                "periods": Periods,
                "solver_output": "",
                "solver_error": "Interrupted by user",
                "variable_mapping": {}
        }
                
        finally:
            # Cleanup temporary file
            if cnf_file and os.path.exists(cnf_file):
                try:
                    os.unlink(cnf_file)
                except Exception as cleanup_error:
                    print(f"  Warning: Could not cleanup {cnf_file}: {cleanup_error}")

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