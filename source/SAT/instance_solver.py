from source.SAT.build_model import build_model
from source.SAT.optimization import *
from source.SAT.dimacs import *
import subprocess
from z3 import *
import tempfile
import time
import uuid
import os

SOLVERS = {
    "z3": None,
    "glucose": "/usr/local/bin/glucose"
}


def solve_instance(n_teams, solver_name, use_sb=False, use_optimization=False, path=None):
    """Solves SAT instance with optimized binary search"""
    start_time = time.time()
    
    if use_optimization and solver_name == "z3":
        
        model, variables, max_diff, time_taken, is_optimal = optimize_home_away_difference(n_teams, use_sb)
        
        num_weeks, num_periods = n_teams - 1, n_teams // 2
        return {
            "status": sat if model else unsat,
            "time": time_taken,
            "model": model,
            "variables": variables,
            "weeks": list(range(num_weeks)),
            "periods": list(range(num_periods)),
            "extra_params": {
                "sb": use_sb, "opt": use_optimization, 
                "teams_list": list(range(n_teams)),
                "teams": n_teams, 
                "max_diff": max_diff,
                "is_optimal": is_optimal  
            }
        }
    elif use_optimization and solver_name == "glucose":
        if path is None:
            raise ValueError("Per l'ottimizzazione con Glucose devi fornire il path dell'eseguibile")
        
        result = optimize_home_away_difference_glucose(n_teams, path, use_sb, timeout=300)
        Teams = list(range(n_teams))

        # Ricostruisci dizionario simile agli altri branch
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
                "max_diff": result["best_max_diff"],
                "is_optimal": result["is_optimal"],
            },
            "dimacs_output": result["dimacs_output"],
            "variable_mapping": result["variable_mapping"]
        }

    else:
        # Regular solving
        solver, variables, Weeks, Periods, extra_params = build_model(n_teams, use_sb, use_optimization)
        
        if solver_name == "z3":
            return solve_with_z3(solver, variables, Weeks, Periods, extra_params, start_time)
        else:
            return solve_with_dimacs(solver, variables, solver_name, Weeks, Periods, extra_params, start_time, solvers_config=SOLVERS)


def solve_with_z3(solver, variables, Weeks, Periods, extra_params, start_time):
    """
    Solve using Z3 solver
    """
    try:
        status = solver.check()
        elapsed_time = time.time() - start_time

        is_optimal = (status == sat)
    
        result = {
            "status": status,
            "time": elapsed_time,
            "stats": solver.statistics(),
            "variables": variables,
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": {
                **extra_params,
                "is_optimal": is_optimal
            }
        }
    
        if status == sat:
            result["model"] = solver.model()
    
        return result
    
    except KeyboardInterrupt:
        print("\nZ3 solver interrupted by user")
        return {
            "status": unknown,
            "time": 300, 
            "stats": {"error": "interrupted", "solver": "z3"},
            "variables": variables,
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": {**extra_params, "is_optimal": False},
            "model": None
        }


def solve_with_dimacs(solver, variables, solver_name, Weeks, Periods, extra_params,
                      start_time, solvers_config=None, instance_name=None):
    """
    Solve using external DIMACS solver (e.g., Glucose) with proper file handling
    and unique temporary files to avoid conflicts during parallel execution.
    """

    if solvers_config is None:
        solvers_config = {}

    # Use tempfile for automatic cleanup
    cnf_file = None
    try:
        # Get solver path
        dimacs_solver_path = solvers_config.get(solver_name)
        if not dimacs_solver_path:
            raise ValueError(f"DIMACS solver path not provided for: {solver_name}")

        Teams = list(range(len(variables[0][0][0])))

        # 1. Build DIMACS and variable mapping
        dimacs_str, var_map = solver_to_dimacs(solver)

        # 2. Build structured variable mapping
        variable_mapping = build_variable_mapping(variables, var_map, Teams, Weeks, Periods)
        
        if variable_mapping is None:
            print("WARNING: Variable mapping failed, using fallback method")
            variable_mapping = get_all_variables_for_dimacs(solver, variables, Teams, Weeks, Periods)

        # 3. Create unique temporary file (auto-deleted when closed)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=False) as tmp_file:
            cnf_file = tmp_file.name
            tmp_file.write(dimacs_str)

        conversion_time = time.time() - start_time
        #print(f"CNF conversion time: {conversion_time:.2f}s")

        # 4. Execute external solver
        solver_start = time.time()
        result = subprocess.run(
            [dimacs_solver_path, "-model", cnf_file],
            capture_output=True, 
            text=True, 
            timeout=300  # 5 minute timeout
        )
        solver_time = time.time() - solver_start

        elapsed_time = time.time() - start_time
        #print(f"Solver execution time: {solver_time:.2f}s")

        # 5. Determine status
        if result.returncode == 10:
            status = sat
        elif result.returncode == 20:
            status = unsat
        else:
            status = unknown
            print(f"Unexpected return code: {result.returncode}")
            if result.stderr:
                print(f"Solver stderr: {result.stderr[:200]}...")  # First 200 chars

        # 6. Build result dictionary
        result_dict = {
            "status": status,
            "time": elapsed_time,
            "stats": {
                "return_code": result.returncode,
                "solver": solver_name,
                "conversion_time": conversion_time,
                "solver_time": solver_time,
                "stdout_lines": len(result.stdout.splitlines()),
                "stderr_lines": len(result.stderr.splitlines()),
                "variables_count": len(var_map)
            },
            "variables": variables,
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": extra_params,
            "solver_output": result.stdout,
            "solver_error": result.stderr,
            "variable_mapping": variable_mapping,
            "cnf_file": cnf_file  # For debugging
        }

        if status == sat:
            result_dict["dimacs_output"] = result.stdout

        return result_dict

    except subprocess.TimeoutExpired:
        return {
            "status": unknown,
            "time": 300,
            "stats": {"error": "timeout", "solver": solver_name},
            "variables": variables,
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": extra_params,
            "solver_output": "",
            "solver_error": "Timeout after 300 seconds",
            "variable_mapping": {}
        }
    except KeyboardInterrupt:
        print(f"\nSolver {solver_name} interrupted by user")
        return {
            "status": unknown,
            "time": 300, 
            "stats": {"error": "interrupted", "solver": solver_name},
            "variables": variables,
            "weeks": Weeks,
            "periods": Periods,
            "extra_params": extra_params,
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
                print(f"Warning: Could not cleanup {cnf_file}: {cleanup_error}")