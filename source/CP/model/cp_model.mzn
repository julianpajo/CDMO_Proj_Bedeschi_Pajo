include "all_different.mzn";

% ----------
% PARAMETERS
% ----------

bool: sb;
int: teams; % even number
set of int: TEAMS = 1..teams;

int: weeks = teams - 1;
set of int: WEEKS = 1..weeks;

int: periods = teams div 2;
set of int: PERIODS = 1..periods;

% ------------------
% DECISION VARIABLES
% ------------------

% Opponent matrix: O[i,j] = opponent of team i in week j
array[TEAMS, WEEKS] of var TEAMS: O;

% Place matrix: P[i,j] = 1 if home, 0 if away
array[TEAMS, WEEKS] of var 0..1: P;

% Period assignment: per[i,j] = period where team i plays in week j
array[TEAMS, WEEKS] of var PERIODS: per;


% -----------
% CONSTRAINTS
% -----------

% (1) Each team plays all others exactly once;
constraint
    forall(i in TEAMS) (
        all_different([O[i,j] | j in WEEKS]) /\
        forall(j in WEEKS) (O[i,j] != i)
    );

% (2) Every team plays once a week;
constraint
    forall(i in TEAMS, j in WEEKS) (
        O[O[i,j], j] = i /\
        P[i,j] + P[O[i,j], j] = 1
    );

% (3) Every team plays at most twice in the same period over the tournament;
constraint
    forall(i in TEAMS, p in PERIODS) (
        count([per[i,j] | j in WEEKS], p) <= 2
    );

% (4) Period consistency;
constraint
    forall(i in TEAMS, j in WEEKS) (
        per[O[i,j], j] = per[i,j]
    );

% (5) In every week, each period has exactly two teams playing (one match);
constraint
    forall(j in WEEKS, p in PERIODS) (
        count([per[t,j] == p | t in TEAMS], true) = 2
    );

% -----------------
% SYMMETRY BREAKING
% -----------------

% (SB1) Fixes first match of team 1 at home.
constraint sb -> P[1,1] = 1;

% (SB2) Fixes opponent order for team 1 to break week/opponent symmetries.
constraint sb -> forall(j in WEEKS) (O[1,j] = j+1);

% ---------------------
% OPTIMIZATION FUNCTION
% ---------------------

array[TEAMS] of var 0..weeks: num_home =
    [ sum([ bool2int(P[t,w] = 1) | w in WEEKS ]) | t in TEAMS ];

array[TEAMS] of var 0..weeks: num_away =
    [ sum([ bool2int(P[t,w] = 0) | w in WEEKS ]) | t in TEAMS ];

array[TEAMS] of var 0..weeks: imbalances =
    [ abs(num_home[t] - num_away[t]) | t in TEAMS ];

var 0..weeks: max_imbalance = max(imbalances);