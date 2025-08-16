from z3 import *
from itertools import combinations


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

    # M[w][p][i][j] True if i vs j in week w, period p
    M = [[[[ Bool(f"M_{w}_{p}_{i}_{j}") for j in range(n)] for i in range(n)] for p in Periods] for w in Weeks]

    return M


# -----------------------
# CARDINALITY CONSTRAINTS
# -----------------------

def at_least_one(bool_vars):
  return Or(bool_vars)

def at_most_one(bool_vars):
  return And([Not(And(a, b)) for a, b in combinations(bool_vars, 2)])

def exactly_one(bool_vars):
  return PbEq([(x,1) for x in bool_vars], 1)


def at_most_k_np(bool_vars, k):
    return PbLe([(x, 1) for x in bool_vars], k) 

def at_least_k_np(bool_vars, k):
    return PbGe([(var, 1) for var in bool_vars], k)


# ----------------
# HARD CONSTRAINTS
# ----------------

# (1) every team plays with every other team only once
def constraint_each_pair_once(M, n_teams, Weeks, Periods, s):
    for i, j in combinations(range(n_teams), 2):
        s.add(exactly_one([Or(M[w][p][i][j], M[w][p][j][i]) for w in Weeks for p in Periods]))


# (2) every team plays once a week
def constraint_one_match_per_week(M, n_teams, Weeks, Periods, s):
    for i in range(n_teams):
        for w in Weeks:
            s.add(exactly_one(
                [M[w][p][i][j] for p in Periods for j in range(n_teams) if j != i] + 
                [M[w][p][j][i] for p in Periods for j in range(n_teams) if j != i]
            ))

# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(M, n_teams, Weeks, Periods, s):
    for i in range(n_teams):
        for p in Periods:
            appearances_i = []
            for w in Weeks:
                # team i plays at home
                appearances_i += [M[w][p][i][j] for j in range(n_teams) if i != j]
                # team i plays away
                appearances_i += [M[w][p][j][i] for j in range(n_teams) if i != j]
            s.add(at_most_k_np(appearances_i, 2))


# -------------------
# IMPLIED CONSTRAINTS
# -------------------

# (4) one match per period
def constraint_one_match_per_slot(M, n_teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            slot_matches = [M[w][p][i][j] for i in range(n_teams) 
                                          for j in range(n_teams) if i != j]
            s.add(exactly_one(slot_matches))

# (5) it's not possible to have a match with the same teams
def constraint_diff_teams_per_match(M, n_teams, Weeks, Periods, s):
    s.add([Not(M[w][p][i][i]) for w in Weeks for p in Periods for i in range(n_teams)])


# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

# (sb1) The first match (first week and period) is between the first and the second teams (0-1)
def sb1(M, s):
    s.add(M[0][0][0][1])


# (sb2) Fix opponents for team 0
def sb2(M, n_teams, Weeks, Periods, s):
    for w in Weeks:
        if w < n_teams - 1:
            opponent = w + 1 # team 1 in week 0, team 2 in week 1, etc.
            s.add(exactly_one([M[w][p][0][opponent] for p in Periods]))


# (sb3) Ordering
def sb3(M, n_teams, Weeks, Periods, s):
    s.add([Not(M[w][p][i][j]) 
          for w in Weeks 
          for p in Periods 
          for i in range(n_teams) 
          for j in range(n_teams) 
          if i >= j])



# ---------------------
# CONSTRAINTS FUNCTIONS
# ---------------------

def add_hard_constraints(M, n_teams, Weeks, Periods, s):
    constraint_each_pair_once(M, n_teams, Weeks, Periods, s)
    constraint_one_match_per_week(M, n_teams, Weeks, Periods, s)
    constraint_max_two_per_period(M, n_teams, Weeks, Periods, s)


def add_implied_constraints(M, n_teams, Weeks, Periods, s):
    constraint_one_match_per_slot(M, n_teams, Weeks, Periods, s)
    constraint_diff_teams_per_match(M, n_teams, Weeks, Periods, s)


def add_symmetry_breaking_constraints(M, n_teams, Weeks, Periods, s):
    sb1(M, s)
    sb2(M, n_teams, Weeks, Periods, s)
    sb3(M, n_teams, Weeks, Periods, s)