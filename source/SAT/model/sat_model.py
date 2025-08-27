from itertools import combinations
from z3 import *


# ----------
# PARAMETERS
# ----------

def get_params(num_teams):
    if num_teams % 2:
        raise ValueError("Number of teams must be even")
    num_weeks = num_teams - 1
    num_periods = num_teams // 2
    return num_teams, num_weeks, num_periods
        

# ------------------
# DECISION VARIABLES
# ------------------

def create_variables(Teams, Weeks, Periods):
    n = len(Teams)

    # x[w][p][s][t] True if team i is in slot s (0=home, 1=away) of period p in week w
    x = [[[[Bool(f"x_{w}_{p}_{s}_{t}") for t in Teams] 
                                       for s in [0, 1]] 
                                       for p in Periods] 
                                       for w in Weeks]

    return x


# -----------------------
# CARDINALITY CONSTRAINTS
# -----------------------

def at_least_one_np(bool_vars):
  return Or(bool_vars)

def at_most_one_np(bool_vars):
  return And([Not(And(a, b)) for a, b in combinations(bool_vars, 2)])

def exactly_one_np(bool_vars):
  return And(at_least_one_np(bool_vars), at_most_one_np(bool_vars))

def at_least_k_np(bool_vars, k):
    return at_most_k_np([Not(var) for var in bool_vars], len(bool_vars)-k)

def at_most_k_np(bool_vars, k):
    return And([Or([Not(x) for x in X]) for X in combinations(bool_vars, k + 1)])

def exactly_k_np(bool_vars, k):
    return And(at_least_k_np(bool_vars, k), at_most_k_np(bool_vars, k))


def exactly_one_np(bool_vars, name):
  return PbEq([(x,1) for x in bool_vars], 1)

def at_most_k_np(bool_vars, k, name):
    return PbLe([(x, 1) for x in bool_vars], k) 

def at_least_k_np(bool_vars, k):
    return PbGe([(var, 1) for var in bool_vars], k)



def at_least_one(bool_vars):
   return Or(bool_vars)

def at_most_one(bool_vars, name=None):
    return PbLe([(var, 1) for var in bool_vars], 1)

def exactly_one(bool_vars, name=None):
    return PbEq([(var, 1) for var in bool_vars], 1)

def at_most_k(bool_vars, k, name=None):
    return PbLe([(var, 1) for var in bool_vars], k)

def at_least_k(bool_vars, k, name=None):
    return PbGe([(var, 1) for var in bool_vars], k)

def exactly_k(bool_vars, k, name=None):
    return And(at_most_k(bool_vars, k), at_least_k(bool_vars, k))


# ----------------
# HARD CONSTRAINTS
# ----------------

# (1) every team plays with every other team only once
def constraint_each_pair_once(x, Teams, Weeks, Periods, s):
    all_matches = {}
    
    for w in Weeks:
        for p in Periods:
            match_id = f"match_w{w}_p{p}"
            # Create a variable for each possible match in this slot
            for t1, t2 in combinations(Teams, 2):
                match_var = Bool(f"{match_id}_{t1}_{t2}")
                # Link to actual assignment
                s.add(match_var == Or(
                    And(x[w][p][0][t1], x[w][p][1][t2]),
                    And(x[w][p][0][t2], x[w][p][1][t1])
                ))
                if (t1, t2) not in all_matches:
                    all_matches[(t1, t2)] = []
                all_matches[(t1, t2)].append(match_var)
    
    # Each pair must appear exactly once
    for (t1, t2), match_vars in all_matches.items():
        s.add(exactly_one(match_vars, f"pair_{t1}_{t2}"))


# (2) every team plays once a week
def constraint_one_match_per_week(x, Teams, Weeks, Periods, s):
    for t in Teams:
        for w in Weeks:
            week_t = [x[w][p][0][t] for p in Periods] + [x[w][p][1][t] for p in Periods]
            s.add(exactly_one(week_t, f"team{t}_week{w}"))

# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(x, Teams, Weeks, Periods, s):
    for t in Teams:
        for p in Periods:
            s.add(at_most_k([x[w][p][slot][t] for w in Weeks for slot in [0,1]], 2, f"period{p}_team{t}"))


def add_hard_constraints(x, Teams, Weeks, Periods, s):
    constraint_each_pair_once(x, Teams, Weeks, Periods, s)
    constraint_one_match_per_week(x, Teams, Weeks, Periods, s)
    constraint_max_two_per_period(x, Teams, Weeks, Periods, s)


# -------------------
# IMPLIED CONSTRAINTS
# -------------------

# (4) one match per slot
def constraint_one_match_per_slot(x, Teams, Weeks, Periods, s):
    for p in Periods:
        for w in Weeks:
            s.add(exactly_one([x[w][p][0][i] for i in Teams], f"home_week{w}_period{p}"))
            s.add(exactly_one([x[w][p][1][j] for j in Teams], f"away_week{w}_period{p}"))
            for t in Teams:
                # Non same team
                s.add(Not(And(x[w][p][0][t], x[w][p][1][t])))


# (5) two distinct team in a match
def constraint_diff_teams_per_match(x, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            for t in Teams:
                s.add(Or(Not(x[w][p][0][t]), Not(x[w][p][1][t])))


def add_implied_constraints(x, Teams, Weeks, Periods, s):
    constraint_diff_teams_per_match(x, Teams, Weeks, Periods, s)
    constraint_one_match_per_slot(x, Teams, Weeks, Periods, s)



# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

# (sb1) Fix the first match to be team 0 vs team 1
def add_sb1(x, s):
    s.add(x[0][0][0][0])
    s.add(x[0][0][1][1])


# (sb2) Fix opponents for team 0
def add_sb2(x, Teams, Weeks, Periods, s):
    for w in Weeks:
        if w < len(Teams) - 1:
            opponent = w + 1
            matches = []
            for p in Periods:
                # team 0 home, opponent away
                matches.append(And(x[w][p][0][0], x[w][p][1][opponent]))
                # team 0 away, opponent home
                matches.append(And(x[w][p][1][0], x[w][p][0][opponent]))
            s.add(exactly_one(matches, f"sb_team0_week{w}"))


def add_team_order_constraint(x, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            for t1 in Teams:
                for t2 in Teams:
                    if t1 > t2:
                        invalid_match = And(x[w][p][0][t1], x[w][p][1][t2])
                        s.add(Not(invalid_match))



def add_symmetry_breaking_constraints(x, Teams, Weeks, Periods, s, use_optimization):
    add_sb1(x, s)
    add_sb2(x, Teams, Weeks, Periods, s)
    if not use_optimization:
        add_team_order_constraint(x, Teams, Weeks, Periods, s)



# -----------------------
# OPTIMIZATION CONSTRAINT
# -----------------------
def add_max_diff_constraint(x, Teams, Weeks, Periods, max_diff, s):
    """
    Boolean-only constraint for home-away difference
    """
    total_weeks = len(Weeks)
    
    for t in Teams:
        home_games = []
        for w in Weeks:
            for p in Periods:
                home_games.append(x[w][p][0][t])
        
        # The number of home games must be between min_home and max_home
        min_home = (total_weeks - max_diff) // 2
        max_home = (total_weeks + max_diff) // 2
        
        if min_home == max_home:
            # Exactly k home games
            s.add(exactly_k(home_games, min_home, f"exactly_{min_home}_team{t}"))
        else:
            # Range constraint
            if min_home > 0:
                s.add(at_least_k(home_games, min_home, f"at_least_{min_home}_team{t}"))
            if max_home < total_weeks:
                s.add(at_most_k(home_games, max_home, f"at_most_{max_home}_team{t}"))



def calculate_imbalances(model, variables, Teams, Weeks, Periods):
    """Calculate home-away imbalances for each team correctly"""
    imbalances = {}
    for t in Teams:
        home = 0
        away = 0
        
        for w in Weeks:
            for p in Periods:
                if is_true(model.evaluate(variables[w][p][0][t])):
                    home += 1
                if is_true(model.evaluate(variables[w][p][1][t])):
                    away += 1
        
        # Each team should play exactly len(Weeks) games
        # So home + away should equal len(Weeks)
        imbalances[t] = abs(home - away)
        #print(f"Team {t}: {home} home, {away} away, imbalance: {abs(home-away)}")
    
    return imbalances