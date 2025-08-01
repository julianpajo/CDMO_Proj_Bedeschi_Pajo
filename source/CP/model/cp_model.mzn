% ---------- INCLUDES ----------

include "globals.mzn";


% ---------- Instance Parameters ----------

int: teams;
int: weeks = teams - 1;
int: periods = teams div 2;

bool: sb;

set of int: Teams = 1..teams;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

% ---------- VARIABLES ----------

array[Weeks, Periods] of var Teams: home;
array[Weeks, Periods] of var Teams: away;

array[1..weeks*periods] of var Teams: flat_home = [home[w,p] | w in Weeks, p in Periods];
array[1..weeks*periods] of var Teams: flat_away = [away[w,p] | w in Weeks, p in Periods];

array[1..2*weeks*periods] of var Teams: vars = flat_home ++ flat_away;


% ---------- CONSTRAINTS ----------

% (1) Teams in a match must be different
constraint forall(w in Weeks, p in Periods)(home[w, p] != away[w, p]);


% (2) Each team plays exactly once per week
constraint forall(w in Weeks)(
    alldifferent([home[w,p] | p in Periods] ++ [away[w,p] | p in Periods])
);


% (3) Each team plays at most twice in the same period
constraint forall(t in Teams, p in Periods)(
    sum([bool2int(home[w,p] = t \/ away[w,p] = t) | w in Weeks]) <= 2
);


% (4) Each match {t1, t2} occurs exactly once
constraint
  forall(t1, t2 in Teams where t1 < t2)(
    sum([bool2int((home[w,p] = t1 /\ away[w,p] = t2) \/ 
                  (home[w,p] = t2 /\ away[w,p] = t1)) 
         | w in Weeks, p in Periods]) = 1
  );



% ---------- SYMMETRY BREAKING CONSTRAINTS ----------

% (SB1) Fix the first week as consecutive pairs: [1,2], [3,4], [5,6], etc.
constraint sb ->
    forall(p in Periods)(
        home[1, p] = 2*p - 1 /\
        away[1, p] = 2*p
    );

% (SB2) Team indices ordered: home < away (to avoid duplicate {i,j} and {j,i})
constraint sb ->
    forall(w in Weeks, p in Periods)(
        home[w, p] < away[w, p]
    );