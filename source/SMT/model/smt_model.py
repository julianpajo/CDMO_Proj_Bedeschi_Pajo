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

    # y[w][p][s] in Teams: team y[w][p][s] plays in slot [0,1] (0=home, 1=away) of period p in week w
    y = [[[Int(f"y_{w}_{p}_{slot}") for slot in [0, 1]] 
                                 for p in Periods] 
                                 for w in Weeks]

    return y



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
def constraint_each_pair_once(y, Teams, Weeks, Periods, s):
    for t1 in Teams:
        for t2 in Teams:
            if t1 < t2:
                matches = [
                    Or(
                        And(y[w][p][0] == t1, y[w][p][1] == t2),
                        And(y[w][p][0] == t2, y[w][p][1] == t1)
                    )
                    for w in Weeks for p in Periods
                ]
                s.add(exactly_one(matches, f"pair_{t1}_{t2}"))


# (2) every team plays once a week
def constraint_one_match_per_week(y, Teams, Weeks, Periods, s):
    for t in Teams:
        for w in Weeks:
            matches = [Or(y[w][p][0] == t, y[w][p][1] == t) for p in Periods]
            s.add(exactly_one(matches, f"team{t}_week{w}"))
    

# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(y, Teams, Weeks, Periods, s):
    for t in Teams:
        for p in Periods:
            matches = [
                Or(y[w][p][0] == t, y[w][p][1] == t)
                for w in Weeks
            ]
            s.add(at_most_k(matches, 2, f"team{t}_period{p}"))
    


def add_hard_constraints(y, Teams, Weeks, Periods, s):
    constraint_each_pair_once(y, Teams, Weeks, Periods, s)
    constraint_one_match_per_week(y, Teams, Weeks, Periods, s)
    constraint_max_two_per_period(y, Teams, Weeks, Periods, s)


# -------------------
# IMPLIED CONSTRAINTS
# -------------------

# (4) one match per slot
def constraint_one_match_per_slot(y, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            # enforce validity of teams (between 0 and n_teams-1)
            # enforce one match home, one match away
            s.add(And(y[w][p][0] >= min(Teams), y[w][p][0] <= max(Teams)))
            s.add(And(y[w][p][1] >= min(Teams), y[w][p][1] <= max(Teams)))
    


# (5) two distinct team in a match
def constraint_diff_teams_per_match(y, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            # teams in the same match must be different
            s.add(y[w][p][0] != y[w][p][1])
    


def add_implied_constraints(y, Teams, Weeks, Periods, s):
    constraint_one_match_per_slot(y, Teams, Weeks, Periods, s)
    constraint_diff_teams_per_match(y, Teams, Weeks, Periods, s)    



# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

# (sb1) Fix the first match to be team 0 vs team 1
def add_sb1(y, s):
    s.add(y[0][0][0] == 0)  # team 0: home
    s.add(y[0][0][1] == 1)  # team 1: away


# (sb2) Fix opponents for team 0
def add_sb2(y, Teams, Weeks, Periods, s):
    for w in Weeks:
        if w < len(Teams) - 1:
            opponent = w + 1
            # team 0 and the opponent must be in the same period (already same week)
            match = []
            for p in Periods:
                match.append(And(y[w][p][0] == 0, y[w][p][1] == opponent))
                match.append(And(y[w][p][0] == opponent, y[w][p][1] == 0))
            
            s.add(exactly_one(match, name=f"sb2_team0_vs_{opponent}_week{w}"))



def add_team_order_constraint(y, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            home_team = y[w][p][0]
            away_team = y[w][p][1]

            s.add(home_team < away_team)



def add_symmetry_breaking_constraints(y, Teams, Weeks, Periods, s, use_optimization):
    add_sb1(y, s)
    add_sb2(y, Teams, Weeks, Periods, s)
    if not use_optimization:
        add_team_order_constraint(y, Teams, Weeks, Periods, s)



# ------------
# OPTIMIZATION
# ------------
def team_imbalance(y, t, Weeks, Periods):
    home = Sum([If(y[w][p][0] == t, 1, 0) for w in Weeks for p in Periods])
    away = Sum([If(y[w][p][1] == t, 1, 0) for w in Weeks for p in Periods])

    imbalance = home - away

    return If(imbalance >= 0, imbalance, -imbalance)


def max_imbalance(y, Teams, Weeks, Periods):
    imbalances = []
    for t in Teams:
        imb = team_imbalance(y, t, Weeks, Periods)
        imbalances.append(imb)
    
    # look for the maximum value
    max_imb = imbalances[0]
    for i in range(1, len(Teams)):
        max_imb = If(imbalances[i] > max_imb, imbalances[i], max_imb)
    
    return max_imb