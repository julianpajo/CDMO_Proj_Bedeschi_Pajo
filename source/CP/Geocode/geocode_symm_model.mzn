% ---------- Instance Parameters ----------
int: teams;
int: weeks = teams - 1;
int: periods = teams div 2;

set of int: Teams = 1..teams;
set of int: Weeks = 1..weeks;
set of int: Periods = 1..periods;

% ---------- VARIABLES ----------
% match[t1, t2, p, w] = true if team t1 plays team t2 at period p, week w (only for t1 < t2)
array[Teams, Teams, Periods, Weeks] of var bool: match;

% ---------- CONSTRAINTS ----------

% Disable duplicate and symmetric matches
constraint
  forall(t1, t2 in Teams where t1 >= t2, p in Periods, w in Weeks) (
    match[t1,t2,p,w] = false
  );

% (1) Each cell (week, period) must contain exactly one match
constraint
  forall(w in Weeks, p in Periods)(
    sum(t1, t2 in Teams where t1 < t2)(
      bool2int(match[t1,t2,p,w])
    ) = 1
  );

% (2) Each team plays exactly once per week
constraint
  forall(t in Teams, w in Weeks)(
    sum(p in Periods, t1 in Teams where t1 != t)(
      bool2int(match[min(t,t1), max(t,t1), p, w])
    ) = 1
  );

% (3) Each team plays at most twice in the same period throughout the tournament
constraint
  forall(t in Teams, p in Periods)(
    sum(w in Weeks, t1 in Teams where t1 != t)(
      bool2int(match[min(t,t1), max(t,t1), p, w])
    ) <= 2
  );

% (4) Each match {t1, t2} occurs exactly once in the tournament
constraint
  forall(t1, t2 in Teams where t1 < t2)(
    sum(p in Periods, w in Weeks)(
      bool2int(match[t1,t2,p,w])
    ) = 1
  );

% ---------- SYMMETRY BREAKING ----------
constraint
  forall(i in 1..periods)(
    match[2*i-1, 2*i, i, 1] = true
  );

% ---------- TABULAR OUTPUT ----------
output [
  "\t" ++ concat([ "W" ++ show(w) ++ "\t" | w in Weeks ]) ++ "\n"
] ++
[
  "P" ++ show(p) ++ "\t" ++
  concat([
    let {
      array[int] of string: matches_in_cell = [
        if fix(match[t1,t2,p,w]) then
          "T" ++ show(t1) ++ "-T" ++ show(t2)
        else
          ""
        endif
        | t1, t2 in Teams where t1 < t2
      ],
      string: match_str = join(", ", [m | m in matches_in_cell where m != ""])
    } in
      if match_str == "" then "-\t" else match_str ++ "\t" endif
    | w in Weeks
  ]) ++ "\n"
  | p in Periods
];
