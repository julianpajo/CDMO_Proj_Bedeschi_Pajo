from source.SMT.model import smt_model
from z3 import *


def build_model(n_teams, use_sb=False, use_optimization=False):
    """
    Builds the SMT model with specified parameters.
    
    Params:
        n_teams: Number of teams
        use_sb: Whether to use symmetry breaking
        use_optimization: Whether to use optimization techniques
        max_diff_constraint: Maximum home-away difference constraint
    
    Returns:
        tuple: (solver, variables, weeks, periods, extra_params)
    """
    
    solver = Solver()
    solver.set("random_seed", 42)    
    solver.set("timeout", 300_000)  # 5 minutes timeout
    
    # Get parameters
    num_teams, num_weeks, num_periods = smt_model.get_params(n_teams)
    Teams = list(range(num_teams))
    Weeks = list(range(num_weeks))
    Periods = list(range(num_periods))
    
    # Create SMT variables 
    y = smt_model.create_variables(Teams, Weeks, Periods)  
    
    # Add constraints
    smt_model.add_hard_constraints(y, Teams, Weeks, Periods, solver) 
    smt_model.add_implied_constraints(y, Teams, Weeks, Periods, solver)
    
    if use_sb:
        smt_model.add_symmetry_breaking_constraints(y, Teams, Weeks, Periods, solver, use_optimization) 
    
    extra_params = {
        "sb": use_sb,
        "opt": use_optimization,
        "teams_list": Teams,  
        "teams": n_teams,
    }

    """
    if use_optimization:
        max_imbalance = smt_model.max_imbalance(y, Teams, Weeks, Periods)
        solver.minimize(max_imbalance)
        extra_params["max_imbalance"] = max_imbalance

        # upper bound
        upper_bound = num_teams // 2
        solver.add(max_imbalance <= upper_bound)
    """
    
    
    return solver, y, Weeks, Periods, extra_params  