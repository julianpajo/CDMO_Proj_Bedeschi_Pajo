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

    home = {}   # home[i,j,w] true if i plays at home against j in week w
    per = {}    # per[i,w,p] true if i plays in week w, period p
    
    for i in Teams:
        for j in Teams:
            for w in Weeks:
                home[(i, j, w)] = Bool(f"home_{i}_{j}_{w}")
    
    for i in Teams:
        for w in Weeks:
            for p in Periods:
                per[(i, w, p)] = Bool(f"period_{i}_{w}_{p}")


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



def at_most_k_seq(bool_vars, k, name=None):
    """
    Sequential counter encoding - O(n*k) auxiliary variables
    MOLTO più efficiente per k piccolo (2-3) e n medio (100-200)
    """
    if k >= len(bool_vars):
        return True
    if k <= 0:
        return And([Not(var) for var in bool_vars])
    
    n = len(bool_vars)
    if n == 0:
        return True
    
    # Create auxiliary variables
    s = [[Bool(f"{name}_s_{i}_{j}" if name else f"s_{i}_{j}") 
          for j in range(k)] for i in range(n-1)]
    
    constraints = []
    
    # First element constraints
    constraints.append(Or(Not(bool_vars[0]), s[0][0]))
    for j in range(1, k):
        constraints.append(Not(s[0][j]))
    
    # Middle elements
    for i in range(1, n-1):
        constraints.append(Or(Not(bool_vars[i]), s[i][0]))
        constraints.append(Or(Not(s[i-1][0]), s[i][0]))
        
        for j in range(1, k):
            constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][j-1]), s[i][j]))
            constraints.append(Or(Not(s[i-1][j]), s[i][j]))
        
        constraints.append(Or(Not(bool_vars[i]), Not(s[i-1][k-1])))
    
    # Last element constraint
    constraints.append(Or(Not(bool_vars[n-1]), Not(s[n-2][k-1])))
    
    return And(*constraints)

def exactly_k_seq(bool_vars, k, name=None):
    """Exactly k using sequential counter"""
    return And(at_most_k_seq(bool_vars, k, name), 
               at_least_k_seq(bool_vars, k, name))

def at_least_k_seq(bool_vars, k, name=None):
    """At least k using negation of at_most k-1"""
    if k <= 0:
        return True
    if k > len(bool_vars):
        return False
    return Not(at_most_k_seq(bool_vars, k-1, name))


# ----------------
# HARD CONSTRAINTS
# ----------------

# (1) every team plays with every other team only once
def constraint_each_pair_once(home, Teams, Weeks, s):
    for i, j in combinations(Teams, 2):
        s.add(exactly_one([home[(i,j,w)] for w in Weeks] + [home[(j,i,w)] for w in Weeks]))


# (2) every team plays once a week
def constraint_one_match_per_week(home, Teams, Weeks, s):
    for i in Teams:
        for w in Weeks:
            week_match = [home[(i,j,w)] for j in Teams if i != j] + [home[(j,i,w)] for j in Teams if i != j]
            s.add(exactly_one(week_match))  


# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(per, Teams, Weeks, Periods, s):
    for t in Teams:
        for p in Periods:
            matches_period = [per[(t, w, p)] for w in Weeks]
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
        for p in Periods:
            # two teams per match
            s.add(exactly_k([per[(i,w,p)] for i in Teams], 2))
        # channelling: if i plays against j in week w, they must be in the same period
        for i, j in combinations(Teams, 2):
            match_occurs = Or(home.get((i,j,w), False), home.get((j,i,w), False))
            same_period = Or([And(per[(i,w,p)], per[(j,w,p)]) for p in Periods])
            
            # A -> B becomes Not(A) ∨ B
            s.add(Or(Not(match_occurs), same_period))


def add_channelling_constraint(home, per, Teams, Weeks, Periods, s):
    constraint_period_consistency(home, per, Teams, Weeks, Periods, s)



# -------------------
# IMPLIED CONSTRAINTS
# -------------------

# No self matches
def constraint_diff_teams(home, Teams, Weeks, s):
    for i in Teams:
        for w in Weeks:
            s.add(Not(home[(i, i, w)]))


# Two teams per period
def constraint_two_teams_period(per, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            matches_period = []
            for i in Teams:
                if (i, w, p) in per:
                    matches_period.append(per[(i, w, p)])
        
            if matches_period:
                s.add(exactly_k(matches_period, 2))


# home[i,j,w] ==> Not(home[j,i,w])
def constrain_home_symmetry(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            if i == j:
                continue
            for w in Weeks:
                # they cannot be both true
                s.add(Or(Not(home[(i, j, w)]), Not(home[(j, i, w)])))


def constraint_one_period_a_week(per, Teams, Weeks, Periods, s):
    for i in Teams:
        for w in Weeks:
            week_periods = [per[(i, w, p)] for p in Periods]
            s.add(exactly_one(week_periods))


def add_implied_constraints(home, per, Teams, Weeks, Periods, s):
    constraint_diff_teams(home, Teams, Weeks, s)
    constraint_two_teams_period(per, Teams, Weeks, Periods, s)
    constrain_home_symmetry(home, Teams, Weeks, s)
    constraint_one_period_a_week(per, Teams, Weeks, Periods, s)


# -----------------------------
# SYMMETRY BREAKING CONSTRAINTS
# -----------------------------

# (sb1) Fix the first match to be team 0 vs team 1
def add_sb1(home, per, s):
    s.add(home[(0, 1, 0)])  # team 0 is home against 1 in week 0
    s.add(Not(home[(1, 0, 0)])) # implicit
    s.add(per[(0, 0, 0)])   # team 0 plays week 0, period 0    
    s.add(per[(1, 0, 0)])   # team 1 plays week 0, period 0 


# (sb2) Fix opponents for team 0
def add_sb2(home, Teams, Weeks, s):
    for w in Weeks:
        opponent = w + 1
        if opponent < len(Teams):
            s.add(Or(home[(0, opponent, w)], home[(opponent, 0, w)]))


def add_team_order_constraint(home, Teams, Weeks, s):
    for i in Teams:
        for j in Teams:
            for w in Weeks:
                if i > j:
                    # we fix i < j
                    s.add(Not(home[(i,j,w)]))



def add_symmetry_breaking_constraints(home, per, Teams, Weeks, Periods, s, use_optimization):
    add_sb1(home, per, s)
    add_sb2(home, Teams, Weeks, s)
    if not use_optimization:
        add_team_order_constraint(home, Teams, Weeks, s)



# -----------------------
# OPTIMIZATION CONSTRAINT
# -----------------------
# home-away max imbalance
# -----------------------

def add_max_diff_constraint(home, Teams, Weeks, max_diff, s):
    """
    Adds a Boolean-only SAT constraint to bound the home-away imbalance for each team.
    home[i,j,w] = True if i plays at home against j in week w
    """
    total_games = len(Weeks)
    
    for t in Teams:
        home_games = []
        for j in Teams:
            if t == j:
                continue
            for w in Weeks:
                if (t,j,w) in home:
                    home_games.append(home[(t,j,w)])
                elif (j,t,w) in home:  # opzionale, se consideri i match in trasferta
                    home_games.append(Not(home[(j,t,w)]))
        
        if not home_games:
            print(f"DEBUG: nessuna partita trovata per team {t}")
            continue
        
        min_home = (total_games - max_diff) // 2
        max_home = (total_games + max_diff) // 2
        
        s.add(at_least_k(home_games, min_home))
        s.add(at_most_k(home_games, max_home))
                

# -----------------------
# CALCULATE IMBALANCES FROM MODEL
# -----------------------
def calculate_imbalances(model, home, Teams, Weeks):
    """
    Computes home-away imbalances for each team from a solved model.
    """
    imbalances = {}

    for i in Teams:
        home_count = 0
        away_count = 0
        for j in Teams:
            if i == j:
                continue    # skip self-match
            for w in Weeks:
                if (i,j,w) in home and is_true(model.evaluate(home[(i, j, w)])):
                    home_count += 1
                elif (j,i,w) in home and is_true(model.evaluate(home[(j, i, w)])):
                        away_count += 1

        imbalances[i] = abs(home_count - away_count)

    return imbalances
