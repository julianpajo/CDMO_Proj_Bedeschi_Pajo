from source.SMT.build_model import build_model
from source.SMT.model import smt_model
from z3 import *
import time

def solve_instance(n_teams, solver_name, use_sb=False, use_optimization=False, max_diff_constraint=None):
    
    start_time = time.time()

    if use_optimization:

        model, variables, max_diff, elapsed, is_optimal = optimize_home_away_difference(n_teams, use_sb, 300)

        return {
            "status": sat if model else unsat,
            "time": elapsed,
            "model": model,
            "variables": variables,
            "weeks": list(range(n_teams - 1)),
            "periods": list(range(n_teams // 2)),
            "extra_params": {
                "sb": use_sb,
                "opt": True,
                "teams_list": list(range(n_teams)),
                "teams": n_teams,
                "max_diff": max_diff,
                "is_optimal": is_optimal
            }
        }
    
    else:
        # Regular solving path
        solver, y, weeks, periods, extra_params = build_model(n_teams, use_sb, False)
        
        # Solve the model
        status = solver.check()
        elapsed_time = time.time() - start_time

        # Prepare result
        result = {
            "status": status,
            "time": elapsed_time,
            "stats": solver.statistics(),
            "variables": y,
            "weeks": weeks,
            "periods": periods,
            "extra_params": {
                **extra_params,
                "opt": False,
                "max_diff": None,
                "is_optimal": (status == sat) 
            }
        }

        # Add model if SAT
        if status == sat:
            result["model"] = solver.model()
        
        return result


def optimize_home_away_difference(n_teams, use_sb=False, timeout=300):
    """
    Fast optimization for SMT using binary search with push/pop
    """
    start_time = time.time()
    
    # Build base SMT model
    solver, y, Weeks, Periods, extra_params = build_model(n_teams, use_sb, True)
    Teams = list(range(n_teams))
    
    # Create the max_imbalance expression once
    max_imbalance = smt_model.max_imbalance(y, Teams, Weeks, Periods)
    
    # Binary search bounds
    lower_bound, upper_bound = 1, n_teams - 1
    best_model, best_max_diff = None, upper_bound
    
    
    # Push the base state
    solver.push()
    
    # Binary search
    while lower_bound <= upper_bound and (time.time() - start_time) < timeout:
        mid = (lower_bound + upper_bound) // 2
        print(f"Testing max_imbalance <= {mid}")
        
        # Remove previous constraint and add new one
        solver.pop()
        solver.push()
        solver.add(max_imbalance <= mid)
        
        if solver.check() == sat:
            best_model = solver.model()
            best_max_diff = mid
            upper_bound = mid - 1
        else:
            lower_bound = mid + 1
    
    # Cleanup
    solver.pop()
    
    elapsed = time.time() - start_time
    
    if best_model:
        # Calculate actual imbalance from the model
        imbalances = []
        for t in Teams:
            home = sum(1 for w in Weeks for p in Periods 
                      if best_model.evaluate(y[w][p][0]).as_long() == t)
            away = sum(1 for w in Weeks for p in Periods 
                      if best_model.evaluate(y[w][p][1]).as_long() == t)
            imbalances.append(abs(home - away))
        
        actual_max = max(imbalances)
        is_optimal = (actual_max == 1)
        
        return best_model, y, actual_max, elapsed, is_optimal
    
    return None, None, n_teams - 1, elapsed, False