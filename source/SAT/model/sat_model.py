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

    # per[i][w][p] true if i plays in week w, period p
    per = [[[Bool(f"p_{i}_{w}_{p}") for p in Periods] for w in Weeks] for i in Teams]

    return home, per


# -----------------------
# CARDINALITY CONSTRAINTS
# -----------------------

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

def constraint_each_pair_once(home, Teams, Weeks, s):
    for i, j in combinations(Teams, 2):
        if i != j:
            s.add(exactly_one([home[i][j][w] for w in Weeks] + [home[j][i][w] for w in Weeks]))


def constraint_one_match_per_week(home, Teams, Weeks, s):
    for i in Teams:
        for w in Weeks:
            week_match = []
            for j in Teams:
                if i != j:
                    week_match.append(home[i][j][w])
                    week_match.append(home[j][i][w])
            s.add(exactly_one(week_match))  


def constraint_max_two_per_period(per, Teams, Weeks, Periods, s):
    for t in Teams:
        for p in Periods:
            matches_period = [per[t][w][p] for w in Weeks]
            s.add(at_most_k(matches_period, 2))


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
                if i < j:  # only once per pair
                    match_occurs = Or(home[i][j][w], home[j][i][w])
                    
                    for p in Periods:
                        # If match occurs, then (¬per[i] ∨ per[j])
                        s.add(Or(Not(match_occurs), Not(per[i][w][p]), per[j][w][p]))
                        
                        # If match occurs, then (per[i] ∨ ¬per[j])
                        s.add(Or(Not(match_occurs), per[i][w][p], Not(per[j][w][p])))

def add_channelling_constraint(home, per, Teams, Weeks, Periods, s):
    constraint_period_consistency(home, per, Teams, Weeks, Periods, s)


# -------------------
# IMPLIED CONSTRAINTS
# -------------------

def constraint_two_teams_period(per, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            matches_period = [per[i][w][p] for i in Teams]
            s.add(exactly_k(matches_period, 2))


def constrain_home_symmetry(home, Teams, Weeks, s):
    for i, j in combinations(Teams, 2):
        for w in Weeks:
            s.add(Or(Not(home[i][j][w]), Not(home[j][i][w])))


def constraint_one_period_a_week(per, Teams, Weeks, Periods, s):
    for i in Teams:
        for w in Weeks:
            week_periods = [per[i][w][p] for p in Periods]
            s.add(exactly_one(week_periods))


def add_implied_constraints(home, per, Teams, Weeks, Periods, s):
    constraint_two_teams_period(per, Teams, Weeks, Periods, s)
    constrain_home_symmetry(home, Teams, Weeks, s)
    constraint_one_period_a_week(per, Teams, Weeks, Periods, s)


# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

def add_sb1(home, per, s):
    s.add(home[0][1][0]) 
    s.add(per[0][0][0])   
    s.add(per[1][0][0])   


def add_sb2(home, Teams, Weeks, s):
    for w in Weeks:
        opponent = w + 1
        if opponent < len(Teams):
            s.add(Or(home[0][opponent][w], home[opponent][0][w]))


def add_team_order_constraint(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            for w in Weeks:
                if i > j:
                    s.add(Not(home[i][j][w]))


def add_symmetry_breaking_constraints(home, per, Teams, Weeks, Periods, s, use_optimization):
    add_sb1(home, per, s)
    add_sb2(home, Teams, Weeks, s)
    if not use_optimization:
        add_team_order_constraint(home, Teams, Weeks, s)


# -----------------------
# OPTIMIZATION CONSTRAINT
# -----------------------

def add_max_diff_constraint(home, Teams, Weeks, max_diff, s):
    total_games = len(Weeks)
    
    for i in Teams:
        home_games = []
        for j in Teams:
            if i == j:
                continue
            for w in Weeks:
                home_games.append(home[i][j][w])
        
        min_home = (total_games - max_diff) // 2
        max_home = (total_games + max_diff) // 2
        
        s.add(at_least_k(home_games, min_home))
        s.add(at_most_k(home_games, max_home))


# -----------------------
# CALCULATE IMBALANCES
# -----------------------

def calculate_imbalances(model, home, Teams, Weeks):
    imbalances = {}

    for i in Teams:
        home_count = 0
        away_count = 0
        for j in Teams:
            if i == j:
                continue
            for w in Weeks:
                if is_true(model.evaluate(home[i][j][w])):
                    home_count += 1
                elif is_true(model.evaluate(home[j][i][w])):
                    away_count += 1

        imbalances[i] = abs(home_count - away_count)

    return imbalances
