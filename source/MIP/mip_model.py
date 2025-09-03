from amplpy import AMPL, modules
import os
import time
from source.MIP import mip_utils as utils
import traceback

modules.activate(os.getenv("AMPL_LICENSE_UUID"))

current_dir = os.getcwd()
DEFAULT_MIP_OUTPUT_DIR = os.path.join(current_dir, 'res/MIP')
DEFAULT_MIP_MODEL_FILE = os.path.join(current_dir, 'source/MIP/model/mip_model.mod')


def mip_solver(n, solver, use_sb=False, use_optimization=False):
    """
    Solves the MIP model using the specified parameters.
    Params:
        n: Number of teams (instances)
        solver: The solver to use (e.g., "gurobi", "cplex")
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques

    Returns:
        ampl: The AMPL object after solving the model
    """
    ampl = AMPL()

    ampl.setOption("solver_msg", 0)
    ampl.setOption("solver", solver)

    time_limit = 300
    if solver == "gurobi":
        ampl.setOption("gurobi_options", f"TimeLimit={time_limit}")
    elif solver == "cplex":
        ampl.setOption("cplex_options", f"timelimit={time_limit}")

    ampl.read(DEFAULT_MIP_MODEL_FILE)

    ampl.getParameter('n').set(n)

    ampl.getParameter('use_sb').set(1 if use_sb else 0)
    ampl.getParameter('use_opt').set(1 if use_optimization else 0)

    ampl.solve()

    return ampl


def run_model(results_dict, n, solver, use_sb=False, use_optimization=False):
    """
    Runs the MIP model with the given parameters and updates the results dictionary.

    Params:
        results_dict: Dictionary to store results
        n: Number of teams (instances)
        solver: The solver to use (e.g., "gurobi", "cplex")
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    Returns:
        results_dict: Updated dictionary with results for the given configuration
    """

    key = utils.make_key(solver, use_sb, use_optimization)
    try:
        print(
            f"\nRunning MIP instance with"
            f"\n  - {n} teams"
            f"\n  - solver = {solver}"
            f"\n  - symmetry breaking = {use_sb}"
            f"\n  - optimization = {use_optimization}"
        )

        start = time.time()
        ampl = mip_solver(n, solver, use_sb, use_optimization)
        elapsed_time = time.time() - start

        y_var = ampl.getVariable('y')
        A_var = ampl.getVariable('A')
        H_var = ampl.getVariable('H')

        y_dict = {}
        A_dict = {}
        H_dict = {}

        try:
            try:
                y_values = y_var.getValues()
                df_y = y_values.to_pandas()
                if not df_y.empty:
                    val_col = df_y.columns[-1]
                    idx_cols = df_y.columns[:-1]
                    for _, row in df_y.iterrows():
                        indices = tuple(int(row[c]) if str(row[c]).isdigit() else row[c] for c in idx_cols)
                        val = float(row[val_col])
                        if val > 0.5:
                            y_dict[indices] = int(round(val))
            except Exception:
                TEAMS = range(1, n + 1)
                WEEKS = range(1, n)
                for i in TEAMS:
                    for k in TEAMS:
                        if i < k:  # only non-oriented pairs
                            for w in WEEKS:
                                try:
                                    val = float(ampl.getValue(f"y[{i},{k},{w}]"))
                                    if val > 0.5:
                                        y_dict[(i, k, w)] = int(round(val))
                                except Exception:
                                    pass

            try:
                A_values = A_var.getValues()
                df_A = A_values.to_pandas()
                if not df_A.empty:
                    val_col = df_A.columns[-1]
                    idx_cols = df_A.columns[:-1]
                    for _, row in df_A.iterrows():
                        indices = tuple(int(row[c]) if str(row[c]).isdigit() else row[c] for c in idx_cols)
                        val = float(row[val_col])
                        if val > 0.5:
                            A_dict[indices] = int(round(val))
            except Exception:
                TEAMS = range(1, n + 1)
                WEEKS = range(1, n)
                PERIODS = range(1, n // 2 + 1)
                for i in TEAMS:
                    for k in TEAMS:
                        if i < k:  # only non-oriented pairs
                            for w in WEEKS:
                                for p in PERIODS:
                                    try:
                                        val = float(ampl.getValue(f"A[{i},{k},{w},{p}]"))
                                        if val > 0.5:
                                            A_dict[(i, k, w, p)] = int(round(val))
                                    except Exception:
                                        pass

            try:
                H_values = H_var.getValues()
                df_H = H_values.to_pandas()
                if not df_H.empty:
                    val_col = df_H.columns[-1]
                    idx_cols = df_H.columns[:-1]
                    for _, row in df_H.iterrows():
                        indices = tuple(int(row[c]) if str(row[c]).isdigit() else row[c] for c in idx_cols)
                        val = float(row[val_col])
                        if val > 0.5:
                            H_dict[indices] = int(round(val))
            except Exception:
                TEAMS = range(1, n + 1)
                WEEKS = range(1, n)
                for h in TEAMS:
                    for a in TEAMS:
                        if h != a:
                            for w in WEEKS:
                                try:
                                    val = float(ampl.getValue(f"H[{h},{a},{w}]"))
                                    if val > 0.5:
                                        H_dict[(h, a, w)] = int(round(val))
                                except Exception:
                                    pass

        except Exception:
            print("Error processing variables, using fallback methods...")

        W, P = n - 1, n // 2

        variables_dict = {
            'A_dict': A_dict,
            'H_dict': H_dict,
            'y_dict': y_dict
        }
        solution = utils.parse_solution(ampl, variables_dict, W, P, n)

        time_val, optimal, solution, obj = utils.process_result(
            ampl, solution, elapsed_time, use_optimization
        )

        utils.print_solution(time_val, optimal, solution, obj)

        results_dict[key] = {
            "sol": solution,
            "time": time_val,
            "optimal": optimal,
            "obj": obj
        }

    except Exception:
        traceback.print_exc()
        results_dict[key] = {
            "sol": [],
            "time": 300,
            "optimal": False,
            "obj": None
        }

    return results_dict


def run_single_instance(n, solver, use_sb=False, use_optimization=False):
    """
    Runs a single instance of the MIP model with the given parameters.

    Params:
        n: Number of teams (instances)
        solver: The solver to use (e.g., "gurobi", "cplex")
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    """

    if solver is None:
        solver = 'gurobi'

    os.makedirs(DEFAULT_MIP_OUTPUT_DIR, exist_ok=True)
    results_dict = {}
    results_dict = run_model(results_dict, n, solver, use_sb, use_optimization)

    utils.write_solution(DEFAULT_MIP_OUTPUT_DIR, n, results_dict)


def run_all():
    """
    Runs all configurations for the MIP model.
    """

    solvers = ["gurobi", "cplex"]
    instances = [6, 8, 10, 12, 14, 16]
    output_dir = DEFAULT_MIP_OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    for n in instances:
        results_dict = {}

        for solver in solvers:
            for sb in [False, True]:
                for opt in [False, True]:
                    results_dict = run_model(results_dict, n, solver, sb, opt)

        utils.write_solution(output_dir, n, results_dict)
