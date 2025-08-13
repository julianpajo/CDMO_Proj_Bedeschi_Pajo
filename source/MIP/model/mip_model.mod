# =========================
# PARAMETERS
# =========================
param n; # number of teams
param W := n - 1; # weeks
param P := n div 2; # periods per week

param use_sb default 0; # use symmetry breaking (0/1)
param use_opt default 0; # use optimization (0/1)

set TEAMS := 1..n;
set WEEKS := 1..W;
set PERIODS := 1..P;

# All ordered pairs of distinct teams
set MATCHES := {h in TEAMS, a in TEAMS: h <> a};

# =========================
# DECISION VARIABLES
# =========================
var X {h in TEAMS, a in TEAMS, w in WEEKS, p in PERIODS: h <> a} binary;

# For optimization
var home_games {t in TEAMS} integer >= 0 <= W;
var away_games {t in TEAMS} integer >= 0 <= W;
var imbalance {t in TEAMS} integer >= 0 <= W;
var max_imbalance integer >= 0 <= W;

# =========================
# CONSTRAINTS
# =========================

# C1: each pair plays exactly once (either direction)
s.t. PairOnce {i in TEAMS, k in TEAMS: i < k}:
    sum {w in WEEKS, p in PERIODS} (X[i,k,w,p] + X[k,i,w,p]) = 1;

# C2: each team plays exactly one match per week
s.t. OnePerWeek {t in TEAMS, w in WEEKS}:
    sum {opp in TEAMS, p in PERIODS: opp <> t} (X[t,opp,w,p] + X[opp,t,w,p]) = 1;

# C3: at most 2 matches in same period slot over all weeks for a team
s.t. MaxTwoPerPeriod {t in TEAMS, p in PERIODS}:
    sum {w in WEEKS, opp in TEAMS: opp <> t} (X[t,opp,w,p] + X[opp,t,w,p]) <= 2;

# Slot capacity: exactly 1 match in each (week, period)
s.t. OneMatchPerSlot {w in WEEKS, p in PERIODS}:
    sum {h in TEAMS, a in TEAMS: h <> a} X[h,a,w,p] = 1;

# Optional Symmetry Breaking (conditional)
# Force team 1 home vs team 2 in week 1
s.t. SB1: sum {p in PERIODS} X[1,2,1,p] >= use_sb;

# Force team 1 vs team (w+1) in week w
s.t. SB2 {w in WEEKS: w+1 <= n}:
    sum {p in PERIODS} (X[1,w+1,w,p] + X[w+1,1,w,p]) >= use_sb;

# Home/Away counts
s.t. HomeGamesDef {t in TEAMS}:
    home_games[t] = sum {opp in TEAMS, w in WEEKS, p in PERIODS: opp <> t} X[t,opp,w,p];

s.t. AwayGamesDef {t in TEAMS}:
    away_games[t] = sum {opp in TEAMS, w in WEEKS, p in PERIODS: opp <> t} X[opp,t,w,p];

# Imbalance constraints
s.t. Imbalance1 {t in TEAMS}: imbalance[t] >= home_games[t] - away_games[t];
s.t. Imbalance2 {t in TEAMS}: imbalance[t] >= away_games[t] - home_games[t];
s.t. MaxImbalanceDef {t in TEAMS}: max_imbalance >= imbalance[t];

# =========================
# OBJECTIVE
# =========================
# Conditional objective based on use_opt parameter
minimize MaxImbalanceObj: use_opt * max_imbalance;