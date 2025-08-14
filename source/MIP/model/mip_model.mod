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
var imbalance {t in TEAMS} integer >= 1 <= W;
var max_imbalance integer >= 1 <= W;

# =========================
# CONSTRAINTS
# =========================

# (1) Each team plays all others exactly once;
s.t. PairOnce {i in TEAMS, k in TEAMS: i < k}:
    sum {w in WEEKS, p in PERIODS} (X[i,k,w,p] + X[k,i,w,p]) = 1;

# (2) Every team plays once a week;
s.t. OnePerWeek {t in TEAMS, w in WEEKS}:
    sum {opp in TEAMS, p in PERIODS: opp <> t} (X[t,opp,w,p] + X[opp,t,w,p]) = 1;

# (3) Every team plays at most twice in the same period over the tournament;
s.t. MaxTwoPerPeriod {t in TEAMS, p in PERIODS}:
    sum {w in WEEKS, opp in TEAMS: opp <> t} (X[t,opp,w,p] + X[opp,t,w,p]) <= 2;

# (4) In every week, each period has exactly two teams playing (one match);
s.t. OneMatchPerSlot {w in WEEKS, p in PERIODS}:
    sum {h in TEAMS, a in TEAMS: h <> a} X[h,a,w,p] = 1;

% -----------------
% SYMMETRY BREAKING
% -----------------

# (SB1) Fixes first match of team 1 at home.
s.t. SB1: sum {p in PERIODS} X[1,2,1,p] >= use_sb;

# (SB2) Fixes opponent order for team 1 to break week/opponent symmetries.
s.t. SB2 {w in WEEKS: w+1 <= n}:
    sum {p in PERIODS} (X[1,w+1,w,p] + X[w+1,1,w,p]) >= use_sb;

% ---------------------
% OPTIMIZATION FUNCTION
% ---------------------

s.t. HomeGamesDef {t in TEAMS}:
    home_games[t] = sum {opp in TEAMS, w in WEEKS, p in PERIODS: opp <> t} X[t,opp,w,p];

s.t. AwayGamesDef {t in TEAMS}:
    away_games[t] = sum {opp in TEAMS, w in WEEKS, p in PERIODS: opp <> t} X[opp,t,w,p];

s.t. Imbalance1 {t in TEAMS}: imbalance[t] >= home_games[t] - away_games[t];
s.t. Imbalance2 {t in TEAMS}: imbalance[t] >= away_games[t] - home_games[t];
s.t. MaxImbalanceDef {t in TEAMS}: max_imbalance >= imbalance[t];

minimize MaxImbalanceObj: use_opt * max_imbalance;