from source.SAT.model import sat_model
from z3 import *
import os, time
import os.path as pt
from source.SAT import sat_utils as utils


current_dir = os.getcwd()
DEFAULT_SAT_OUTPUT_DIR = os.path.join(current_dir, 'res/SAT')
DEFAULT_SAT_MODEL_FILE = os.path.join(current_dir, 'source/SAT/model/sat_model.py')


def sat_solver(n, use_sb=False, use_optimization=False):
    """
    Solves the SAT model using Z3.
    Params:
        n: Number of teams
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques

    Returns:
        solver: The Z3 solver after solving
    """

    s = Solver()
    s.set("timeout", 300000)

    num_teams, num_weeks, num_periods = sat_model.get_params(n)

    Teams = list(range(num_teams))
    Weeks = list(range(num_weeks))
    Periods = list(range(num_periods))


    # Create SAT variables
    M = sat_model.create_variables(Teams, Weeks, Periods)
    

    # Add constraints
    sat_model.add_hard_constraints(M, num_teams, Weeks, Periods, s)
    sat_model.add_implied_constraints(M, num_teams, Weeks, Periods, s)

    if use_sb:
        sat_model.add_symmetry_breaking_constraints(M, num_teams, Weeks, Periods, s)

    
    # Solve
    status = s.check()

    if status == sat:
        return s.model(), M, Weeks, Periods
    elif status == unknown:
        raise ValueError("Solver timed out")
    else:
        raise ValueError("No SAT solution found")


def run_model_sat(n, results_dict, solver="z3", use_sb=False, use_optimization=False):
    """
    Runs the SAT model with the given parameters and updates the results dictionary.
    Params:
        results_dict: Dictionary to store results
        n: Number of teams
        solver: Solver to use ("z3" is default here for SAT)
        use_sb: Whether to use symmetry breaking
        use_optimization: Placeholder for extra optimization strategies (if applicable)
    Returns:
        results_dict: Updated dictionary with results for the given configuration
    """
    key = utils.make_key(solver, use_sb, use_optimization)

    try:
        print(f"Running {key} for n={n} (SAT)...")

        start_time = time.time()
        model, M, Weeks, Periods = sat_solver(n, use_sb, use_optimization)
        end_time = time.time()
        
        elapsed_time = end_time - start_time

        # Parse solution from z3 model
        solution = utils.parse_solution(model, M, Weeks, Periods, n)
        has_solution = solution and all(cell is not None for row in solution for cell in row)

        # Process result
        time_val, optimal, solution, obj = utils.process_result(model, solution, elapsed_time)
        if not has_solution:
            solution = []
            optimal = False

        print("Solution found: \n", utils.print_solution(solution))

        
        results_dict[key] = {
            "sol": solution,
            "time": time_val,
            "optimal": optimal,
            "obj": obj  # SAT always None
        }

    except Exception as e:
        print(f"Error in {key} for n={n}: {e}")
        results_dict[key] = {
            "sol": [],
            "time": 300,
            "optimal": False,
            "obj":None
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

    results_dict = run_model_sat(n, results_dict, solver, use_sb, use_optimization)

    utils.write_solution(output_dir, n, results_dict)



def run_all():
    """
    Runs all configurations for the SAT model.
    """

    solvers = ["z3"]
    instances = [6, 8, 10, 12, 14]
    output_dir = DEFAULT_SAT_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    for n in instances:
        results_dict = {}

        for solver in solvers:
            for sb in [False, True]:
                    results_dict = run_model_sat(n, results_dict=results_dict, solver=solver, use_sb=sb, use_optimization=False)

        utils.write_solution(output_dir, n, results_dict)