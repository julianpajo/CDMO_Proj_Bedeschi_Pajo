from source.SMT.instance_solver import solve_instance 
from source.SMT.build_model import build_model        
from source.SMT import smt_utils as utils             
import os.path as pt
from z3 import *
import os, time
import gc


current_dir = os.getcwd()
DEFAULT_SMT_OUTPUT_DIR = os.path.join(current_dir, 'res/SMT') 


def smt_solver(n_teams, solver_name, use_sb=False, use_optimization=False):
    """
    Solves the SMT model using Z3.
    
    Params:
        n_teams: Number of teams
        solver_name: The solver name (sempre "z3" per SMT)
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    
    Returns:
        dict: Result object containing solution and statistics
    """
    
    if solver_name.lower() != "z3":
        raise ValueError(f"Solver {solver_name} not supported for SMT. Use 'z3'")

    # Solve the instance
    result = solve_instance(n_teams, solver_name, use_sb, use_optimization, None)
    
    return result


def run_model(results_dict, n, solver, sb=False, opt=False):
    """
    Runs the SMT model with the given parameters and updates the results dictionary.
    Params:
        results_dict: Dictionary to store results
        n: Number of teams
        solver: Solver to use ("z3")
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization
    Returns:
        results_dict: Updated dictionary with results for the given configuration
    """
    key = utils.make_key(solver, sb, opt)

    try:
        print(
            f"\nRunning SMT instance with" 
            f"\n  - {n} teams"
            f"\n  - solver = {solver}"
            f"\n  - symmetry breaking = {sb}"
            f"\n  - optimization = {opt}"
        )

        result = smt_solver(n, solver, sb, opt) 

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
    Runs a single instance of the SMT model with the given parameters.

    Params:
        n: Number of teams (instances)
        solver: The solver to use ("z3")
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    """

    if solver is None:
        solver = 'z3'

    output_dir = DEFAULT_SMT_OUTPUT_DIR  
    os.makedirs(output_dir, exist_ok=True)

    results_dict = {}

    results_dict = run_model(results_dict, n, solver, use_sb, use_optimization)

    utils.write_solution(output_dir, n, results_dict)


def run_all():
    """
    Runs all configurations for the SMT model.
    """
    solvers = ["z3"] 
    instances = [6, 8, 10, 12, 14, 16, 18]
    output_dir = DEFAULT_SMT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    for n in instances:
        results_dict = {}

        for solver in solvers:
            for sb in [False, True]:
                for opt in [False, True]: 
                    results_dict = run_model(results_dict, n, solver, sb, opt)

                    gc.collect()

        utils.write_solution(output_dir, n, results_dict)