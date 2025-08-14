from z3 import *
from itertools import combinations

################ CARDINALITY CONSTRAINTS ################

def at_least_one(bool_vars):
  return Or(bool_vars)

def at_most_one(bool_vars):
  return And([Not(And(a, b)) for a, b in combinations(bool_vars, 2)])

def exactly_one(bool_vars):
  #return And(at_most_one(bool_vars), at_least_one(bool_vars))
  return PbEq([(x,1) for x in bool_vars], 1)


#def at_most_k_np(bool_vars, k):
#    return And([Or([Not(x) for x in X]) for X in combinations(bool_vars, k + 1)])

def at_most_k_np(bool_vars, k):
    return PbLe([(x, 1) for x in bool_vars], k) 

#def at_least_k_np(bool_vars, k):
#    return at_most_k_np([Not(var) for var in bool_vars], len(bool_vars)-k)

def at_least_k_np(bool_vars, k):
    return PbGe([(var, 1) for var in bool_vars], k)



#######################  CONSTRAINTS  #######################

# (1) every team plays with every other team only once
def constraint_each_pair_once(M, n_teams, Weeks, Periods, s):
    for i in range(n_teams):
        for j in range(i+1, n_teams):
            s.add(exactly_one([M[w][p][i][j] for w in Weeks for p in Periods]))


# (2) every team plays once a week
def constraint_one_match_per_week(M, n_teams, Weeks, Periods, s):
    for i in range(n_teams):
        for w in Weeks:
            s.add(exactly_one([
                M[w][p][i][j] if i < j else M[w][p][j][i]
                for p in Periods
                for j in range(n_teams) if j != i
            ]))

# (3) every team plays at most twice in the same period over the tournament
def constraint_max_two_per_period(M, n_teams, Weeks, Periods, s):
    for t in range(n_teams):
        for p in Periods:
            matches = []
            for w in Weeks:
                for j in range(t+1, n_teams):
                    matches.append(M[w][p][t][j])
                for i in range(t):
                    matches.append(M[w][p][i][t])
            s.add(at_most_k_np(matches, 2))

# (4) one match per period
def constraint_one_match_per_slot(M, n_teams, Weeks, Periods, s):
    for w in Weeks:
        for p in Periods:
            slot_matches = [M[w][p][i][j] for i in range(n_teams) 
                                          for j in range(i+1, n_teams)]
            s.add(exactly_one(slot_matches))



################ SYMMETRY BREAKING CONSTRAINTS ################


# (sb1) The first match (first week and period) is between the first and the second teams (0-1)
def sb1(M, s):
    s.add(M[0][0][0][1])


# (sb2) Fix opponents order for team 0
def sb2(M, n_teams, Weeks, Periods, s):
    for w in Weeks:
        opponent = w + 1  # team 1 in week 0, team 2 in week 1, etc.
        if opponent < n_teams:
            s.add(Or([M[w][p][0][opponent] for p in Periods]))

