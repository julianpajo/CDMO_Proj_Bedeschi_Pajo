import time, json, math, os
from z3 import *
from source.SAT.constraints import *

# ---------------------------------------------------------------------
# Parameters setup
# ---------------------------------------------------------------------
def get_params(num_teams):
    if num_teams % 2:
        raise ValueError("N must be even")
    return num_teams, num_teams - 1, num_teams // 2
           # n teams, W weeks, P periods
 
 
# ---------------------------------------------------------------------
# Variables setup
# ---------------------------------------------------------------------
def create_H_A_variables(Teams, Weeks, Periods):
  
    H = [[[Bool(f"H_{w}_{p}_{t}") for t in Teams] for p in Periods] for w in Weeks]
    A = [[[Bool(f"A_{w}_{p}_{t}") for t in Teams] for p in Periods] for w in Weeks]

    return H, A


# ---------------------------------------------------------------------
# Extract solution
# ---------------------------------------------------------------------
def extract_solution(model, H, A, Teams, Weeks, Periods):
    """
    To extract the solution and built the solution Periods x Weeks (Team_h x Team_a).
    """
    sol = []
    for p in Periods:
        row = []
        for w in Weeks:
            home_team = None
            away_team = None
            for t in Teams:
                if is_true(model.evaluate(H[w][p][t], model_completion=True)): #assume ungrounded variables to be False 
                    home_team = t + 1
                if is_true(model.evaluate(A[w][p][t], model_completion=True)):
                    away_team = t + 1
            row.append([home_team, away_team])
        sol.append(row)
    return sol


# ---------------------------------------------------------------------
# Build Result
# ---------------------------------------------------------------------
def build_result(time_elapsed, res, model, H, A, Teams, Weeks, Periods):
    """
    To build .json file
    """
    if time_elapsed > 300 or res != sat:
        return {
            "time": 300,
            "optimal": False,
            "obj": None,
            "sol": None
        }

    time_int = math.floor(time_elapsed)
    optimal = (res == sat)
    obj = None  # no objective function

    sol = extract_solution(model, H, A, Teams, Weeks, Periods) if optimal else None


    return {
        "time": time_int,
        "optimal": optimal,
        "obj": obj,
        "sol": sol
    }


# ---------------------------------------------------------------------
# Print Result
# ---------------------------------------------------------------------
def print_schedule(sol):
    print("[")
    for period in sol:
        print("  [", end="")
        print(", ".join(f"[{match[0]}, {match[1]}]" for match in period), end="")
        print("]")
    print("]")


# ---------------------------------------------------------------------
# Solving Routine
# ---------------------------------------------------------------------
def run_single_instance(num_teams, use_sb=False, single=True):
    
    # Get the parameters
    num_teams, num_weeks, num_periods = get_params(num_teams)
    print(f"{'-'*60}\nRunning SAT instance with {num_teams} teams, sb = {use_sb}\n{'-'*60}")

    Teams = list(range(num_teams))
    Weeks = list(range(num_weeks))
    Periods = list(range(num_periods))

    # Create the variables, one for the teams who play home and one for the one who play away
    H, A = create_H_A_variables(Teams, Weeks, Periods)

    # Create the Z3 solver
    s = Solver()

    # Set a timeout: 300 seconds (in millisecond)
    s.set("timeout", 300_000)
    
    # ---------------------- ADD CONSTRAINTS ----------------------
    constraint_diff_teams_in_a_match(H,A,Teams,Weeks,Periods,s)
    constraint_only_once_in_a_week(H,A,Teams,Weeks,Periods,s)
    constraint_at_most_twice_in_a_period(H,A,Teams,Weeks,Periods,s)
    constraint_only_once_each_match(H,A,Teams,Weeks,Periods,s)
    constraint_one_match_per_slot(H,A,Teams,Weeks,Periods,s)

    # --------------- SYMMETRY BREAKING CONSTRAINTS ---------------

    if use_sb:
        sb1_fixing_first_week(H,A,Teams,Weeks,Periods,s)
        sb2_fixing_team_order(H,A,Teams,Weeks,Periods,s)


    # Solve
    print("Start solving...")
    start_time = time.time()
    res = s.check()
    end_time = time.time()
    elapsed = end_time - start_time
    
    
    model = s.model() if res == sat else None    
    result = build_result(elapsed, res, model, H, A, Teams, Weeks, Periods)

    # Print solution
    if result["optimal"]:
        print(f"Solver result: sat in {elapsed:.2f} seconds")
        print("\nSchedule found:")
        print_schedule(result["sol"])
    else:
        print("\nNo valid schedule found or solver timed out.")
    
    # Save
    if single:
        output_dir = os.path.join(os.path.dirname(__file__), "../..", "res", "SAT")
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{num_teams}.json")

        with open(out_path, "w") as f:
            json.dump({ "z3_sb" if use_sb else "z3_nosb": result }, f, indent=2)
    

    return result


def run_all():
    output_dir = os.path.join(os.path.dirname(__file__), "../..", "res", "SAT")
    os.makedirs(output_dir, exist_ok=True)

    n_list = [6, 8, 10, 12, 14]

    for num_teams in n_list:
        results = {}
        for sb in [True, False]:
            key = f"z3_sb" if sb else "z3_nosb"
            results[key] = run_single_instance(num_teams, sb, single=False)

        
        out_path = os.path.join(output_dir, f"{num_teams}.json")
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)