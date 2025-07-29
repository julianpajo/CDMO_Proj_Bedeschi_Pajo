% ---------- INCLUDES ----------
include "globals.mzn";

% ---------- Instance Parameters ----------
int: teams;
int: weeks = teams - 1;
int: periods = teams div 2;

set of int: Teams = 1..teams;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

% ---------- VARIABLES ----------
% match[w, p] = [home, away] team in week w and period p
array[Weeks, Periods] of var Teams: home;
array[Weeks, Periods] of var Teams: away;

% Flattened list of matches for easier global constraints
array[1..weeks*periods] of var Teams: flat_home = [home[w,p] | w in Weeks, p in Periods];
array[1..weeks*periods] of var Teams: flat_away = [away[w,p] | w in Weeks, p in Periods];

% ---------- CONSTRAINTS ----------

% (1) Teams in a match must be different
constraint
  forall(w in Weeks, p in Periods)(
    home[w, p] != away[w, p]
  );

% (2) Team indices ordered: home < away (to avoid duplicate {i,j} and {j,i})
constraint
  forall(w in Weeks, p in Periods)(
    home[w, p] < away[w, p]
  );

% (3) Each team plays exactly once per week
constraint
  forall(w in Weeks)(
    alldifferent([home[w,p] | p in Periods] ++ [away[w,p] | p in Periods])
  );

% (4) Each match {t1, t2} occurs exactly once in the tournament
array[Teams, Teams] of var 0..1: played;
constraint
  forall(t1, t2 in Teams where t1 < t2)(
    played[t1, t2] = sum([bool2int(home[w,p] = t1 /\ away[w,p] = t2) | w in Weeks, p in Periods])
  ) /\
  forall(t1, t2 in Teams where t1 < t2)(
    played[t1, t2] = 1
  );

% (5) Each team plays at most twice in the same period throughout the tournament
constraint
  forall(t in Teams, p in Periods)(
    sum([bool2int(home[w,p] = t \/ away[w,p] = t) | w in Weeks]) <= 2
  );

% ---------- GLOBAL CONSTRAINTS ----------
% Enforce each team appears exactly (teams - 1) times across all matches
constraint
  global_cardinality(flat_home ++ flat_away, [i | i in Teams], [teams - 1 | i in Teams]);


% ---------- SYMMETRY BREAKING CONSTRAINTS ----------

% (SB1) Fix the first week as consecutive pairs: [1,2], [3,4], [5,6], etc.
constraint
  forall(p in Periods)(
    home[1, p] = 2*p - 1 /\
    away[1, p] = 2*p
  );

constraint
  forall(w in Weeks, p in 1..periods-1)(
    home[w, p] < home[w, p+1] \/
    (home[w, p] = home[w, p+1] /\ away[w, p] < away[w, p+1])
  );

solve satisfy;

% ---------- OUTPUT ----------
output [
  "[\n"
] ++
[
  "  [" ++ 
  join(", ", ["[" ++ show(home[w,p]) ++ ", " ++ show(away[w,p]) ++ "]" | w in Weeks]) ++
  if p < periods then "]\n" else "]\n" endif
  | p in Periods
] ++
[
  "]\n"
];