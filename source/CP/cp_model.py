from source.CP.instance_solver import solve_instance
from source.CP.build_model import build_model
from minizinc import Solver
from source.CP import cp_utils as utils
import os
import os.path as pt

current_dir = os.getcwd()

DEFAULT_CP_MODEL_FILE = pt.join(current_dir, 'source/CP/model/cp_model.mzn')
DEFAULT_CP_OUTPUT_DIR = pt.join(current_dir, 'res/CP')


def cp_solver(n_instances, solver, use_sb=False, use_heuristics=False, use_optimization=False):
    """
    Solves the CP model using the specified solver and parameters.
    Params:
        n_instances: Number of instances to solve
        solver: The solver to use (e.g., "gecode")
        use_sb: Whether to use symmetry breaking
        use_heuristics: Whether to use heuristics
        use_optimization: Whether to use optimization techniques
    Returns:
        result: The result of the solver
    """

    solver_instance = Solver.lookup(solver)
    path = DEFAULT_CP_MODEL_FILE

    model, extra_params = build_model(path, use_sb, use_heuristics, use_optimization)

    result = solve_instance(n_instances, solver_instance, model, extra_params)
    return result


def run_model(results_dict, n, solver, sb, hf, opt):
    """
    Runs the CP model with the given parameters and updates the results dictionary.
    
    Params:
        results_dict: Dictionary to store results
        n: Number of teams (instances)
        solver: The solver to use (e.g., "gecode")
        sb: Whether to use symmetry breaking
        hf: Whether to use heuristics
        opt: Whether to use optimization techniques
    """

    key = utils.make_key(solver, sb, hf, opt)
    try:
        print(f"Running {key} for n={n}...")
        result = cp_solver(n_instances=n, solver=solver,
                           use_sb=sb, use_heuristics=hf,
                           use_optimization=opt)

        time, optimal, solution, obj = utils.process_result(result, opt)

        print("Solution found: \n", utils.print_solution(solution))

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


def run_single_instance(n, solver, use_sb=False, use_heuristics=False, use_optimization=False):
    """
    Runs a single instance of the CP model with the given parameters.

    Params:
        n: Number of teams (instances)
        solver: The solver to use (e.g., "gecode")
        use_sb: Whether to use symmetry breaking
        use_heuristics: Whether to use heuristics
        use_optimization: Whether to use optimization techniques
    """

    output_dir = DEFAULT_CP_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    results_dict = {}

    results_dict = run_model(results_dict, n, solver, use_sb, use_heuristics, use_optimization)

    utils.write_solution(output_dir, n, results_dict)


def run_all():
    """
    Runs all configurations for the CP model.
    """

    solvers = ["gecode", "chuffed"]
    instances = [6, 8, 10, 12, 14, 16]
    output_dir = DEFAULT_CP_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    for n in instances:
        results_dict = {}

        for solver in solvers:
            for sb in [False, True]:
                for hf in [False, True]:
                    for opt in [False, True]:
                        results_dict = run_model(results_dict, n, solver, sb, hf, opt)

        utils.write_solution(output_dir, n, results_dict)
