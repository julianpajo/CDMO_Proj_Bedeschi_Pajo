from source.SAT.model import sat_model
from z3 import *


def build_model(n_teams, use_sb=False, use_optimization=False, max_diff_constraint=None):
    """
    Builds the SAT model with specified parameters.
    
    Params:
        n_teams: Number of teams
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
        max_diff_constraint: maximum allowed home-away imbalance (optional)
    Returns:
        tuple: (solver, home, per, weeks, periods, extra_params)
    """
    solver = Solver()
    solver.set("random_seed", 42)
    solver.set("timeout", 300_000)  # 5 minutes timeout
    
    
    # Get parameters
    num_teams, num_weeks, num_periods = sat_model.get_params(n_teams)
    Teams = list(range(num_teams))
    Weeks = list(range(num_weeks))
    Periods = list(range(num_periods))
    
    # Create variables
    home, per = sat_model.create_variables(Teams, Weeks, Periods)
    
    # Add constraints
    sat_model.add_hard_constraints(home, per, Teams, Weeks, Periods, solver)
    sat_model.add_channeling_constraint(home, per, Teams, Weeks, Periods, solver)
    sat_model.add_implied_constraints(home, per, Teams, Weeks, Periods, solver)  

    if use_sb:
        sat_model.add_symmetry_breaking_constraints(home, per, Teams, Weeks, Periods, solver, use_optimization)

    
    extra_params = {
        "sb": use_sb,
        "opt": use_optimization,
        "teams_list": Teams,  
        "teams": n_teams,
        "max_diff_constraint": max_diff_constraint
    }
    
    return solver, home, per, Weeks, Periods, extra_params