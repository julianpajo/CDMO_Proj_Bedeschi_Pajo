from source.SAT.model import sat_model
from z3 import *


def build_model(n_teams, use_sb=False, use_optimization=False, max_diff_constraint=None):
    """
    Builds the SAT model with specified parameters.
    
    Params:
        n_teams: Number of teams
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
    
    Returns:
        tuple: (solver, variables, weeks, periods, extra_params)
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
    x = sat_model.create_variables(Teams, Weeks, Periods)
    
    # Add constraints
    sat_model.add_hard_constraints(x, Teams, Weeks, Periods, solver)
    sat_model.add_implied_constraints(x, Teams, Weeks, Periods, solver)
    
    if use_sb:
        sat_model.add_symmetry_breaking_constraints(x, Teams, Weeks, Periods, solver, use_optimization)


    if use_optimization and max_diff_constraint is not None:
        sat_model.add_max_diff_constraint(x, Teams, Weeks, Periods, max_diff_constraint, solver)

    
    extra_params = {
        "sb": use_sb,
        "opt": use_optimization,
        "teams_list": Teams,  
        "teams": n_teams,
        "max_diff_constraint": max_diff_constraint
    }
    
    return solver, x, Weeks, Periods, extra_params