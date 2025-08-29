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

    # home[i,w] = j means team i plays at home against team j in week w
    home = {}   
    for i in Teams:
        for w in Weeks:
            home[(i, w)] = Int(f"home_{i}_{w}")
    
    # period[i,w] = p means team i plays in period p in week w
    per = {}
    for i in Teams:
        for w in Weeks:
            per[(i, w)] = Int(f"period_{i}_{w}")

    return home, per



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
def constraint_each_pair_once(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            if i < j:
                # Either i plays home against j or j plays home against i exactly once
                matches_i = [If(home[(i, w)] == j, 1, 0) for w in Weeks]
                matches_j = [If(home[(j, w)] == i, 1, 0) for w in Weeks]
                s.add(Sum(matches_i) + Sum(matches_j) == 1)


# (2) every team plays once a week
def constraint_one_match_per_week(home, Teams, Weeks, s):
    for i in Teams:
        for w in Weeks:
            home_game = If(home[(i, w)] != -1, 1, 0)
            away_games = Sum([If(home[(j, w)] == i, 1, 0) for j in Teams if j != i])
            s.add(home_game + away_games == 1)
            s.add(Implies(home[(i, w)] != -1, 
                         And(home[(i, w)] >= 0, home[(i, w)] < len(Teams), home[(i, w)] != i)))
    

# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(per, Teams, Weeks, Periods, s):
    for t in Teams:
        for p in Periods:
            period_matches = [If(per[(t, w)] == p, 1, 0) for w in Weeks]
            s.add(Sum(period_matches) <= 2)
    


def add_hard_constraints(home, per, Teams, Weeks, Periods, s):
    constraint_each_pair_once(home, Teams, Weeks, s)
    constraint_one_match_per_week(home, Teams, Weeks, s)
    constraint_max_two_per_period(per, Teams, Weeks, Periods, s)


# ----------------------
# CHANNELLING CONSTRAINT
# ----------------------

def constraint_period_consistency(home, per, Teams, Weeks, Periods, s):
    for w in Weeks:
        for i in Teams:
            for j in Teams:
                if i != j:
                    # If i plays against j in week w, they must have the same period
                    plays_together = Or(home[(i, w)] == j, home[(j, w)] == i)
                    same_period = per[(i, w)] == per[(j, w)]
                    s.add(Implies(plays_together, same_period))


def add_channelling_constraint(home, per, Teams, Weeks, Periods, s):
    constraint_period_consistency(home, per, Teams, Weeks, Periods, s)



# -------------------
# IMPLIED CONSTRAINTS
# -------------------

def constraint_no_self_matches(home, Teams, Weeks, s):
    for i in Teams:
        for w in Weeks:
            s.add(home[(i, w)] != i)
    

def constraint_two_teams_per_period(per, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            # Count how many teams play in period p in week w
            teams_in_period = [If(per[(i, w)] == p, 1, 0) for i in Teams]
            s.add(Sum(teams_in_period) == 2)


# home[i,j,w] ==> Not(home[j,i,w])
def constrain_home_symmetry(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            if i == j:
                continue
            for w in Weeks:
                # If i plays home against j, then j cannot play home against i
                s.add(Implies(home[(i, w)] == j, home[(j, w)] != i))

    


def add_implied_constraints(home, per, Teams, Weeks, Periods, s):
    constraint_no_self_matches(home, Teams, Weeks, s)
    constraint_two_teams_per_period(per, Teams, Weeks, Periods, s)
    constrain_home_symmetry(home, Teams, Weeks, s) 



# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

# (sb1) Fix the first match to be team 0 vs team 1
def add_sb1(home, per, s):
    # Fix first match: team 0 vs team 1 in period 0
    s.add(home[(0, 0)] == 1)
    s.add(home[(1, 0)] == -1)  # team 1 doesn't play at home
    s.add(per[(0, 0)] == 0)
    s.add(per[(1, 0)] == 0)


# (sb2) Fix opponents for team 0
def add_sb2(home, Teams, Weeks, s):
    for w in Weeks:
        if w < len(Teams) - 1:
            opponent = w + 1
            option1 = home[(0, w)] == opponent  # team 0 home vs w+1
            option2 = home[(opponent, w)] == 0   # team w+1 home vs 0
            
            s.add(Xor(option1, option2))



def add_team_order_constraint(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            if i >= j:
                for w in Weeks:
                    s.add(home[(i, w)] != j)



def add_symmetry_breaking_constraints(home, per, Teams, Weeks, s, use_optimization):
    add_sb1(home, per, s)
    add_sb2(home, Teams, Weeks, s)
    if not use_optimization:
        add_team_order_constraint(home, Teams, Weeks, s)



# ------------
# OPTIMIZATION
# ------------
def team_imbalance(home, t, Teams, Weeks):
    home_games = Sum([If(home[(t, w)] != -1, 1, 0) for w in Weeks])
    away_games = Sum([If(Or([home[(j, w)] == t for j in Teams if j != t]), 1, 0) for w in Weeks])

    imbalance = home_games - away_games

    return If(imbalance >= 0, imbalance, -imbalance)


def max_imbalance(home, Teams, Weeks, s):
    max_imb = Int("max_imbalance")
    for t in Teams:
        s.add(max_imb >= team_imbalance(home, t, Teams, Weeks))

    return max_imb