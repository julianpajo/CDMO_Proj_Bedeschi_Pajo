from source.SAT.instance_solver import solve_instance
from source.SAT import sat_utils as utils
import os.path as pt
from z3 import *
import os, time

import logging


current_dir = os.getcwd()
DEFAULT_SAT_OUTPUT_DIR = os.path.join(current_dir, 'res/SAT')

# DIMACS solvers
SOLVERS = {
    "z3": None,
    "glucose": "/usr/local/bin/glucose"
}


def sat_solver(n_teams, solver_name, use_sb=False, use_optimization=False):
    """
    Solves the SAT model using Z3.
    
    Params:
        n_teams: Number of teams
        solver_name: The solver name (always "z3" for SAT)
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    
    Returns:
        dict: Result object containing solution and statistics
    """
    path = SOLVERS[solver_name] if solver_name.lower() == "glucose" else None

    # Solve the instance
    result = solve_instance(n_teams, solver_name, use_sb, use_optimization, path)
    
    return result


def run_model(results_dict, n, solver, sb=False, opt=False):
    """
    Runs the SAT model with the given parameters and updates the results dictionary.
    Params:
        results_dict: Dictionary to store results
        n: Number of teams
        solver: Solver to use
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization
    Returns:
        results_dict: Updated dictionary with results for the given configuration
    """
    key = utils.make_key(solver, sb, opt)

    try:
        print(
            f"\nRunning SAT instance with"
            f"\n  - {n} teams"
            f"\n  - solver = {solver}"
            f"\n  - symmetry breaking = {sb}"
            f"\n  - optimization = {opt}"
        )

        result = sat_solver(n, solver, sb, opt)

        time, optimal, solution, obj = utils.process_result(result, opt)

        utils.print_solution(time, optimal, solution, obj)

        results_dict[key] = {
            "sol": solution,
            "time": time,
            "optimal": optimal,
            "obj": obj
        }

    except Exception as e:
        print(f"Error in {key} for n={n}: {e}")
        results_dict[key] = {
            "sol": [],
            "time": 300,
            "optimal": False,
            "obj": None
        }
    
    return results_dict


def run_single_instance(n, solver, use_sb=False, use_optimization=False):
    """
    Runs a single instance of the SAT model with the given parameters.

    Params:
        n: Number of teams (instances)
        solver: The solver to use ("z3")
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    """

    output_dir = DEFAULT_SAT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    results_dict = {}

    results_dict = run_model(results_dict, n, solver, use_sb, use_optimization)

    utils.write_solution(output_dir, n, results_dict)



def run_all():
    """
    Runs all configurations for the SAT model.
    """

    solvers = ["z3", "glucose"] 
    instances = [6, 8, 10, 12, 14]
    output_dir = DEFAULT_SAT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    for n in instances:
        results_dict = {}

        for solver in solvers:
            for sb in [False, True]:
                for opt in [False, True]: 
                    results_dict = run_model(results_dict, n, solver, sb, opt)

        utils.write_solution(output_dir, n, results_dict)