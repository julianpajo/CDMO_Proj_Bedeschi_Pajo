from source.SMT.build_model import build_model
from source.SMT.model import smt_model
from z3 import *
import time

def solve_instance(n_teams, solver_name, use_sb=False, use_optimization=False, max_diff_constraint=None):
    
    try:
        if use_optimization:

            model, home, per, max_diff, elapsed = optimize_home_away_difference(n_teams, use_sb, 300)

            return {
                "status": sat if model else unsat,
                "time": elapsed,
                "model": model,
                "home": home, 
                "per": per,
                "weeks": list(range(n_teams - 1)),
                "periods": list(range(n_teams // 2)),
                "extra_params": {
                    "sb": use_sb,
                    "opt": True,
                    "teams_list": list(range(n_teams)),
                    "teams": n_teams,
                    "max_diff": max_diff
                }
            }
    
        else:
            # Regular solving path
            start_time = time.time()

            solver, home, per, weeks, periods, extra_params = build_model(n_teams, use_sb, False)
        
            # Solve the model
            status = solver.check()
            elapsed_time = time.time() - start_time

            # Prepare result
            result = {
                "status": status,
                "model": solver.model() if status == sat else None,
                "time": elapsed_time,
                "stats": solver.statistics(),
                "home": home, 
                "per": per,
                "weeks": weeks,
                "periods": periods,
                "extra_params": {
                    **extra_params,
                    "opt": False,
                    "max_diff": None,
                    "is_optimal": (status == sat) 
                }
            }
        
            return result
        
    
    except KeyboardInterrupt:
        return {
            "status": unsat,
            "time": 300,
            "model": None,
            "message": "Execution stopped by user"
        }
        


def optimize_home_away_difference(n_teams, use_sb=False, timeout=300):
    """
    SMT optimization using binary search with precomputed Z3 expressions.
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
            # Add max imbalance constraint
            smt_model.add_max_diff_constraint(home, Teams, Weeks, mid, solver)

            status = solver.check()

            if status == sat:
                best_model = solver.model()
                best_max_diff = mid
                solver.pop()
                upper_bound = mid - 1
                if best_max_diff == 1:
                    break
            else:
                solver.pop()
                lower_bound = mid + 1

        elapsed = time.time() - start_time

        # Timeout with no solution
        if elapsed >= timeout and best_model is None:
            return None, None, None, None, timeout

        # Solution found or timeout with partial solution
        return best_model, home, per, best_max_diff, elapsed

    except KeyboardInterrupt:
        return best_model, home, per, best_max_diff, timeout