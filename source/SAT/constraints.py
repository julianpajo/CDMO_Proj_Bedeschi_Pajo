from z3 import *
from itertools import combinations


## ------- CARDINALITY CONSTRAINTS ------- 


## PAIRWISE ENCODING

def at_least_one_np(bool_vars):
  return Or(bool_vars)

def at_most_one_np(bool_vars):
  return And([Not(And(a, b)) for a, b in combinations(bool_vars, 2)])

def exactly_one_np(bool_vars):
  return And(at_most_one_np(bool_vars), at_least_one_np(bool_vars))


def at_most_k_np(bool_vars, k):
    return And([Or([Not(x) for x in X]) for X in combinations(bool_vars, k + 1)])

# def at_most_k_np(bool_vars, k):
#     return PbLe([(x, 1) for x in bool_vars], k) 

def at_least_k_np(bool_vars, k):
    return at_most_k_np([Not(var) for var in bool_vars], len(bool_vars)-k)

# def at_least_k_np(bool_vars, k):
#     return PbGe([(var, 1) for var in bool_vars], k)


## ---------- CONSTRAINTS ----------

# (1) Teams in a match must be different
def constraint_diff_teams_in_a_match(H,A,Teams,Weeks,Periods,s):
    for w in Weeks:
        for p in Periods:
            for t in Teams:
                s.add(Not(And(H[w][p][t], A[w][p][t])))


# (2) Each team plays exactly once per week (it can be either at home or away)
def constraint_only_once_in_a_week(H,A,Teams,Weeks,Periods,s):
    for w in Weeks:
        for t in Teams:
            occurrence = [H[w][p][t] for p in Periods] + [A[w][p][t] for p in Periods]
            s.add(exactly_one_np(occurrence))


# (3) Each team plays at most twice in the same period
def constraint_at_most_twice_in_a_period(H,A,Teams,Weeks,Periods,s):
    for t in Teams:
        for p in Periods:
            occurence = [H[w][p][t] for w in Weeks] + [A[w][p][t] for w in Weeks]
            s.add(at_most_k_np(occurence, 2))


# (4) Each match {t1, t2} occurs exactly once
def constraint_only_once_each_match(H,A,Teams,Weeks,Periods,s):
    for t1 in Teams:
        for t2 in Teams:
            if t1 < t2:
                occurrences = []
                for w in Weeks:
                    for p in Periods:
                        # let's save all occurences where t1 plays home and t2 away
                        occurrences.append(And(H[w][p][t1], A[w][p][t2]))
                        # let's save all occurences where t2 plays home and t1 away
                        occurrences.append(And(H[w][p][t2], A[w][p][t1]))

                s.add(exactly_one_np(occurrences))


# (5) Exactly one match per slot
def constraint_one_match_per_slot(H, A, Teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            home_vars = [H[w][p][t] for t in Teams]
            away_vars = [A[w][p][t] for t in Teams]
            s.add(exactly_one_np(home_vars))
            s.add(exactly_one_np(away_vars))

                

## ---------- SYMMETRY BREAKING CONSTRAINTS ----------

# (SB1) We fix all matches of the first week
def sb1_fixing_first_week(H,A,Teams,Weeks,Periods,s):
    for p in Periods:
        home_t = 2*p
        away_t = 2*p + 1

        # for each period we fix the right match
        s.add(H[0][p][home_t] == True)
        s.add(A[0][p][away_t] == True)

        # and force the others to be false
        for t in Teams:
            if t != home_t:
                s.add(H[0][p][t] == False)
            if t != away_t:
                s.add(A[0][p][t] == False)


# (SB2) If team_i >= team_j, then team_i cannot be at home and team_j away
def sb2_fixing_team_order(H,A,Teams,Weeks,Periods,s):
    for w in Weeks:
        for p in Periods:
            for i in Teams:
                for j in Teams:
                    if i >= j:
                        s.add(Not(And(H[w][p][i], A[w][p][j])))
