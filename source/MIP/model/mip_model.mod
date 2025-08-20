# =========================
# PARAMETERS
# =========================
param n;                 # number of teams
param W := n - 1;        # number of weeks
param P := n div 2;      # number of periods per week

param use_sb default 0;  # symmetry breaking flag (0/1)
param use_opt default 0; # optimization flag (0/1)

set TEAMS := 1..n;
set WEEKS := 1..W;
set PERIODS := 1..P;

# Set of unordered team pairs (i < k)
set MATCHES := {i in TEAMS, k in TEAMS: i < k};


# =========================
# DECISION VARIABLES
# =========================
# 1) Match scheduling per week (unordered)
var y {i in TEAMS, k in TEAMS, w in WEEKS: i < k} binary;

# 2) Period assignment for each scheduled match
var A {i in TEAMS, k in TEAMS, w in WEEKS, p in PERIODS: i < k} binary;

# 3) Home/away orientation for scheduled matches
var H {h in TEAMS, a in TEAMS, w in WEEKS: h <> a} binary;

# Variables for optimization (home/away balance)
var home_games {t in TEAMS} integer >= 0 <= W;
var away_games {t in TEAMS} integer >= 0 <= W;
var imbalance  {t in TEAMS} integer >= 0 <= W;
var max_imbalance integer >= 0 <= W;


# =========================
# HARD CONSTRAINTS
# =========================

# (1) Every team plays with every other team only once
s.t. PairOnce {(i,k) in MATCHES}:
    sum {w in WEEKS} y[i,k,w] = 1;

# (2) Every team plays once a week
s.t. OnePerWeek {t in TEAMS, w in WEEKS}:
    sum {k in TEAMS: k < t} y[k,t,w] +
    sum {k in TEAMS: k > t} y[t,k,w] = 1;

# (3) Every team plays at most twice in the same period over the tournament
s.t. MaxTwoPerPeriod {t in TEAMS, p in PERIODS}:
    sum {w in WEEKS}
        (
          sum {k in TEAMS: k < t} A[k,t,w,p] +
          sum {k in TEAMS: k > t} A[t,k,w,p]
        ) <= 2;


# =========================
# IMPLIED CONSTRAINTS
# =========================

# (IC1) Period consistency:
# If a match (i,k) is scheduled in week w, it must be assigned
# to exactly one period in that week (and none otherwise).
s.t. PeriodConsistency {(i,k) in MATCHES, w in WEEKS}:
    sum {p in PERIODS} A[i,k,w,p] = y[i,k,w];

# (IC2) Two teams per period (one match per slot):
# Each period in each week hosts exactly one match,
# hence exactly two teams.
s.t. OneMatchPerSlot {w in WEEKS, p in PERIODS}:
    sum {(i,k) in MATCHES} A[i,k,w,p] = 1;

# (IC3) Symmetry of matches (home/away orientation):
# If match (i,k) is played in week w, exactly one of the two
# orientations (i home, k away) or (k home, i away) must hold.
s.t. HomeAwaySymmetry {(i,k) in MATCHES, w in WEEKS}:
    H[i,k,w] + H[k,i,w] = y[i,k,w];


# =========================
# SYMMETRY BREAKING (if use_sb = 1)
# =========================

# (SB1): Fix match (1,2) in week 1
s.t. SB1:
    sum {p in PERIODS} A[1,2,1,p] = use_sb;

# (SB2): Team 1 plays team (w+1) in week w
s.t. SB2 {w in WEEKS: w+1 <= n}:
    y[min(1,w+1), max(1,w+1), w] >= use_sb;


# =========================
# HOME/AWAY BALANCE & OBJECTIVE
# =========================

s.t. HomeGamesDef {t in TEAMS}:
    home_games[t] = sum {a in TEAMS, w in WEEKS: a <> t} H[t,a,w];

s.t. AwayGamesDef {t in TEAMS}:
    away_games[t] = sum {h in TEAMS, w in WEEKS: h <> t} H[h,t,w];

s.t. Imbalance1 {t in TEAMS}: imbalance[t] >= home_games[t] - away_games[t];
s.t. Imbalance2 {t in TEAMS}: imbalance[t] >= away_games[t] - home_games[t];

s.t. MaxImbalanceDef {t in TEAMS}: max_imbalance >= imbalance[t];

minimize MaxImbalanceObj: use_opt * max_imbalance;
