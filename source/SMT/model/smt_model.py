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

    # home[i][j][w] true if i plays at home against j in week w
    home = []
    for i in Teams:
        home_row = []
        for j in Teams:
            if i == j:
                home_row.append([])  # empty list for i = j
            else:
                home_row.append([Bool(f"h_{i}_{j}_{w}") for w in Weeks])
        home.append(home_row)
    
    # period[i,w] = p means team i plays in period p in week w
    per = [[Int(f"p_{i}_{w}") for w in Weeks] for i in Teams]

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
    for i, j in combinations(Teams, 2):
        if i < j:
            s.add(exactly_one([home[i][j][w] for w in Weeks] + [home[j][i][w] for w in Weeks]))


# (2) every team plays once a week
def constraint_one_match_per_week(home, Teams, Weeks, s):
    for i in Teams:
        for w in Weeks:
            week_match = []
            for j in Teams:
                if i != j:
                    week_match.append(home[i][j][w])
                    week_match.append(home[j][i][w])
            s.add(exactly_one(week_match)) 
    

# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(per, Teams, Weeks, Periods, s):
    for i in Teams:
        for p in Periods:
            s.add(Sum([If(per[i][w] == p, 1, 0) for w in Weeks]) <= 2)
    


def add_hard_constraints(home, per, Teams, Weeks, Periods, s):
    constraint_each_pair_once(home, Teams, Weeks, s)
    constraint_one_match_per_week(home, Teams, Weeks, s)
    constraint_max_two_per_period(per, Teams, Weeks, Periods, s)


# -----------------
# DOMAIN CONSTRAINT
# -----------------
def add_domain_constrain(per, Teams, Weeks, Periods, s):
    for i in Teams:
        for w in Weeks:
            s.add(And(per[i][w] >= 0, per[i][w] < len(Periods)))



# ----------------------
# CHANNELLING CONSTRAINT
# ----------------------

def constraint_period_consistency(home, per, Teams, Weeks, Periods, s):
    for w in Weeks:
        for i, j in combinations(Teams, 2):
            if i < j:
                plays_together = Or(home[i][j][w], home[j][i][w])
                s.add(Implies(plays_together, per[i][w] == per[j][w]))


def add_channelling_constraint(home, per, Teams, Weeks, Periods, s):
    constraint_period_consistency(home, per, Teams, Weeks, Periods, s)


# -------------------
# IMPLIED CONSTRAINTS
# -------------------

def constraint_two_teams_per_period(per, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            # Count how many teams play in period p in week w
            s.add(Sum([If(per[i][w] == p, 1, 0) for i in Teams]) == 2)


# home[i,j,w] ==> Not(home[j,i,w])
def constrain_home_symmetry(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            if i < j:
                for w in Weeks:
                    # they cannot be both true
                    s.add(Or(Not(home[i][j][w]), Not(home[j][i][w])))

    


def add_implied_constraints(home, per, Teams, Weeks, Periods, s):
    constraint_two_teams_per_period(per, Teams, Weeks, Periods, s)
    constrain_home_symmetry(home, Teams, Weeks, s) 



# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

# (sb1) Fix the first match to be team 0 vs team 1
def add_sb1(home, per, s):
    # Fix first match: team 0 vs team 1 in period 0
    s.add(home[0][1][0])
    s.add(per[0][0] == 0)
    s.add(per[1][0] == 0)


# (sb2) Fix opponents for team 0
def add_sb2(home, Teams, Weeks, s):
    for w in Weeks:
        if w < len(Teams) - 1:
            opponent = w + 1
            s.add(exactly_one([home[0][opponent][w], home[opponent][0][w]]))



def add_team_order_constraint(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            if i > j:
                for w in Weeks:
                    s.add(Not(home[i][j][w]))



def add_symmetry_breaking_constraints(home, per, Teams, Weeks, s, use_optimization):
    add_sb1(home, per, s)
    add_sb2(home, Teams, Weeks, s)
    if not use_optimization:
        add_team_order_constraint(home, Teams, Weeks, s)
