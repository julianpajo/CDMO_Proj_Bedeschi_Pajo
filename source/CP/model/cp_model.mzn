include "all_different.mzn";

% ==========
% PARAMETERS
% ==========

bool: sb;

int: teams; % even number
set of int: TEAMS = 1..teams;

int: weeks = teams - 1;
set of int: WEEKS = 1..weeks;

int: periods = teams div 2;
set of int: PERIODS = 1..periods;

% ==================
% DECISION VARIABLES
% ==================

% Opponent matrix: O[i,j] = opponent of team i in week j
array[TEAMS, WEEKS] of var TEAMS: O;

% Place matrix: P[i,j] = 1 if home, 0 if away
array[TEAMS, WEEKS] of var 0..1: PL;

% Period assignment: per[i,j] = period where team i plays in week j
array[TEAMS, WEEKS] of var PERIODS: per;


% ================
% HARD CONSTRAINTS
% ================

% (1) Each team plays all others exactly once
constraint
    forall(i in TEAMS) (
        all_different([O[i,j] | j in WEEKS])
    );

% (2) Every team plays once per week
constraint
    forall(j in WEEKS) (
        all_different([O[t,j] | t in TEAMS])
    );

% (3) Every team plays at most twice in the same period
% Each period can appear 0, 1 or 2 times for a given team
constraint
    forall(i in TEAMS) (
        global_cardinality(
            [per[i,j] | j in WEEKS],   % variables to count
            PERIODS,                   % possible values
            [0 | p in PERIODS],        % lower bound (0 each)
            [2 | p in PERIODS]         % upper bound (2 each)
        )
    );


% ===================
% IMPLIED CONSTRAINTS
% ===================

% (4) No self-matches
constraint
    forall(i in TEAMS, j in WEEKS) (
        O[i,j] != i
    );

% (5) Symmetry of matches
constraint
    forall(i in TEAMS, j in WEEKS) (
        O[O[i,j], j] = i /\
        PL[i,j] + PL[O[i,j], j] = 1
    );

% (6) Period consistency
% If i plays k in week j, they share the same period
constraint
    forall(i in TEAMS, j in WEEKS) (
        per[O[i,j], j] = per[i,j]
    );

% (7) Two teams per period each week
constraint
    forall(j in WEEKS) (
        global_cardinality(
            [per[t,j] | t in TEAMS],
            PERIODS,
            [2 | p in PERIODS],
            [2 | p in PERIODS]
        )
    );

% =============================
% SYMMETRY BREAKING CONSTRAINTS
% =============================

% (SB1) Fixes first match of team 1 at home.
constraint sb -> PL[1,1] = 1;

% (SB2) Fixes opponent order for team 1 to break week/opponent symmetries.
constraint sb -> forall(j in WEEKS) (O[1,j] = j+1);

% =====================
% OPTIMIZATION FUNCTION
% =====================

array[TEAMS] of var 0..weeks: num_home =
    [ sum([ bool2int(PL[t,w] = 1) | w in WEEKS ]) | t in TEAMS ];

array[TEAMS] of var 0..weeks: num_away =
    [ sum([ bool2int(PL[t,w] = 0) | w in WEEKS ]) | t in TEAMS ];

array[TEAMS] of var 1..weeks: imbalances =
    [ abs(num_home[t] - num_away[t]) | t in TEAMS ];

var 1..weeks: max_imbalance = max(imbalances);