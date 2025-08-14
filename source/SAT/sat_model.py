import time, json, math, os
from z3 import *
from z3 import Solver, unsat, unknown, sat
from source.SAT.constraints import *

current_dir = os.getcwd()
DEFAULT_SAT_OUTPUT_DIR = os.path.join(current_dir, 'res/SAT')


# ---------------------------------------------------------------------
#                         Parameters setup
# ---------------------------------------------------------------------

def get_params(num_teams):
    if num_teams % 2:
        raise ValueError("Number of teams must be even")
    return num_teams, num_teams - 1, num_teams // 2
#          n teams,   W weeks,       P periods


# ---------------------------------------------------------------------
#                          Variables setup
# ---------------------------------------------------------------------
def create_variables(Teams, Weeks, Periods):
    n = len(Teams)

    # m[w][p][i][j] True if i vs j in week w, period p
    M = [[[[ Bool(f"M_{w}_{p}_{i}_{j}") if i < j else None for j in range(n)] for i in range(n)] for p in Periods] for w in Weeks]

    return M


# ---------------------------------------------------------------------
# Extract solution
# ---------------------------------------------------------------------
def extract_solution(model, M, Weeks, Periods, n):
    sol = []
    for p in Periods:
        period_row = []
        for w in Weeks:
            match_found = False
            for i in range(n):
                for j in range(i+1, n):
                    if is_true(model.evaluate(M[w][p][i][j], model_completion=True)):
                        period_row.append([i+1, j+1])
                        match_found = True
                        break
                if match_found:
                    break
            if not match_found:
                period_row.append([None, None])
        sol.append(period_row)
    return sol



# ---------------------------------------------------------------------
# Build Result
# ---------------------------------------------------------------------
def build_result(time_elapsed, res, model, M, Weeks, Periods, n):
    """ 
    Build .json file
    """
    time_int = math.floor(time_elapsed)

    if res == sat:
        sol = extract_solution(model, M, Weeks, Periods, n)
        return {
            "time": time_int,
            "optimal": True,
            "obj": None,
            "sol": sol
        }

    else:
        return {
            "time": 300,
            "optimal": False,
            "obj": None,
            "sol": None
        }
  


# ---------------------------------------------------------------------
# Print Result
# ---------------------------------------------------------------------
def print_schedule(sol):
    print("[")
    for period in sol:
        print("  [", end="")
        for match in period:
            print(f"[{match[0]}, {match[1]}] , ", end="")
        print("]")
    print("]")



def run_single_instance(num_teams, use_sb=False, single=True):
    # Get the parameters
    num_teams, num_weeks, num_periods = get_params(num_teams)
    print(f"{'-'*60}\nRunning SAT instance with {num_teams} teams, sb = {use_sb}\n{'-'*60}")

    Teams = list(range(num_teams))
    Weeks = list(range(num_weeks))
    Periods = list(range(num_periods))

    # Create the variables (only P)
    M = create_variables(Teams, Weeks, Periods)  # M[w][p][i][j]

    # Create the Z3 solver
    s = Solver()
    s.set("timeout", 300_000)  # 300 seconds in milliseconds

    # Start timer to store (computational + solving) time
    start_time = time.time()

    # ---------------------- ADD CONSTRAINTS ----------------------
    constraint_each_pair_once(M, num_teams, Weeks, Periods, s)
    constraint_one_match_per_week(M, num_teams, Weeks, Periods, s)
    constraint_max_two_per_period(M, num_teams, Weeks, Periods, s)
    constraint_one_match_per_slot(M, num_teams, Weeks, Periods, s)

    # --------------- SYMMETRY BREAKING CONSTRAINTS ---------------
    if use_sb:
        sb1(M, s)
        # sb2(M, num_teams, Weeks, Periods, s)

    # -------------------------- SOLVE ----------------------------
    print("Start solving...")
    res = s.check()

    end_time = time.time()
    elapsed = end_time - start_time

    model = s.model() if res == sat else None
    result = build_result(elapsed, res, model, M, Weeks, Periods, num_teams)

    # ------------------------ PRINT SOLUTION ---------------------
    if result["optimal"]:
        print(f"Proved to be sat in {elapsed:.2f} seconds")
        print("\nSchedule found:")
        print_schedule(result["sol"])
    elif res == unsat:
        print("\nNo valid schedule exists")
    else:
        print("Solver timed out")

    # ------------------------ SAVE SOLUTION ----------------------
    if single:
        output_dir = os.path.abspath(DEFAULT_SAT_OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        
        out_path = os.path.join(output_dir, f"{num_teams}.json")

        key = "z3_sb" if use_sb else "z3_nosb"

        with open(out_path, "w") as f:
            json.dump({key: result}, f, indent=2)

    return result


def run_all():
    output_dir = os.path.abspath(DEFAULT_SAT_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    n_list = [6, 8, 10, 12, 14, 16]

    for num_teams in n_list:
        results = {}
        for sb in [True, False]:
            key = f"z3_sb" if sb else "z3_nosb"
            results[key] = run_single_instance(num_teams, sb, single=False)

        out_path = os.path.join(output_dir, f"{num_teams}.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)